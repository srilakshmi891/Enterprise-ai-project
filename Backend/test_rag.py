# -*- coding: utf-8 -*-
"""
RAG Milestone 1 -- Retrieval & Context Assembly API Test Suite
ASCII-only output for Windows compatibility.
"""
import io
import time
import requests

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

    # 5. Index
    r_idx = requests.post(f"{BASE_URL}/documents/{doc_id}/index", headers=hdrs(token))
    assert r_idx.status_code == 200, f"Index failed: {r_idx.text}"

    return doc_id


def run_tests():
    print(SEP)
    print("  RAG Milestone 1 -- Retrieval & Context Assembly Test Suite")
    print(SEP)

    # Setup Users
    print("\n-- SETUP --")
    ts = int(time.time())
    user_a_name = f"rag_user_a_{ts}"
    user_b_name = f"rag_user_b_{ts}"
    user_c_name = f"rag_user_c_{ts}"
    ensure_user(user_a_name, f"{user_a_name}@example.com", "securepass123")
    ensure_user(user_b_name, f"{user_b_name}@example.com", "securepass123")
    ensure_user(user_c_name, f"{user_c_name}@example.com", "securepass123")
    token_a = login(user_a_name, "securepass123")
    token_b = login(user_b_name, "securepass123")
    token_c = login(user_c_name, "securepass123")
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

    # 1. Test 1 -- Basic Retrieval
    print("\n-- Test 1: Basic Retrieval --")
    txt_a = "Agile software development principles prioritize iterative delivery and team collaboration."
    doc_a_id = setup_document(token_a, "agile_guide.txt", txt_a.encode("utf-8"), "text/plain")

    r_ret1 = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_a),
        json={"question": "What are Agile software development principles?", "top_k": 5}
    )
    assert_status("POST /rag/retrieve basic query", r_ret1, {200})
    if r_ret1.status_code == 200:
        data1 = r_ret1.json()
        assert_true("Response contains question", data1.get("question") == "What are Agile software development principles?")
        assert_true("retrieved_count > 0", data1.get("retrieved_count", 0) > 0)
        assert_true("results list is non-empty", len(data1.get("results", [])) > 0)
        assert_true("context string is non-empty", len(data1.get("context", "")) > 0)

    # 2. Test 2 -- Question Validation
    print("\n-- Test 2: Question Validation --")
    r_empty_q = requests.post(f"{BASE_URL}/rag/retrieve", headers=hdrs(token_a), json={"question": ""})
    assert_status("Reject empty question (expect 422)", r_empty_q, {422})

    r_ws_q = requests.post(f"{BASE_URL}/rag/retrieve", headers=hdrs(token_a), json={"question": "   \n  "})
    assert_status("Reject whitespace question (expect 422)", r_ws_q, {422})

    # 3. Test 3 -- Top K Limit
    print("\n-- Test 3: Top K Limit --")
    r_topk = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_a),
        json={"question": "Agile software collaboration", "top_k": 3}
    )
    assert_status("POST /rag/retrieve with top_k=3", r_topk, {200})
    if r_topk.status_code == 200:
        assert_true("len(results) <= 3", len(r_topk.json().get("results", [])) <= 3)

    # 4. Test 4 -- Document Filter
    print("\n-- Test 4: Document Filter --")
    r_filter = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_a),
        json={"question": "Agile software", "top_k": 5, "document_id": doc_a_id}
    )
    assert_status("POST /rag/retrieve with document_id filter", r_filter, {200})
    if r_filter.status_code == 200:
        res_filter = r_filter.json().get("results", [])
        all_match = all(r["document_id"] == doc_a_id for r in res_filter)
        assert_true("All retrieved chunks match target document_id", all_match)

    # 5. Test 5 -- User Isolation
    print("\n-- Test 5: User Isolation --")
    txt_b = "DevOps automation pipeline streamlines CI/CD deployment."
    doc_b_id = setup_document(token_b, "devops.txt", txt_b.encode("utf-8"), "text/plain")

    # User A searches for DevOps (User B's domain)
    r_user_a_search = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_a),
        json={"question": "DevOps automation CI/CD deployment", "top_k": 5}
    )
    assert_status("User A POST /rag/retrieve query", r_user_a_search, {200})
    if r_user_a_search.status_code == 200:
        res_a = r_user_a_search.json().get("results", [])
        b_docs_in_a = [r for r in res_a if r["document_id"] == doc_b_id]
        assert_true("User B's document NEVER appears in User A retrieval", len(b_docs_in_a) == 0)

    # User B searches for Agile (User A's domain)
    r_user_b_search = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_b),
        json={"question": "Agile software development principles", "top_k": 5}
    )
    assert_status("User B POST /rag/retrieve query", r_user_b_search, {200})
    if r_user_b_search.status_code == 200:
        res_b = r_user_b_search.json().get("results", [])
        a_docs_in_b = [r for r in res_b if r["document_id"] == doc_a_id]
        assert_true("User A's document NEVER appears in User B retrieval", len(a_docs_in_b) == 0)

    # 6. Test 6 -- Cross-user Document ID
    print("\n-- Test 6: Cross-user Document ID --")
    r_cross_doc = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_b),
        json={"question": "Agile", "top_k": 5, "document_id": doc_a_id}
    )
    assert_status("User B retrieve with User A's document_id (expect 404)", r_cross_doc, {404})

    # 7. Test 7 -- Unauthenticated Request
    print("\n-- Test 7: Unauthenticated Request --")
    r_unauth = requests.post(
        f"{BASE_URL}/rag/retrieve",
        json={"question": "What is Agile?"}
    )
    assert_status("Unauthenticated POST /rag/retrieve (expect 401)", r_unauth, {401})

    # 8. Test 8 -- Empty Result
    print("\n-- Test 8: Empty Result --")
    # User C has no indexed documents
    r_empty_c = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_c),
        json={"question": "What is model evaluation?", "top_k": 5}
    )
    assert_status("User C retrieve with no indexed documents", r_empty_c, {200})
    if r_empty_c.status_code == 200:
        data_c = r_empty_c.json()
        assert_true("retrieved_count is 0", data_c.get("retrieved_count") == 0)
        assert_true("results list is empty", data_c.get("results") == [])
        assert_true("context string is empty", data_c.get("context") == "")

    # 9. Test 9 -- Context Assembly Format
    print("\n-- Test 9: Context Assembly Format --")
    if r_ret1.status_code == 200:
        ctx = r_ret1.json().get("context", "")
        assert_true("Context contains '[Source 1]'", "[Source 1]" in ctx)
        assert_true("Context contains 'File: agile_guide.txt'", "File: agile_guide.txt" in ctx)
        assert_true("Context contains 'Document ID:'", "Document ID:" in ctx)
        assert_true("Context contains 'Chunk:'", "Chunk:" in ctx)
        assert_true("Context contains source text", "Agile software development" in ctx)

    # 10. Test 10 -- Source Metadata Structure
    print("\n-- Test 10: Source Metadata Structure --")
    if r_ret1.status_code == 200:
        first_res = r_ret1.json().get("results", [])[0]
        assert_true("Result contains 'chunk_id'", "chunk_id" in first_res)
        assert_true("Result contains 'document_id'", first_res.get("document_id") == doc_a_id)
        assert_true("Result contains 'chunk_index'", "chunk_index" in first_res)
        assert_true("Result contains 'filename'", first_res.get("filename") == "agile_guide.txt")
        assert_true("Result contains 'text'", "text" in first_res)
        assert_true("Result contains 'distance'", isinstance(first_res.get("distance"), float))

    # 11. Test 11 -- Existing Search Regression
    print("\n-- Test 11: Existing Search Regression --")
    r_search_reg = requests.post(
        f"{BASE_URL}/search",
        headers=hdrs(token_a),
        json={"question": "Agile principles", "query": "Agile principles", "top_k": 5}
    )
    assert_status("POST /search endpoint regression test", r_search_reg, {200})

    # Summary
    print(f"\n{SEP}")
    print("  SUMMARY OF ASSERTIONS")
    print(f"  Total assertions: {total_assertions}")
    print(f"  Passed assertions: {passed_assertions}")
    print(f"  Failed assertions: {total_assertions - passed_assertions}")
    print(SEP)

    if total_assertions == passed_assertions:
        print(f"{SUCCESS} All RAG Retrieval & Context Assembly tests passed successfully!")
    else:
        print(f"{ERROR} Some RAG Retrieval tests failed.")


if __name__ == "__main__":
    run_tests()
