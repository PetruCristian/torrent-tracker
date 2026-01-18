import requests
from flask_app.config import Config

# BASE_URL = "http://localhost:" + str(Config.REST_API_PORT)
BASE_URL = "http://localhost:" + str(Config.NGINX_PORT)

def register(username: str, email: str, password: str, firstName: str, lastName: str):
    user_payload = {
        "username": username,
        "email": email,
        "password": password,
        "firstName": firstName,
        "lastName": lastName
    }

    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json=user_payload)

        if resp.status_code == 201:
            print("PASS: User registered successfully.")
        else:
            print(f"FAIL: Expected 201, got {resp.status_code}")
            print(f"Response: {resp.text}")
            return

    except Exception as e:
        print(f"ERROR: Connection failed - {e}")
        return

def login(username: str, password: str):
    login_payload = {
        "username": username,
        "password": password
    }

    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json=login_payload)

        if resp.status_code == 200:
            data = resp.json()
            if "access_token" in data:
                print("Login successful. Token received.")
                print(f"Token: {data['access_token'][:15]}...")
                return data['access_token']
            else:
                print("200 OK but no token found in response.")
        else:
            print(f"Expected 200, got {resp.status_code}")
            print(f"Response: {resp.text}")
            return

    except Exception as e:
        print(f"ERROR: Connection failed - {e}")
        return

if __name__ == "__main__":
    while (True):
        command: str = input("register, login, users, update: ")

        match command:
            case "register":
                username: str = input("Username: ")
                email: str = input("Email: ")
                password: str = input("Password: ")
                firstName: str = input("First name: ")
                lastName: str = input("Last name: ")
                register(username, email, password, firstName, lastName)

            case "login":
                username: str = input("Username: ")
                password: str = input("Password: ")
                login(username, password)

            case "users":
                theadministrator_token = login("theadministrator", "admin")

                headers = {
                    "Authorization": f"Bearer {theadministrator_token}"
                }

                resp = requests.get(f"{BASE_URL}/users", headers=headers)

                print(resp.content)

            case "update":
                theadministrator_token = login("theadministrator", "admin")

                headers = {
                    "Authorization": f"Bearer {theadministrator_token}"
                }

                uuid = input("Target user ID: ")
                new_role = input("New role: ")
                role_payload = {
                    "role": new_role
                }

                resp = requests.put(f"{BASE_URL}/users/{uuid}", headers=headers, json=role_payload)

                print(resp.content)

            case _:
                print("Unknown command. Exiting...")
                exit(0)
