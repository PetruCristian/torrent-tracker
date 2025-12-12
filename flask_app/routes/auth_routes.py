from flask import Blueprint, request, jsonify
from models import User, db
from services.auth_service import login_user
from config import Config

# Import the Admin client
from keycloak import KeycloakAdmin, KeycloakError

auth_bp = Blueprint('auth', __name__)

def get_admin_client():
    return KeycloakAdmin(
        server_url=Config.KEYCLOAK_SERVER_URL,
        username=Config.KEYCLOAK_ADMIN_USER,
        password=Config.KEYCLOAK_ADMIN_PASSWORD,
        realm_name=Config.KEYCLOAK_REALM,
        user_realm_name='master', 
        verify=True
    )

@auth_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not all(k in data for k in ('username', 'password', 'email')):
        return jsonify({"error": "Missing username, password, or email"}), 400

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    first_name = data.get('firstName', '')
    last_name = data.get('lastName', '')

    try:
        keycloak_admin = get_admin_client()

        new_user_payload = {
            "email": email,
            "username": username,
            "enabled": True,
            "firstName": first_name,
            "lastName": last_name,
            "emailVerified": True, # I'm definetly not going to bother with verifying emails
            "credentials": [{
                "value": password,
                "type": "password",
                "temporary": False
            }]
        }

        keycloak_user_id = keycloak_admin.create_user(new_user_payload)

        keycloak_admin.assign_realm_roles(user_id=keycloak_user_id, roles=['normal'])

    except KeycloakError as e:
        error_msg = str(e)
        if "409" in error_msg:
            return jsonify({"error": "User already exists in Keycloak"}), 409
        return jsonify({"error": f"Keycloak registration failed: {error_msg}"}), 500

    try:
        # Check if local user exists (to prevent sync issues)
        if not User.query.filter_by(username=username).first():
            local_user = User(
                username=username,
                email=email,
                role='normal'
            )
            db.session.add(local_user)
            db.session.commit()

        return jsonify({"message": "User registered successfully in Keycloak and DB"}), 201

    except Exception as e:
        # If database fails, delete the Keycloak user to maintain consistency
        keycloak_admin.delete_user(keycloak_user_id)
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    try:
        token_response = login_user(username, password)
        return jsonify(token_response), 200
    except Exception as e:
        return jsonify({"error": "Invalid credentials", "details": str(e)}), 401

@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    return jsonify({"message": "Logged out successfully"}), 200