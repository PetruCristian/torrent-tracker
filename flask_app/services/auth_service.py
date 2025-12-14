from keycloak import KeycloakOpenID, KeycloakAdmin, KeycloakError
from flask import request, jsonify, g
from functools import wraps
from config import Config
import requests

keycloak_openid = KeycloakOpenID(
    server_url=Config.KEYCLOAK_SERVER_URL,
    client_id=Config.KEYCLOAK_CLIENT_ID,
    realm_name=Config.KEYCLOAK_REALM,
    client_secret_key=Config.KEYCLOAK_CLIENT_SECRET
)

def get_keycloak_admin_client():
    return KeycloakAdmin(
        server_url=Config.KEYCLOAK_SERVER_URL,
        username=Config.KEYCLOAK_ADMIN_USER,
        password=Config.KEYCLOAK_ADMIN_PASSWORD,
        realm_name=Config.KEYCLOAK_REALM,
        user_realm_name="master", 
        verify=True
    )

def get_keycloak_admin_token():
    url = Config.KEYCLOAK_SERVER_URL + "/realms/master/protocol/openid-connect/token"
    payload = {
        "client_id": "admin-cli",
        "username": "admin",
        "password": "admin",
        "grant_type": "password"
    }

    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def get_keycloak_user_id(admin_token, username):
    url = f"{Config.KEYCLOAK_SERVER_URL}/admin/realms/{Config.KEYCLOAK_REALM}/users?username={username}"
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        users = resp.json()
        # Keycloak search is fuzzy, so filter for exact match
        for u in users:
            if u['username'] == username:
                return u['id']
    return None

def get_role_representation(admin_token, role_name):
    url = f"{Config.KEYCLOAK_SERVER_URL}/admin/realms/{Config.KEYCLOAK_REALM}/roles/{role_name}"
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return None

def verify_token(token):
    data = {
        "token": token,
        "client_id": Config.KEYCLOAK_CLIENT_ID,
        "client_secret": Config.KEYCLOAK_CLIENT_SECRET
    }

    r = requests.post(Config.KEYCLOAK_INTROSPECT, data=data)

    if r.status_code != 200:
        return None

    info = r.json()
    if not info.get("active"):
        return None

    return info

def require_roles(*roles):
    """
    Decorator to protect routes.
    Verifies the token and checks if the user has the required role.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = None

            auth_header = request.headers.get("Authorization")

            if not auth_header:
                return jsonify({"error": "Missing Authorization header"}), 401

            token = auth_header.split(" ")[1] # "Bearer <token>"

            if not token:
                return jsonify({"message": "Token is missing"}), 401

            user_info = verify_token(token)

            if not user_info:
                return jsonify({"error": "Invalid token"}), 401

            if roles:
                user_roles = user_info.get("realm_access", {}).get("roles", [])
                if not any(role in user_roles for role in roles):
                    return jsonify({"message": "Permission denied. Missing role"}), 403

            # Attach user info to global context for the route to use
            g.user = user_info

            return f(*args, **kwargs)
        return wrapper
    return decorator

def login_user(username, password):
    """Helper to exchange credentials for a token (for the /login route)"""
    return keycloak_openid.token(username, password)