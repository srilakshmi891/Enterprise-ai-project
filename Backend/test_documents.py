# -*- coding: utf-8 -*-
"""
Document Upload Module -- Full API Test Suite
ASCII-only output for Windows compatibility.
"""
import io
import json
import zipfile

import requests

BASE_URL = "http://127.0.0.1:8001"

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"
SEP  = "=" * 60


def login(username, password):
    r = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    return r.json()["access_token"]


def hdrs(token):
    return {"Authorization": f"Bearer {token}"}


def check(label, r, expected):
    if r.status_code in expected:
        print(f"{PASS}  {label}  ->  HTTP {r.status_code}")
        return True
    else:
        print(f"{FAIL}  {label}  ->  HTTP {r.status_code}  (expected {expected})")
        print(f"       Body: {r.text[:200]}")
        return False


def ensure_user(username, email, password):
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "username": username, "email": email,
        "password": password, "name": username,
    })
    if r.status_code == 201:
        print(f"{INFO}  Registered: {username}")
    elif "already" in r.text.lower():
        print(f"{INFO}  Already exists: {username}")
    else:
        print(f"{INFO}  Register {username}: HTTP {r.status_code}  {r.text[:80]}")


# ---------------------------------------------------------------------------
print(SEP)
print("  Document Upload Module -- API Test Suite")
print(SEP)

# Setup
print("\n-- SETUP --")
ensure_user("testuser_a", "usera_doc@example.com", "password123")
ensure_user("testuser_b", "userb_doc@example.com", "password123")
token_a = login("testuser_a", "password123")
token_b = login("testuser_b", "password123")
print(f"{INFO}  Tokens acquired for User A and User B")

# Test 1 -- Upload TXT
print("\n-- Test 1: Upload TXT --")
r = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
    files={"file": ("test.txt", b"Hello world", "text/plain")})
check("Upload TXT", r, {201})
doc_txt = r.json() if r.status_code == 201 else {}
doc_id_a = doc_txt.get("id")
print(f"{INFO}  doc_id={doc_id_a}  filename={doc_txt.get('filename')}  size={doc_txt.get('file_size')}  status={doc_txt.get('status')}")

# Test 2 -- Upload Markdown
print("\n-- Test 2: Upload Markdown --")
r = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
    files={"file": ("readme.md", b"# Hello", "text/plain")})
check("Upload MD", r, {201})
doc_md = r.json() if r.status_code == 201 else {}
print(f"{INFO}  doc_id={doc_md.get('id')}  filename={doc_md.get('filename')}")

# Test 3 -- Upload PDF
print("\n-- Test 3: Upload PDF --")
pdf_bytes = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
    b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj "
    b"xref\n0 4\n0000000000 65535 f \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n9\n%%EOF"
)
r = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
    files={"file": ("report.pdf", pdf_bytes, "application/pdf")})
check("Upload PDF", r, {201})
doc_pdf = r.json() if r.status_code == 201 else {}
doc_id_pdf = doc_pdf.get("id")
print(f"{INFO}  doc_id={doc_id_pdf}  filename={doc_pdf.get('filename')}")

# Test 4 -- Upload DOCX
print("\n-- Test 4: Upload DOCX --")
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("[Content_Types].xml",
        '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '</Types>')
    z.writestr("word/document.xml",
        '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>Test DOCX</w:t></w:r></w:p></w:body></w:document>')
docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
r = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
    files={"file": ("notes.docx", buf.getvalue(), docx_mime)})
check("Upload DOCX", r, {201})
doc_docx = r.json() if r.status_code == 201 else {}
print(f"{INFO}  doc_id={doc_docx.get('id')}  filename={doc_docx.get('filename')}")

# Test 5 -- Unsupported file type
print("\n-- Test 5: Unsupported file type (.exe) --")
r = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
    files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")})
check("Reject .exe (expect 400)", r, {400})

# Test 6 -- File too large
print("\n-- Test 6: File too large (11 MB TXT) --")
big = b"x" * (11 * 1024 * 1024)
r = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
    files={"file": ("huge.txt", big, "text/plain")})
check("Reject oversized file (expect 413)", r, {413})

# Test 7 -- List documents
print("\n-- Test 7: GET /documents (list) --")
r = requests.get(f"{BASE_URL}/documents", headers=hdrs(token_a))
check("List documents", r, {200})
data = r.json()
print(f"{INFO}  total={data.get('total')}  page={data.get('page')}  per_page={data.get('per_page')}")

# Test 8 -- Document detail
print(f"\n-- Test 8: GET /documents/{doc_id_a} (detail) --")
r = requests.get(f"{BASE_URL}/documents/{doc_id_a}", headers=hdrs(token_a))
check("Document detail", r, {200})
print(f"{INFO}  {json.dumps(r.json(), default=str)[:200]}")

# Test 9 -- Download
print(f"\n-- Test 9: GET /documents/{doc_id_a}/download --")
r = requests.get(f"{BASE_URL}/documents/{doc_id_a}/download", headers=hdrs(token_a))
check("Download document", r, {200})
print(f"{INFO}  content-length={len(r.content)} bytes")

# Test 10 -- Delete
print(f"\n-- Test 10: DELETE /documents/{doc_id_pdf} --")
r = requests.delete(f"{BASE_URL}/documents/{doc_id_pdf}", headers=hdrs(token_a))
check("Delete document (expect 204)", r, {204})

# Test 11 -- Unauthenticated
print("\n-- Test 11: GET /documents without auth (expect 401) --")
r = requests.get(f"{BASE_URL}/documents")
check("Unauthenticated rejected", r, {401})

# SECURITY -- Multi-user ownership
print(f"\n-- SECURITY: User B tries User A doc (id={doc_id_a}) --")
r = requests.get(f"{BASE_URL}/documents/{doc_id_a}", headers=hdrs(token_b))
check("User B GET User A doc (expect 404)", r, {403, 404})

r = requests.get(f"{BASE_URL}/documents/{doc_id_a}/download", headers=hdrs(token_b))
check("User B DOWNLOAD User A doc (expect 404)", r, {403, 404})

r = requests.delete(f"{BASE_URL}/documents/{doc_id_a}", headers=hdrs(token_b))
check("User B DELETE User A doc (expect 404)", r, {403, 404})

r = requests.get(f"{BASE_URL}/documents", headers=hdrs(token_b))
check("User B list (expect 200)", r, {200})
print(f"{INFO}  User B total docs={r.json().get('total')} (expected 0)")

# REGRESSION
print("\n-- REGRESSION: Existing endpoints --")
r = requests.get(f"{BASE_URL}/auth/me", headers=hdrs(token_a))
check("/auth/me", r, {200})

print(f"\n{SEP}")
print("  Test run complete.")
print(SEP)
