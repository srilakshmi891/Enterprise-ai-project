# -*- coding: utf-8 -*-
"""
Document Text Extraction Module -- API Test Suite
ASCII-only output for Windows compatibility.
"""
import io
import json
import requests
import docx

BASE_URL = "http://127.0.0.1:8001"

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"
SUCCESS = "[SUCCESS]"
ERROR = "[ERROR]"
SEP = "=" * 60

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

def check(label, r, expected_status):
    if r.status_code in expected_status:
        print(f"{PASS}  {label}  ->  HTTP {r.status_code}")
        return True
    else:
        print(f"{FAIL}  {label}  ->  HTTP {r.status_code}  (expected {expected_status})")
        print(f"       Body: {r.text[:300]}")
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

def build_docx_bytes(text):
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def build_pdf_bytes(text):
    # A simple valid PDF containing Helvetica text
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
        b"3 0 obj\n<</Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 595 842] /Contents 4 0 R>>\nendobj\n"
        b"4 0 obj\n<</Length 43>>\nstream\n"
        b"BT\n/F1 12 Tf\n72 712 Td\n(" + text.encode("ascii", "ignore") + b") Tj\nET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000056 00000 n \n"
        b"0000000111 00000 n \n"
        b"0000000282 00000 n \n"
        b"trailer\n<</Size 5 /Root 1 0 R>>\n"
        b"startxref\n376\n%%EOF\n"
    )

