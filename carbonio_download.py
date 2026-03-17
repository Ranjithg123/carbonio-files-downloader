
#!/usr/bin/env python3
"""
Carbonio Files Bulk Downloader
Downloads Files for all users listed in account.txt using admin impersonation
"""

import requests
import os
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
BASE_URL      = "https://mail.yourdomain.com"         # Carbonio webmail URL
ADMIN_URL     = "https://mail.yourdomain.com:7071"    # Carbonio admin port
ADMIN_USER    = "zextras@yourdomain.com"              # Admin email
ADMIN_PASS    = "your_admin_password"                 # Admin password
ACCOUNTS_FILE = "./account.txt"                       # Path to accounts list
OUTPUT_DIR    = "./carbonio_files_download"           # Download destination
# ──────────────────────────────────────────────────────────────────────────────

FOLDER_TYPES = {"FOLDER", "ROOT"}

EXT_MAP = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "text/plain": ".txt",
    "application/zip": ".zip",
}

session = requests.Session()
session.verify = False

# ─── AUTH ─────────────────────────────────────────────────────────────────────

def get_admin_token():
    """Get admin auth token via admin port 7071"""
    url = f"{ADMIN_URL}/service/admin/soap"
    payload = {
        "Header": {"context": {"_jsns": "urn:zimbra"}},
        "Body": {
            "AuthRequest": {
                "_jsns": "urn:zimbraAdmin",
                "name": ADMIN_USER,
                "password": ADMIN_PASS
            }
        },
        "_jsns": "urn:zimbraSoap"
    }
    resp = session.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()

    if "Fault" in data.get("Body", {}):
        fault = data["Body"]["Fault"]["Reason"]["Text"]
        raise Exception(f"Admin auth failed: {fault}")

    token = data["Body"]["AuthResponse"]["authToken"][0]["_content"]
    print(f"[✓] Authenticated as admin: {ADMIN_USER}")
    return token


def get_user_token(admin_token, target_user):
    """Delegate auth as user via admin port 7071"""
    url = f"{ADMIN_URL}/service/admin/soap"
    payload = {
        "Header": {
            "context": {
                "_jsns": "urn:zimbra",
                "authToken": {"_content": admin_token}
            }
        },
        "Body": {
            "DelegateAuthRequest": {
                "_jsns": "urn:zimbraAdmin",
                "account": {"by": "name", "_content": target_user}
            }
        },
        "_jsns": "urn:zimbraSoap"
    }
    resp = session.post(url, json=payload)

    if resp.status_code != 200:
        print(f"  [!] HTTP {resp.status_code} for {target_user}")
        try:
            print(f"  [!] Response: {resp.json()}")
        except:
            print(f"  [!] Response: {resp.text[:200]}")
        return None

    data = resp.json()

    if "Fault" in data.get("Body", {}):
        fault = data["Body"]["Fault"]["Reason"]["Text"]
        print(f"  [!] Cannot impersonate {target_user}: {fault}")
        return None

    token = data["Body"]["DelegateAuthResponse"]["authToken"][0]["_content"]
    return token

# ─── GRAPHQL ──────────────────────────────────────────────────────────────────

def list_children(token, node_id="LOCAL_ROOT"):
    url = f"{BASE_URL}/services/files/graphql"
    headers = {
        "Cookie": f"ZM_AUTH_TOKEN={token}",
        "Content-Type": "application/json"
    }
    query = """
    query getChildren($node_id: ID!) {
        getNode(node_id: $node_id) {
            id
            name
            type
            ... on Folder {
                children(limit: 50, sort: NAME_ASC) {
                    nodes {
                        id
                        name
                        type
                        ... on File {
                            size
                            mime_type
                        }
                    }
                }
            }
        }
    }
    """
    payload = {
        "operationName": "getChildren",
        "variables": {"node_id": node_id},
        "query": query
    }
    resp = session.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        print(f"  [!] GraphQL error: {data['errors'][0]['message']}")
        return []

    node = data.get("data", {}).get("getNode", {})
    return node.get("children", {}).get("nodes", [])

# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────

def get_filename(node):
    name = node["name"]
    mime = node.get("mime_type", "")
    ext  = EXT_MAP.get(mime, "")
    if ext and not name.lower().endswith(ext):
        name = name + ext
    return name

def download_file(token, node_id, filename, output_dir):
    url = f"{BASE_URL}/services/files/download/{node_id}"
    headers = {"Cookie": f"ZM_AUTH_TOKEN={token}"}

    resp = session.get(url, headers=headers, stream=True)
    resp.raise_for_status()

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    size = 0
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            size += len(chunk)

    print(f"    [↓] {filename} ({size/1024:.1f} KB)")
    return size

def download_all(token, folder_id="LOCAL_ROOT", output_dir=OUTPUT_DIR, depth=0):
    nodes = list_children(token, folder_id)
    total_files = 0
    total_size  = 0

    for node in nodes:
        if node["type"] not in FOLDER_TYPES:
            filename = get_filename(node)
            size = download_file(token, node["id"], filename, output_dir)
            total_files += 1
            total_size  += size
        else:
            sub_dir = os.path.join(output_dir, node["name"])
            print(f"{'  '*depth}  [→] Folder: {node['name']}")
            f, s = download_all(token, node["id"], sub_dir, depth + 1)
            total_files += f
            total_size  += s

    return total_files, total_size

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def load_accounts(filepath):
    with open(filepath, "r") as f:
        accounts = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]
    return accounts

def main():
    print(f"[*] Carbonio Files Bulk Downloader")
    print(f"[*] Server     : {BASE_URL}")
    print(f"[*] Admin port : {ADMIN_URL}")
    print(f"[*] Output     : {OUTPUT_DIR}\n")

    if not os.path.exists(ACCOUNTS_FILE):
        print(f"[✗] Accounts file not found: {ACCOUNTS_FILE}")
        sys.exit(1)

    accounts = load_accounts(ACCOUNTS_FILE)
    print(f"[*] Loaded {len(accounts)} accounts from {ACCOUNTS_FILE}\n")

    try:
        admin_token = get_admin_token()
    except Exception as e:
        print(f"[✗] Admin auth failed: {e}")
        sys.exit(1)

    summary = []
    for i, user in enumerate(accounts, 1):
        print(f"\n[{i}/{len(accounts)}] Processing: {user}")
        print(f"  {'─'*40}")

        user_token = get_user_token(admin_token, user)
        if not user_token:
            summary.append((user, 0, 0, "FAILED - auth error"))
            continue

        user_dir = os.path.join(OUTPUT_DIR, user)
        try:
            files, size = download_all(user_token, "LOCAL_ROOT", user_dir)
            if files == 0:
                print(f"  [~] No files found for {user}")
            summary.append((user, files, size, "OK"))
            print(f"  [✓] {files} files ({size/1024/1024:.2f} MB)")
        except Exception as e:
            print(f"  [✗] Error: {e}")
            summary.append((user, 0, 0, f"FAILED - {e}"))

    print(f"\n{'='*70}")
    print(f"{'SUMMARY':^70}")
    print(f"{'='*70}")
    for user, files, size, status in summary:
        print(f"  {user:<42} {files:>4} files  {size/1024/1024:>8.2f} MB  [{status}]")
    print(f"{'='*70}")

    total_files = sum(f for _, f, _, _ in summary)
    total_size  = sum(s for _, _, s, _ in summary)
    print(f"  {'TOTAL':<42} {total_files:>4} files  {total_size/1024/1024:>8.2f} MB")
    print(f"\n[✓] All done! Files saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
