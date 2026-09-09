# -*- coding: utf-8 -*-
"""
ChromaDB Vector Database & Search Integration -- API Test Suite
ASCII-only output for Windows compatibility.
"""
import io
import time
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


def setup_document(token, filename, content, mime_type):
    # 1. Upload
    r_up = requests.post(
        f"{BASE_URL}/documents/upload",
        headers=hdrs(token),
        files={"file": (filename, content, mime_type)}
    )
    assert r_up.status_code == 201, f"Upload failed: {r_up.text}"
    doc_id = r_up.json()["id"]

    # 2. Process
    r_proc = requests.post(f"{BASE_URL}/documents/{doc_id}/process", headers=hdrs(token))
    assert r_proc.status_code == 200, f"Process failed: {r_proc.text}"

    # 3. Chunk
    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_id}/chunk", headers=hdrs(token))
    assert r_chunk.status_code == 200, f"Chunk failed: {r_chunk.text}"

    # 4. Embed
    r_embed = requests.post(f"{BASE_URL}/documents/{doc_id}/embed", headers=hdrs(token))
    assert r_embed.status_code == 200, f"Embed failed: {r_embed.text}"

    return doc_id


def run_tests():
    print(SEP)
    print("  ChromaDB Vector Database & Search -- API Test Suite")
    print(SEP)

    # Setup Users
    print("\n-- SETUP --")
    ts = int(time.time())
    user_a_name = f"chroma_user_a_{ts}"
    user_b_name = f"chroma_user_b_{ts}"
    ensure_user(user_a_name, f"{user_a_name}@example.com", "securepass123")
    ensure_user(user_b_name, f"{user_b_name}@example.com", "securepass123")
    token_a = login(user_a_name, "securepass123")
    token_b = login(user_b_name, "securepass123")
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

    # 1. Basic Indexing Test
    print("\n-- Test 1: Basic Indexing --")
    txt_a = "Machine learning model evaluation techniques include cross validation and accuracy metrics."
    doc_a_id = setup_document(token_a, "ml_eval.txt", txt_a.encode("utf-8"), "text/plain")

    r_idx = requests.post(f"{BASE_URL}/documents/{doc_a_id}/index", headers=hdrs(token_a))
    assert_status("Index ml_eval.txt into ChromaDB", r_idx, {200})
    if r_idx.status_code == 200:
        data = r_idx.json()
        assert_true("Index response document_id matches", data.get("document_id") == doc_a_id)
        assert_true("Index response indexed_chunks == 1", data.get("indexed_chunks") == 1)
        assert_true("Collection name is document_chunks", data.get("collection") == "document_chunks")
        assert_true("Status is indexed", data.get("status") == "indexed")

    # 2. Idempotency / Duplicate Prevention Test
    print("\n-- Test 2: Idempotency (Re-indexing) --")
    r_idx2 = requests.post(f"{BASE_URL}/documents/{doc_a_id}/index", headers=hdrs(token_a))
    assert_status("Re-index document (idempotent)", r_idx2, {200})
    if r_idx2.status_code == 200:
        assert_true("Re-indexed chunk count remains 1", r_idx2.json().get("indexed_chunks") == 1)

    # 3. Basic Vector Search Test
    print("\n-- Test 3: Semantic Vector Search --")
    r_srch = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_a),
        json={"query": "What is cross validation model evaluation?", "top_k": 5}
    )
    assert_status("POST /search query", r_srch, {200})
    if r_srch.status_code == 200:
        s_data = r_srch.json()
        assert_true("Query returned in response", s_data.get("query") == "What is cross validation model evaluation?")
        results = s_data.get("results", [])
        assert_true("Search results list non-empty", len(results) > 0)
        if results:
            first = results[0]
            assert_true("Result contains correct document_id", first.get("document_id") == doc_a_id)
            assert_true("Result contains filename", first.get("filename") == "ml_eval.txt")
            assert_true("Result distance is float", isinstance(first.get("distance"), float))

    # 4. Top_K Parameter & Validation
    print("\n-- Test 4: Top_K Validation --")
    r_topk = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_a),
        json={"query": "evaluation", "top_k": 2}
    )
    assert_status("POST /search top_k=2", r_topk, {200})
    if r_topk.status_code == 200:
        assert_true("Results length <= top_k (2)", len(r_topk.json().get("results", [])) <= 2)

    r_topk_invalid = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_a),
        json={"query": "test", "top_k": 0}
    )
    assert_status("Reject top_k=0 (expect 422)", r_topk_invalid, {422})

    # 5. User Isolation Security Test
    print("\n-- Test 5: Strict User Isolation --")
    txt_b = "Quantum computing algorithms utilize qubits and superposition."
    doc_b_id = setup_document(token_b, "quantum.txt", txt_b.encode("utf-8"), "text/plain")
    r_idx_b = requests.post(f"{BASE_URL}/documents/{doc_b_id}/index", headers=hdrs(token_b))
    assert_status("User B index quantum.txt", r_idx_b, {200})

    # User A searches for quantum computing
    r_srch_a = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_a),
        json={"query": "qubits superposition quantum computing", "top_k": 5}
    )
    assert_status("User A search query", r_srch_a, {200})
    if r_srch_a.status_code == 200:
        results_a = r_srch_a.json().get("results", [])
        user_b_docs_in_a = [r for r in results_a if r["document_id"] == doc_b_id]
        assert_true("User B's document NEVER appears in User A search results", len(user_b_docs_in_a) == 0)

    # User B searches for machine learning
    r_srch_b = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_b),
        json={"query": "machine learning cross validation", "top_k": 5}
    )
    assert_status("User B search query", r_srch_b, {200})
    if r_srch_b.status_code == 200:
        results_b = r_srch_b.json().get("results", [])
        user_a_docs_in_b = [r for r in results_b if r["document_id"] == doc_a_id]
        assert_true("User A's document NEVER appears in User B search results", len(user_a_docs_in_b) == 0)

    # 6. Document-Specific Search Filter
    print("\n-- Test 6: Document Filter Search --")
    r_doc_filter = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_a),
        json={"query": "evaluation", "top_k": 5, "document_id": doc_a_id}
    )
    assert_status("Search with document_id filter", r_doc_filter, {200})
    if r_doc_filter.status_code == 200:
        res_filter = r_doc_filter.json().get("results", [])
        all_match_doc = all(r["document_id"] == doc_a_id for r in res_filter)
        assert_true("All filtered results match requested document_id", all_match_doc)

    # 7. Ownership Enforcement & 404s
    print("\n-- Test 7: Ownership Enforcement --")
    r_unauth_idx = requests.post(f"{BASE_URL}/documents/{doc_a_id}/index", headers=hdrs(token_b))
    assert_status("User B index User A doc (expect 404)", r_unauth_idx, {404})

    r_unauth_srch_doc = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_b),
        json={"query": "evaluation", "top_k": 5, "document_id": doc_a_id}
    )
    assert_status("User B search User A doc filter (expect 404)", r_unauth_srch_doc, {404})

    # 8. Unauthenticated Requests
    print("\n-- Test 8: Unauthenticated Requests --")
    r_noauth_idx = requests.post(f"{BASE_URL}/documents/{doc_a_id}/index")
    assert_status("Unauth POST /index (expect 401)", r_noauth_idx, {401})

    r_noauth_srch = requests.post(f"{BASE_URL}/search", json={"query": "test"})
    assert_status("Unauth POST /search (expect 401)", r_noauth_srch, {401})

    # 9. Invalid State Errors (Missing chunks / missing embeddings)
    print("\n-- Test 9: Invalid State Indexing --")
    # Upload and process, but no chunk
    r_up_nochunk = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a), files={"file": ("nochunk.txt", b"No chunks", "text/plain")})
    doc_nochunk_id = r_up_nochunk.json()["id"]
    requests.post(f"{BASE_URL}/documents/{doc_nochunk_id}/process", headers=hdrs(token_a))

    r_idx_nochunk = requests.post(f"{BASE_URL}/documents/{doc_nochunk_id}/index", headers=hdrs(token_a))
    assert_status("Index document without chunks (expect 400)", r_idx_nochunk, {400})

    # Upload, process, chunk, but no embed
    r_up_noembed = requests.post(f"{BASE_URL}/documents/upload", headers=hdrs(token_a), files={"file": ("noembed.txt", b"No embed", "text/plain")})
    doc_noembed_id = r_up_noembed.json()["id"]
    requests.post(f"{BASE_URL}/documents/{doc_noembed_id}/process", headers=hdrs(token_a))
    requests.post(f"{BASE_URL}/documents/{doc_noembed_id}/chunk", headers=hdrs(token_a))

    r_idx_noembed = requests.post(f"{BASE_URL}/documents/{doc_noembed_id}/index", headers=hdrs(token_a))
    assert_status("Index document without embeddings (expect 400)", r_idx_noembed, {400})

    # 10. Vector Deletion Test
    print("\n-- Test 10: Vector Deletion on Document DELETE --")
    # Delete doc_b_id
    r_del_b = requests.delete(f"{BASE_URL}/documents/{doc_b_id}", headers=hdrs(token_b))
    assert_status("User B delete document", r_del_b, {204})

    # User B searches again -> should be empty
    r_srch_del = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_b),
        json={"query": "qubits quantum computing", "top_k": 5}
    )
    assert_status("User B search after deletion", r_srch_del, {200})
    if r_srch_del.status_code == 200:
        results_del = r_srch_del.json().get("results", [])
        assert_true("Deleted document vectors removed from ChromaDB", len(results_del) == 0)

    # Summary
    print(f"\n{SEP}")
    print("  SUMMARY OF ASSERTIONS")
    print(f"  Total assertions: {total_assertions}")
    print(f"  Passed assertions: {passed_assertions}")
    print(f"  Failed assertions: {total_assertions - passed_assertions}")
    print(SEP)

    if total_assertions == passed_assertions:
        print(f"{SUCCESS} All ChromaDB & Vector Search tests passed successfully!")
    else:
        print(f"{ERROR} Some ChromaDB & Vector Search tests failed.")


if __name__ == "__main__":
    run_tests()
