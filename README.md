# Carbonio Files Bulk Downloader

A Python script to bulk download all files from **Carbonio Files** (formerly Zextras Drive) for multiple users using admin impersonation.

---

## 📋 Features

- Authenticates as admin via Carbonio Admin SOAP API (port 6071)
- Impersonates each user using `DelegateAuthRequest`
- Downloads all files from each user's Carbonio Files (Drive)
- Recursively downloads files inside folders
- Automatically adds correct file extensions based on MIME type
- Generates a summary report at the end
- Supports multiple domains/accounts in a single run

---

## 🖥️ Requirements

- Python 3.8+
- Carbonio Mail Server with Files module enabled
- Admin credentials with delegate auth permission
- Access to port 6071 (Carbonio Admin port)

---

## 📦 Installation

**1. Clone the repository:**

```bash
git clone https://github.com/Ranjithg123/carbonio-files-downloader.git
cd carbonio-files-downloader
```

**2. Create and activate a virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install requests
```

---

## ⚙️ Configuration

Edit the configuration section at the top of `carbonio_download.py`:

```python
BASE_URL      = "https://mail.yourdomain.com"         # Carbonio webmail URL
ADMIN_URL     = "https://mail.yourdomain.com:6071"    # Carbonio admin port
ADMIN_USER    = "zextras@yourdomain.com"              # Admin email
ADMIN_PASS    = "your_admin_password"                 # Admin password
ACCOUNTS_FILE = "./account.txt"                       # Path to accounts list
OUTPUT_DIR    = "./carbonio_files_download"           # Download destination
```

---

## 👥 accounts.txt Format

Create an `account.txt` file with one email address per line:

```
user1@yourdomain.com
user2@yourdomain.com
user3@anotherdomain.com
# This is a comment - lines starting with # are ignored
user4@yourdomain.com
```

---

## 🚀 Usage

```bash
python3 carbonio_download.py
```

### Example output:

```
[*] Carbonio Files Bulk Downloader
[*] Server     : https://mail.yourdomain.com
[*] Admin port : https://mail.yourdomain.com:6071
[*] Output     : ./carbonio_files_download

[*] Loaded 10 accounts from ./account.txt

[✓] Authenticated as admin: zextras@yourdomain.com

[1/10] Processing: user1@yourdomain.com
  ────────────────────────────────────────
    [↓] Book1.xlsx (7.9 KB)
    [↓] Report.pdf (1.2 MB)
  [→] Folder: Documents
    [↓] Invoice.docx (45.3 KB)
  [✓] 3 files (1.25 MB)

[2/10] Processing: user2@yourdomain.com
  ────────────────────────────────────────
  [~] No files found for user2@yourdomain.com

======================================================================
                             SUMMARY
======================================================================
  user1@yourdomain.com                    3 files      1.25 MB  [OK]
  user2@yourdomain.com                    0 files      0.00 MB  [OK]
======================================================================
  TOTAL                                   3 files      1.25 MB

[✓] All done! Files saved to: ./carbonio_files_download
```

---

## 📁 Output Structure

Files are saved under the `OUTPUT_DIR` folder, organized by user email:

```
carbonio_files_download/
    ├── user1@yourdomain.com/
    │   ├── Book1.xlsx
    │   ├── Report.pdf
    │   └── Documents/
    │       └── Invoice.docx
    ├── user2@yourdomain.com/
    │   └── Screenshot.png
    └── user3@anotherdomain.com/
        └── data.xlsx
```

---

## 🗂️ Supported File Types

|MIME Type|Extension|
|---|---|
|Excel Spreadsheet|`.xlsx`|
|Word Document|`.docx`|
|PowerPoint Presentation|`.pptx`|
|PDF|`.pdf`|
|PNG Image|`.png`|
|JPEG Image|`.jpg`|
|GIF Image|`.gif`|
|Plain Text|`.txt`|
|ZIP Archive|`.zip`|

> Other file types are downloaded without adding an extension.

---

## 🔧 How It Works

```
Admin Login (port 6071)
        │
        ▼
DelegateAuthRequest → Get user token
        │
        ▼
GraphQL API → List files (LOCAL_ROOT)
        │
        ▼
Recurse into folders
        │
        ▼
Download each file → Save to disk
```

1. Authenticates to the **Carbonio Admin SOAP API** on port `6071` using admin credentials
2. For each user in `account.txt`, performs a **DelegateAuthRequest** to get a user-scoped auth token
3. Uses the **Carbonio Files GraphQL API** to list all files and folders
4. Downloads each file using the **Files download endpoint**
5. Saves files to disk organized by user

---

## ⚠️ Known Limitations

- Maximum of **50 files per folder** per API call (Carbonio API limit)
- Files with more than 50 items in a single folder may not be fully downloaded (pagination support can be added if needed)
- SSL verification is disabled by default — set `session.verify = True` if you have a valid SSL certificate

---

## 🔒 Security Notes

- **Never commit your password** to the repository — use environment variables or a `.env` file
- Add `account.txt` to `.gitignore` if it contains sensitive email addresses
- Recommended `.gitignore`:

```
account.txt
carbonio_files_download/
venv/
__pycache__/
*.pyc
.env
```

---

## 🐛 Troubleshooting

| Error                        | Cause                               | Fix                                                              |
| ---------------------------- | ----------------------------------- | ---------------------------------------------------------------- |
| `422 Unprocessable Entity`   | Wrong SOAP endpoint or namespace    | Make sure `ADMIN_URL` uses port `6071` and `/service/admin/soap` |
| `HTTP 401`                   | Wrong admin credentials             | Check `ADMIN_USER` and `ADMIN_PASS`                              |
| `GraphQL errors`             | API schema mismatch                 | Check Carbonio version compatibility                             |
| `0 files found`              | User has no files in Carbonio Files | Normal — user simply has no uploads                              |
| `Connection refused on 6071` | Admin port blocked                  | Open port 6071 in firewall                                       |

---

## 📄 License

MIT License — feel free to use, modify, and distribute.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 📧 Contact

For issues or questions, open a GitHub issue or contact the repository maintainer.
