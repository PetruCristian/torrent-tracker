import requests
from flask_app.config import Config

BASE_URL = "http://localhost:5000"

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
    token = login("theadministrator", "admin")

    if token:
        for i in range(12):
            resp = requests.get(f"{BASE_URL}/")
            print(f"Status code: {resp.status_code}")
            print(f"Response: {resp.text}")