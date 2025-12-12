from keycloak import KeycloakOpenID
from flask import request, jsonify, g
from functools import wraps
from config import Config

keycloak_openid = KeycloakOpenID(
    server_url=Config.KEYCLOAK_SERVER_URL,
    client_id=Config.KEYCLOAK_CLIENT_ID,
    realm_name=Config.KEYCLOAK_REALM,
    client_secret_key=Config.KEYCLOAK_CLIENT_SECRET
)

def token_required(role=None):
    """
    Decorator to protect routes.
    Verifies the JWT token and checks if the user has the required role.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = None

            # 1. Get Token from Header
            auth_header = request.headers.get('Authorization')
            if auth_header:
                try:
                    token = auth_header.split(" ")[1] # "Bearer <token>"
                except IndexError:
                    return jsonify({"message": "Token format is invalid"}), 401

            if not token:
                return jsonify({"message": "Token is missing"}), 401

            try:
                # 2. Verify Token with Keycloak
                # strictly verifies signature and expiration
                user_info = keycloak_openid.userinfo(token)

                # 3. Check Role (Authorization) 
                if role:
                    # Keycloak stores realm roles in: resource_access.realm_access.roles
                    # Depending on setup, it might also be in realm_access['roles']
                    user_roles = user_info.get('realm_access', {}).get('roles', [])
                    if role not in user_roles:
                        return jsonify({"message": "Permission denied. Role required: " + role}), 403

                # Attach user info to global context for the route to use
                g.user = user_info

            except Exception as e:
                return jsonify({"message": "Invalid Token", "error": str(e)}), 401

            return f(*args, **kwargs)
        return wrapper
    return decorator

def login_user(username, password):
    """Helper to exchange credentials for a token (for the /login route)"""
    return keycloak_openid.token(username, password)