def run_tests():
    print(SEP)
    print("  Document Text Extraction -- API Test Suite")
    print(SEP)

    # 1. Setup Users
    print("\n-- SETUP --")
    ensure_user("extractor_a", "ext_a@example.com", "securepass123")
    ensure_user("extractor_b", "ext_b@example.com", "securepass123")
    token_a = login("extractor_a", "securepass123")
    token_b = login("extractor_b", "securepass123")
    print(f"{INFO}  Tokens acquired successfully")

    # Tracking test results
    total_assertions = 0
    passed_assertions = 0

    def assert_status(label, r, expected_status):
        nonlocal total_assertions, passed_assertions
        total_assertions += 1
        if check(label, r, expected_status):
            passed_assertions += 1
            return True
        return False

    # 2. Test TXT Extraction
    print("\n-- Test: TXT Extraction --")
    txt_content = "Hello from TXT extraction test!"
    r_upload = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("test.txt", txt_content.encode("utf-8"), "text/plain")})
    assert_status("Upload TXT", r_upload, {201})
    doc_txt = r_upload.json()
    doc_id_txt = doc_txt.get("id")

    r_process = requests.post(f"{BASE_URL}/documents/{doc_id_txt}/process", headers=hdrs(token_a))
    assert_status("Process TXT", r_process, {200})
    if r_process.status_code == 200:
        data = r_process.json()
        assert_status("TXT status processed", r_process, {200})
        total_assertions += 1
        if data.get("status") == "processed":
            passed_assertions += 1
            print(f"{PASS}  TXT status is processed")
        else:
            print(f"{FAIL}  TXT status is {data.get('status')}")

        total_assertions += 1
        if data.get("extracted_text") == txt_content:
            passed_assertions += 1
            print(f"{PASS}  TXT extracted text matches exactly")
        else:
            print(f"{FAIL}  TXT extracted text mismatch: Got {repr(data.get('extracted_text'))}")

    # Test GET extracted text
    r_text = requests.get(f"{BASE_URL}/documents/{doc_id_txt}/text", headers=hdrs(token_a))
    assert_status("Retrieve TXT text", r_text, {200})
    if r_text.status_code == 200:
        total_assertions += 1
        if r_text.json().get("extracted_text") == txt_content:
            passed_assertions += 1
            print(f"{PASS}  TXT retrieved text matches exactly")
        else:
            print(f"{FAIL}  TXT retrieved text mismatch")

    # 3. Test MD Extraction
    print("\n-- Test: MD Extraction --")
    md_content = "# Title\nParagraph content in markdown."
    r_upload = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("test.md", md_content.encode("utf-8"), "text/plain")})
    assert_status("Upload MD", r_upload, {201})
    doc_md = r_upload.json()
    doc_id_md = doc_md.get("id")

    r_process = requests.post(f"{BASE_URL}/documents/{doc_id_md}/process", headers=hdrs(token_a))
    assert_status("Process MD", r_process, {200})
    if r_process.status_code == 200:
        data = r_process.json()
        total_assertions += 1
        if data.get("extracted_text") == md_content:
            passed_assertions += 1
            print(f"{PASS}  MD extracted text matches exactly")
        else:
            print(f"{FAIL}  MD extracted text mismatch: Got {repr(data.get('extracted_text'))}")

    # 4. Test PDF Extraction
    print("\n-- Test: PDF Extraction --")
    pdf_text = "Hello PDF"
    r_upload = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("test.pdf", build_pdf_bytes(pdf_text), "application/pdf")})
    assert_status("Upload PDF", r_upload, {201})
    doc_pdf = r_upload.json()
    doc_id_pdf = doc_pdf.get("id")

    r_process = requests.post(f"{BASE_URL}/documents/{doc_id_pdf}/process", headers=hdrs(token_a))
    assert_status("Process PDF", r_process, {200})
    if r_process.status_code == 200:
        data = r_process.json()
        total_assertions += 1
        if pdf_text in data.get("extracted_text", ""):
            passed_assertions += 1
            print(f"{PASS}  PDF extracted text contains '{pdf_text}'")
        else:
            print(f"{FAIL}  PDF extracted text mismatch: Got {repr(data.get('extracted_text'))}")

    # 5. Test DOCX Extraction
    print("\n-- Test: DOCX Extraction --")
    docx_text = "Hello DOCX text content"
    r_upload = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("test.docx", build_docx_bytes(docx_text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert_status("Upload DOCX", r_upload, {201})
    doc_docx = r_upload.json()
    doc_id_docx = doc_docx.get("id")

    r_process = requests.post(f"{BASE_URL}/documents/{doc_id_docx}/process", headers=hdrs(token_a))
    assert_status("Process DOCX", r_process, {200})
    if r_process.status_code == 200:
        data = r_process.json()
        total_assertions += 1
        if docx_text in data.get("extracted_text", ""):
            passed_assertions += 1
            print(f"{PASS}  DOCX extracted text contains '{docx_text}'")
        else:
            print(f"{FAIL}  DOCX extracted text mismatch: Got {repr(data.get('extracted_text'))}")

    # 6. Test Invalid/Corrupt Document Handling
    print("\n-- Test: Invalid/Corrupt Document Handling --")
    # Upload corrupt pdf (contains text instead of pdf structure)
    r_upload = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("corrupt.pdf", b"this is random non-pdf garbage text", "application/pdf")})
    assert_status("Upload Corrupt PDF", r_upload, {201})
    doc_corrupt = r_upload.json()
    doc_id_corrupt = doc_corrupt.get("id")

    r_process = requests.post(f"{BASE_URL}/documents/{doc_id_corrupt}/process", headers=hdrs(token_a))
    assert_status("Process Corrupt PDF (expect 500)", r_process, {500})
    
    # Check that status changed to failed
    r_detail = requests.get(f"{BASE_URL}/documents/{doc_id_corrupt}", headers=hdrs(token_a))
    assert_status("Get Corrupt Doc Detail", r_detail, {200})
    if r_detail.status_code == 200:
        total_assertions += 1
        if r_detail.json().get("status") == "failed":
            passed_assertions += 1
            print(f"{PASS}  Corrupt PDF status successfully transitioned to 'failed'")
        else:
            print(f"{FAIL}  Corrupt PDF status was expected to be 'failed', got: {r_detail.json().get('status')}")

    # 7. Test Missing Document
    print("\n-- Test: Missing Document --")
    r_process = requests.post(f"{BASE_URL}/documents/999999/process", headers=hdrs(token_a))
    assert_status("Process Non-existent ID (expect 404)", r_process, {404})

    # 8. Test Unauthenticated Processing
    print("\n-- Test: Unauthenticated Processing --")
    r_process = requests.post(f"{BASE_URL}/documents/{doc_id_txt}/process")
    assert_status("Process without token (expect 401)", r_process, {401})

    # 9. Test User B attempting to process User A's document
    print("\n-- Test: Ownership - Process User A's Doc by User B --")
    r_process = requests.post(f"{BASE_URL}/documents/{doc_id_txt}/process", headers=hdrs(token_b))
    assert_status("User B processing User A's doc (expect 404)", r_process, {404})

    # 10. Test User B attempting to retrieve User A's extracted text
    print("\n-- Test: Ownership - Retrieve User A's Text by User B --")
    r_text = requests.get(f"{BASE_URL}/documents/{doc_id_txt}/text", headers=hdrs(token_b))
    assert_status("User B retrieving User A's text (expect 404)", r_text, {404})

    # 11. Regression Endpoint Verification
    print("\n-- REGRESSION: Verify all basic endpoints --")
    # me
    r_me = requests.get(f"{BASE_URL}/auth/me", headers=hdrs(token_a))
    assert_status("GET /auth/me", r_me, {200})
    # document detail
    r_detail = requests.get(f"{BASE_URL}/documents/{doc_id_txt}", headers=hdrs(token_a))
    assert_status("GET /documents/{id}", r_detail, {200})
    # document download
    r_dl = requests.get(f"{BASE_URL}/documents/{doc_id_txt}/download", headers=hdrs(token_a))
    assert_status("GET /documents/{id}/download", r_dl, {200})
    # delete
    r_del = requests.delete(f"{BASE_URL}/documents/{doc_id_txt}", headers=hdrs(token_a))
    assert_status("DELETE /documents/{id}", r_del, {204})

    print(f"\n{SEP}")
    print("  SUMMARY OF ASSERTIONS")
    print(f"  Total assertions: {total_assertions}")
    print(f"  Passed assertions: {passed_assertions}")
    print(f"  Failed assertions: {total_assertions - passed_assertions}")
    print(SEP)

    if total_assertions == passed_assertions:
        print(f"{SUCCESS} All tests passed successfully!")
    else:
        print(f"{ERROR} Some tests failed.")

if __name__ == "__main__":
    run_tests()
