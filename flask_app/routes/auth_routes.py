import requests
from flask import Blueprint, request, jsonify
from models import User, db
from services.auth_service import login_user, get_keycloak_admin_token, require_roles, get_keycloak_user_id, get_role_representation
from config import Config

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or not all(k in data for k in ("username", "password", "email")):
        return jsonify({"error": "Missing username, password, or email"}), 400

    username: str = data.get("username")
    password: str = data.get("password")
    email: str = data.get("email")
    first_name: str = data.get("firstName", "")
    last_name: str = data.get("lastName", "")

    new_user_payload = {
        "email": email,
        "username": username.lower(),
        "enabled": True,
        "firstName": first_name,
        "lastName": last_name,
        "emailVerified": True, # I"m definetly not going to bother with verifying emails
        "credentials": [{
            "value": password,
            "type": "password",
            "temporary": False
        }]
    }

    try:
        keycloak_admin_token = get_keycloak_admin_token()
    except Exception as e:
        return jsonify({"error": "Backend authentication failed"}), 500

    create_url = Config.KEYCLOAK_SERVER_URL + "/admin/realms/" + Config.KEYCLOAK_REALM + "/users"

    headers = {
        "Authorization": f"Bearer {keycloak_admin_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(create_url, json=new_user_payload, headers=headers)

    if response.status_code == 201:
        try:
            # Check if user already exists in DB
            if not User.query.filter_by(username=username).first():
                local_user = User(
                    username=username,
                    email=email,
                    role="normal"
                )
                db.session.add(local_user)
                db.session.commit()

            return jsonify({"message": "User created successfully in Keycloak and DB"}), 201
        except Exception as e:
            db.session.rollback()

            user_location = response.headers.get("Location")
            if user_location:
                requests.delete(user_location, headers=headers)

            return jsonify({"error": "Database insert failed. Keycloak user deleted.", "details": str(e)}), 500
    elif response.status_code == 409:
        return jsonify({"error": "User already exists"}), 409
    else:
        return jsonify({"error": "Failed to create user", "details": response.text}), response.status_code

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    try:
        token_response = login_user(username, password)
        return jsonify(token_response), 200
    except Exception as e:
        return jsonify({"error": "Invalid credentials", "details": str(e)}), 401

@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.route("/users", methods=["GET"])
@require_roles("admin")
def list_users():
    users = User.query.all()
    output = []
    for user in users:
        output.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        })
    return jsonify(output), 200

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_roles("admin")
def update_user_role(user_id):
    data = request.get_json()
    new_role = data.get('role')

    valid_roles = ['visitor', 'normal', 'uploader', 'admin']
    if not new_role or new_role not in valid_roles:
        return jsonify({"error": f"Invalid role. Must be one of: {valid_roles}"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    old_role = user.role
    if old_role == new_role:
        return jsonify({"message": "User already has this role"}), 200

    try:
        kc_admin_token = get_keycloak_admin_token()
        kc_user_id = get_keycloak_user_id(kc_admin_token, user.username)

        if not kc_user_id:
            return jsonify({"error": "Sync Error: User found locally but not in Keycloak"}), 500

        new_role_rep = get_role_representation(kc_admin_token, new_role)
        old_role_rep = get_role_representation(kc_admin_token, old_role)

        if not new_role_rep:
             return jsonify({"error": f"Role '{new_role}' does not exist in Keycloak settings"}), 500

        mapping_url = f"{Config.KEYCLOAK_SERVER_URL}/admin/realms/{Config.KEYCLOAK_REALM}/users/{kc_user_id}/role-mappings/realm"
        headers = {
            "Authorization": f"Bearer {kc_admin_token}",
            "Content-Type": "application/json"
        }

        if old_role_rep:
            requests.delete(mapping_url, json=[old_role_rep], headers=headers)

        resp = requests.post(mapping_url, json=[new_role_rep], headers=headers)

        if resp.status_code not in [204, 200]:
            return jsonify({"error": "Failed to update Keycloak role", "details": resp.text}), 500

    except Exception as e:
        return jsonify({"error": "Backend connection failed", "details": str(e)}), 500

    try:
        user.role = new_role
        db.session.commit()
        return jsonify({
            "message": f"User {user.username} role updated from {old_role} to {new_role}",
            "local_updated": True,
            "keycloak_updated": True
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database update failed", "details": str(e)}), 500