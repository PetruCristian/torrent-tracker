import requests
from flask_app.config import Config
import os

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

def upload_torrent(token: str, file_path: str, description: str = ""):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': f
            }
            data = {
                'description': description
            }

            resp = requests.post(f"{BASE_URL}/torrents", headers=headers, files=files, data=data)

        if resp.status_code == 201:
            result = resp.json()
            print("Torrent uploaded successfully.")
            print(f"Torrent ID: {result.get('torrent_id')}")
            print(f"Filename: {result.get('filename')}")
            print(f"File Size: {result.get('file_size')} bytes")
            print(f"Info Hash: {result.get('info_hash')}")
            print(f"Pieces Count: {result.get('pieces_count')}")
            return result.get('torrent_id')
        else:
            print(f"FAIL: Expected 201, got {resp.status_code}")
            print(f"Response: {resp.text}")
            return None

    except FileNotFoundError:
        print(f"ERROR: File not found - {file_path}")
        return None
    except Exception as e:
        print(f"ERROR: Upload failed - {e}")
        return None

def search_torrents(token: str, query: str, limit: int = 50):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "q": query,
        "limit": limit
    }

    try:
        resp = requests.get(f"{BASE_URL}/search", headers=headers, params=params)

        if resp.status_code == 200:
            result = resp.json()
            print(f"\nSearch Results for '{query}':")
            print(f"Source: {result.get('source')}")
            print(f"Total Results: {result.get('count')}\n")

            for torrent in result.get('results', []):
                print(f"ID: {torrent.get('id')}")
                print(f"Filename: {torrent.get('filename')}")
                print(f"File Size: {torrent.get('file_size')} bytes")
                print(f"Seeders: {torrent.get('seeders')}")
                print(f"Leechers: {torrent.get('leechers')}")
                print(f"Completed: {torrent.get('completed')}")
                print(f"Created At: {torrent.get('created_at')}")
                if torrent.get('description'):
                    print(f"Description: {torrent.get('description')[:100]}...")
                print("-" * 60)
        else:
            print(f"FAIL: Expected 200, got {resp.status_code}")
            print(f"Response: {resp.text}")

    except Exception as e:
        print(f"ERROR: Search failed - {e}")

def get_torrent_details(token: str, torrent_id: int):
    """Get detailed information about a torrent."""
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        resp = requests.get(f"{BASE_URL}/torrents/{torrent_id}", headers=headers)

        if resp.status_code == 200:
            torrent = resp.json()
            print(f"\n=== Torrent Details ===")
            print(f"ID: {torrent.get('id')}")
            print(f"Filename: {torrent.get('filename')}")
            print(f"Description: {torrent.get('description')}")
            print(f"Info Hash: {torrent.get('info_hash')}")
            print(f"File Size: {torrent.get('file_size')} bytes")
            print(f"Piece Length: {torrent.get('piece_length')} bytes")
            print(f"Pieces Count: {torrent.get('pieces_count')}")
            print(f"Seeders: {torrent.get('seeders')}")
            print(f"Leechers: {torrent.get('leechers')}")
            print(f"Completed: {torrent.get('completed')}")
            print(f"Uploader: {torrent.get('uploader')}")
            print(f"Created At: {torrent.get('created_at')}")

            if torrent.get('files'):
                print(f"\nFiles ({len(torrent.get('files'))}):")
                for file in torrent.get('files'):
                    print(f"  - {file.get('path')} ({file.get('length')} bytes)")

            comments = torrent.get('comments', [])
            if comments:
                print(f"\nComments ({len(comments)}):")
                for comment in comments:
                    print(f"  [{comment.get('author')}] {comment.get('created_at')}")
                    print(f"  {comment.get('content')}")

            print("=" * 60)
        else:
            print(f"FAIL: Expected 200, got {resp.status_code}")
            print(f"Response: {resp.text}")

    except Exception as e:
        print(f"ERROR: Failed to fetch torrent details - {e}")

def delete_torrent(token: str, torrent_id: int):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        resp = requests.delete(f"{BASE_URL}/torrents/{torrent_id}", headers=headers)

        if resp.status_code == 200:
            result = resp.json()
            print("Torrent deleted successfully.")
            print(f"Torrent ID: {result.get('torrent_id')}")
            print(f"Filename: {result.get('filename')}")
        else:
            print(f"FAIL: Expected 200, got {resp.status_code}")
            print(f"Response: {resp.text}")

    except Exception as e:
        print(f"ERROR: Failed to delete torrent - {e}")

def download_torrent(token: str, torrent_id: int, output_path: str = None):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        resp = requests.get(f"{BASE_URL}/torrents/{torrent_id}/download", headers=headers)

        if resp.status_code == 200:
            # Get filename from Content-Disposition header or use default
            content_disposition = resp.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            else:
                filename = f"torrent_{torrent_id}.torrent"

            # Use provided output path or current directory
            if output_path:
                file_path = os.path.join(output_path, filename)
            else:
                file_path = filename

            # Write the file
            with open(file_path, 'wb') as f:
                f.write(resp.content)

            print(f"Torrent downloaded successfully.")
            print(f"Saved to: {os.path.abspath(file_path)}")
            print(f"File size: {len(resp.content)} bytes")
        else:
            print(f"FAIL: Expected 200, got {resp.status_code}")
            print(f"Response: {resp.text}")

    except Exception as e:
        print(f"ERROR: Failed to download torrent - {e}")

if __name__ == "__main__":
    while (True):
        command: str = input("register, login, users, update, upload, search, details, delete, download: ")

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

            case "upload":
                # username: str = input("Username: ")
                # password: str = input("Password: ")
                # token = login(username, password)

                token = login("theadministrator", "admin")

                if token:
                    file_path: str = input("File path: ")
                    description: str = input("Description (optional): ")
                    upload_torrent(token, file_path, description)

            case "search":
                # username: str = input("Username: ")
                # password: str = input("Password: ")
                # token = login(username, password)

                token = login("theadministrator", "admin")

                if token:
                    query: str = input("Search query: ")
                    limit: int = input("Limit (default 50): ") or "50"
                    search_torrents(token, query, int(limit))

            case "details":
                # username: str = input("Username: ")
                # password: str = input("Password: ")
                # token = login(username, password)

                token = login("theadministrator", "admin")

                if token:
                    torrent_id: int = input("Torrent ID: ")
                    get_torrent_details(token, int(torrent_id))

            case "delete":
                # username: str = input("Username: ")
                # password: str = input("Password: ")
                # token = login(username, password)

                token = login("theadministrator", "admin")

                if token:
                    torrent_id: int = input("Torrent ID to delete: ")
                    delete_torrent(token, int(torrent_id))

            case "download":
                # username: str = input("Username: ")
                # password: str = input("Password: ")
                # token = login(username, password)

                token = login("theadministrator", "admin")

                if token:
                    torrent_id: int = input("Torrent ID to download: ")
                    output_path: str = input("Output directory (default: current): ").strip()
                    output_path = output_path if output_path else None
                    download_torrent(token, int(torrent_id), output_path)

            case _:
                print("Unknown command. Exiting...")
                exit(0)
