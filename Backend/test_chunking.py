# -*- coding: utf-8 -*-
"""
Document Text Chunking Module -- API Test Suite
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
    print("  Document Text Chunking -- API Test Suite")
    print(SEP)

    # 1. Setup Users
    print("\n-- SETUP --")
    ensure_user("chunker_a", "chunk_a@example.com", "securepass123")
    ensure_user("chunker_b", "chunk_b@example.com", "securepass123")
    token_a = login("chunker_a", "securepass123")
    token_b = login("chunker_b", "securepass123")
    print(f"{INFO}  Tokens acquired successfully")

    total_assertions = 0
    passed_assertions = 0

    def assert_status(label, r, expected_status):
        nonlocal total_assertions, passed_assertions
        total_assertions += 1
        if check(label, r, expected_status):
            passed_assertions += 1
            return True
        return False

    def assert_true(label, condition, details=""):
        nonlocal total_assertions, passed_assertions
        total_assertions += 1
        if condition:
            passed_assertions += 1
            print(f"{PASS}  {label}")
            return True
        else:
            print(f"{FAIL}  {label} {details}")
            return False

    # 2. Test Small Text -> 1 Chunk
    print("\n-- Test 1: Small Text (1 Chunk) --")
    small_txt = "Short document content for chunking."
    r_up = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("small.txt", small_txt.encode("utf-8"), "text/plain")})
    assert_status("Upload small.txt", r_up, {201})
    doc_small_id = r_up.json()["id"]

    r_proc = requests.post(f"{BASE_URL}/documents/{doc_small_id}/process", headers=hdrs(token_a))
    assert_status("Process small.txt", r_proc, {200})

    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_small_id}/chunk", headers=hdrs(token_a))
    assert_status("Chunk small.txt", r_chunk, {200})
    if r_chunk.status_code == 200:
        c_data = r_chunk.json()
        assert_true("Small text total_chunks == 1", c_data.get("total_chunks") == 1)
        assert_true("Chunk index 0", c_data["chunks"][0]["chunk_index"] == 0)
        assert_true("Chunk text matches source", c_data["chunks"][0]["text"] == small_txt)

    # 3. Test Large Text -> Multiple Chunks with Overlap
    print("\n-- Test 2: Large Text (Multiple Chunks) --")
    paragraphs = [f"Paragraph {i}: " + ("This is detailed test content for enterprise chunking pipeline verification. " * 5) for i in range(1, 15)]
    large_txt = "\n\n".join(paragraphs)
    r_up = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("large.txt", large_txt.encode("utf-8"), "text/plain")})
    assert_status("Upload large.txt", r_up, {201})
    doc_large_id = r_up.json()["id"]

    r_proc = requests.post(f"{BASE_URL}/documents/{doc_large_id}/process", headers=hdrs(token_a))
    assert_status("Process large.txt", r_proc, {200})

    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_large_id}/chunk?chunk_size=400&chunk_overlap=80", headers=hdrs(token_a))
    assert_status("Chunk large.txt (size=400, overlap=80)", r_chunk, {200})
    if r_chunk.status_code == 200:
        c_data = r_chunk.json()
        total_c = c_data.get("total_chunks", 0)
        assert_true("Multiple chunks created (> 1)", total_c > 1, f"got total_chunks={total_c}")
        
        # Verify sequential indexes
        indexes = [c["chunk_index"] for c in c_data["chunks"]]
        expected_indexes = list(range(total_c))
        assert_true("Sequential indexes starting at 0", indexes == expected_indexes)
        
        # Verify chunks non-empty
        all_non_empty = all(len(c["text"].strip()) > 0 for c in c_data["chunks"])
        assert_true("All chunks non-empty", all_non_empty)

    # 4. Test MD File Chunking
    print("\n-- Test 3: Markdown File Chunking --")
    md_body = "# Enterprise Architecture\n\nSection 1: Overview\nDetails regarding enterprise architecture.\n\nSection 2: Security\nRole based access control details."
    r_up = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("doc.md", md_body.encode("utf-8"), "text/plain")})
    assert_status("Upload doc.md", r_up, {201})
    doc_md_id = r_up.json()["id"]
    requests.post(f"{BASE_URL}/documents/{doc_md_id}/process", headers=hdrs(token_a))

    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_md_id}/chunk", headers=hdrs(token_a))
    assert_status("Chunk doc.md", r_chunk, {200})
    if r_chunk.status_code == 200:
        assert_true("MD chunks > 0", r_chunk.json().get("total_chunks", 0) > 0)

    # 5. Test PDF File Chunking
    print("\n-- Test 4: PDF File Chunking --")
    pdf_txt = "Hello PDF Chunking Test"
    r_up = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("doc.pdf", build_pdf_bytes(pdf_txt), "application/pdf")})
    assert_status("Upload doc.pdf", r_up, {201})
    doc_pdf_id = r_up.json()["id"]
    requests.post(f"{BASE_URL}/documents/{doc_pdf_id}/process", headers=hdrs(token_a))

    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_pdf_id}/chunk", headers=hdrs(token_a))
    assert_status("Chunk doc.pdf", r_chunk, {200})
    if r_chunk.status_code == 200:
        assert_true("PDF chunks contains 'Hello PDF'", pdf_txt in r_chunk.json()["chunks"][0]["text"])

    # 6. Test DOCX File Chunking
    print("\n-- Test 5: DOCX File Chunking --")
    docx_txt = "Hello DOCX Chunking Test Content"
    r_up = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("doc.docx", build_docx_bytes(docx_txt), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert_status("Upload doc.docx", r_up, {201})
    doc_docx_id = r_up.json()["id"]
    requests.post(f"{BASE_URL}/documents/{doc_docx_id}/process", headers=hdrs(token_a))

    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_docx_id}/chunk", headers=hdrs(token_a))
    assert_status("Chunk doc.docx", r_chunk, {200})
    if r_chunk.status_code == 200:
        assert_true("DOCX chunks contains text", docx_txt in r_chunk.json()["chunks"][0]["text"])

    # 7. Test Chunking Unprocessed Document
    print("\n-- Test 6: Chunk Unprocessed Document --")
    r_up = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a),
        files={"file": ("unprocessed.txt", b"Unprocessed content", "text/plain")})
    assert_status("Upload unprocessed.txt", r_up, {201})
    doc_unproc_id = r_up.json()["id"]

    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_unproc_id}/chunk", headers=hdrs(token_a))
    assert_status("Chunk unprocessed doc (expect 400)", r_chunk, {400})

    # 8. Test Invalid Parameters
    print("\n-- Test 7: Invalid Parameters --")
    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_small_id}/chunk?chunk_size=100&chunk_overlap=150", headers=hdrs(token_a))
    assert_status("Overlap >= Chunk size (expect 400)", r_chunk, {400})

    # 9. Test Security & Ownership Isolation
    print("\n-- Test 8: Security & Ownership Isolation --")
    r_chunk_b = requests.post(f"{BASE_URL}/documents/{doc_small_id}/chunk", headers=hdrs(token_b))
    assert_status("User B chunk User A's doc (expect 404)", r_chunk_b, {404})

    r_get_b = requests.get(f"{BASE_URL}/documents/{doc_small_id}/chunks", headers=hdrs(token_b))
    assert_status("User B list User A's chunks (expect 404)", r_get_b, {404})

    # 10. Test GET /documents/{id}/chunks
    print("\n-- Test 9: GET /documents/{id}/chunks --")
    r_get_a = requests.get(f"{BASE_URL}/documents/{doc_large_id}/chunks", headers=hdrs(token_a))
    assert_status("GET User A's chunks", r_get_a, {200})
    if r_get_a.status_code == 200:
        c_data = r_get_a.json()
        assert_true("Retrieved document_id matches", c_data.get("document_id") == doc_large_id)
        assert_true("Retrieved total_chunks > 0", c_data.get("total_chunks", 0) > 0)

    # 11. Test Duplicate Prevention (Atomic Replacement)
    print("\n-- Test 10: Duplicate Prevention / Re-chunking --")
    r_rechunk1 = requests.post(f"{BASE_URL}/documents/{doc_small_id}/chunk", headers=hdrs(token_a))
    assert_status("First chunking call", r_rechunk1, {200})
    count1 = r_rechunk1.json().get("total_chunks")

    r_rechunk2 = requests.post(f"{BASE_URL}/documents/{doc_small_id}/chunk", headers=hdrs(token_a))
    assert_status("Second chunking call", r_rechunk2, {200})
    count2 = r_rechunk2.json().get("total_chunks")

    assert_true("Re-chunking does not duplicate chunks", count1 == count2)

    r_verify_get = requests.get(f"{BASE_URL}/documents/{doc_small_id}/chunks", headers=hdrs(token_a))
    assert_true("GET chunks count remains consistent", r_verify_get.json().get("total_chunks") == count1)

    # 12. Test Unauthenticated Requests
    print("\n-- Test 11: Unauthenticated Requests --")
    r_unauth1 = requests.post(f"{BASE_URL}/documents/{doc_small_id}/chunk")
    assert_status("Unauthenticated POST chunk (expect 401)", r_unauth1, {401})

    r_unauth2 = requests.get(f"{BASE_URL}/documents/{doc_small_id}/chunks")
    assert_status("Unauthenticated GET chunks (expect 401)", r_unauth2, {401})

    # Summary
    print(f"\n{SEP}")
    print("  SUMMARY OF ASSERTIONS")
    print(f"  Total assertions: {total_assertions}")
    print(f"  Passed assertions: {passed_assertions}")
    print(f"  Failed assertions: {total_assertions - passed_assertions}")
    print(SEP)

    if total_assertions == passed_assertions:
        print(f"{SUCCESS} All chunking tests passed successfully!")
    else:
        print(f"{ERROR} Some chunking tests failed.")

if __name__ == "__main__":
    run_tests()
