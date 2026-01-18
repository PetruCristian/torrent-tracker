import requests
import uuid

BASE_URL = "http://localhost:5000"
# BASE_URL = "http://localhost:80"

def run_test():
    unique_id = str(uuid.uuid4())[:8]
    username = f"user_{unique_id}"
    email = f"user_{unique_id}@test.com"
    password = "StrongPass123!"

    print(f"--- STARTING TEST FOR: {username} ---")

    user_payload = {
        "username": username,
        "email": email,
        "password": password,
        "firstName": "Lifecycle",
        "lastName": "Test"
    }


    print("\nStep 1: Registering new user...")
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


    print("\nStep 2: Logging in as new user...")
    login_payload = {
        "username": username,
        "password": password
    }

    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json=login_payload)

        if resp.status_code == 200:
            data = resp.json()
            if "access_token" in data:
                print("PASS: Login successful. Token received.")
                print(f"Token: {data['access_token'][:15]}...")
            else:
                print("FAIL: 200 OK but no token found in response.")
        else:
            print(f"FAIL: Expected 200, got {resp.status_code}")
            print(f"Response: {resp.text}")
            return

    except Exception as e:
        print(f"ERROR: Connection failed - {e}")
        return


    print("\nStep 3: Attempting duplicate registration...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json=user_payload)

        if resp.status_code == 409:
            print("PASS: Server correctly rejected duplicate user (409 Conflict).")
            print(f"Message: {resp.json().get('error')}")
        elif resp.status_code == 201:
            print("FAIL: Server allowed duplicate registration! (Got 201)")
        else:
            print(f"WARNING: Expected 409, got {resp.status_code}")
            print(f"Response: {resp.text}")

    except Exception as e:
        print(f"ERROR: Connection failed - {e}")


    print("\nStep 4: Logging in as ADMIN...")
    admin_token = None
    try:
        # Note: You need a valid admin user in your DB/Keycloak for this
        resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "theadministrator", "password": "admin"})
        if resp.status_code == 200:
            admin_token = resp.json().get("access_token")
            print("PASS: Admin logged in.")
        else:
            print(f"FAIL: Admin login failed. Did you create the admin user? Code: {resp.status_code}")
            print("(Cannot proceed with role change test without admin)")
            return
    except Exception as e:
        print(f"ERROR: {e}")
        return


    print("\nStep 5: Finding user ID for role change...")
    target_user_id = None
    headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        # Get list of all users
        resp = requests.get(f"{BASE_URL}/users", headers=headers)
        if resp.status_code == 200:
            users = resp.json()
            # Find our specific user in the list
            for u in users:
                if u['username'] == username:
                    target_user_id = u['id']
                    print(f"PASS: Found user ID: {target_user_id} (Current Role: {u['role']})")
                    break

            if not target_user_id:
                print("FAIL: Could not find the new user in the /users list.")
                return
        else:
            print(f"FAIL: Could not fetch users list - {resp.status_code}")
            return
    except Exception as e:
        print(f"ERROR: {e}")
        return


    print(f"\nStep 6: Promoting user {target_user_id} to 'uploader'...")
    try:
        payload = {"role": "uploader"}
        resp = requests.put(f"{BASE_URL}/users/{target_user_id}", json=payload, headers=headers)

        if resp.status_code == 200:
            print("PASS: Role update request successful.")
            print(f"Response: {resp.json()}")
        else:
            print(f"FAIL: Role update failed - {resp.status_code}")
            print(f"Response: {resp.text}")
            return
    except Exception as e:
        print(f"ERROR: {e}")
        return


    print("\nStep 7: Verifying role persistence...")
    try:
        # Fetch the list again to make sure the database updated
        resp = requests.get(f"{BASE_URL}/users", headers=headers)
        users = resp.json()
        for u in users:
            if u['id'] == target_user_id:
                if u['role'] == 'uploader':
                    print("PASS: Database shows role is now 'uploader'.")
                else:
                    print(f"FAIL: Database still shows role as '{u['role']}'.")
                break
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    run_test()