# -*- coding: utf-8 -*-
"""
AI Project Assistant Orchestration -- API Test Suite
ASCII-only output for Windows compatibility.
"""
import io
import time
import requests

from app.services.gemini_service import gemini_service, GeminiService, GeminiServiceError
from app.services.assistant_router import classify_intent, IntentType

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
    print("  AI Project Assistant Orchestration -- API Test Suite")
    print(SEP)

    # Setup Users
    print("\n-- SETUP --")
    ts = int(time.time())
    user_a_name = f"asst_user_a_{ts}"
    user_b_name = f"asst_user_b_{ts}"
    user_c_name = f"asst_user_c_{ts}"
    ensure_user(user_a_name, f"{user_a_name}@example.com", "securepass123")
    ensure_user(user_b_name, f"{user_b_name}@example.com", "securepass123")
    ensure_user(user_c_name, f"{user_c_name}@example.com", "securepass123")
    token_a = login(user_a_name, "securepass123")
    token_b = login(user_b_name, "securepass123")
    token_c = login(user_c_name, "securepass123")
    print(f"{INFO}  Tokens acquired successfully")

    captured_prompts = []

    def mock_gemini(prompt, question, context):
        captured_prompts.append((prompt, question, context))
        return "Model evaluation measures model performance using cross validation based on the provided data."

    gemini_service.set_mock_generator(mock_gemini)

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

    # 1. Test 1 -- Document Question
    print("\n-- Test 1: Document Question --")
    txt_a = "Model evaluation techniques assess machine learning performance using cross validation."
    doc_a_id = setup_document(token_a, "eval_guide.txt", txt_a.encode("utf-8"), "text/plain")

    r_doc_q = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "What does the document say about model evaluation?", "top_k": 5}
    )
    assert_status("POST /assistant/ask document question", r_doc_q, {200})
    if r_doc_q.status_code == 200:
        d1 = r_doc_q.json()
        assert_true("Intent is DOCUMENT", d1.get("intent") == IntentType.DOCUMENT)
        assert_true("Answer exists", len(d1.get("answer", "")) > 0)
        assert_true("Sources list non-empty", len(d1.get("sources", [])) > 0)
        assert_true("Source type is document", d1.get("sources", [{}])[0].get("type") == "document")

    # 2. Test 2 -- GitHub Question
    print("\n-- Test 2: GitHub Question --")
    r_gh_q = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "What repositories are available on GitHub?"}
    )
    assert_status("POST /assistant/ask GitHub question", r_gh_q, {200})
    if r_gh_q.status_code == 200:
        d2 = r_gh_q.json()
        assert_true("Intent is GITHUB", d2.get("intent") == IntentType.GITHUB)
        assert_true("Answer exists", len(d2.get("answer", "")) > 0)

    # 3. Test 3 -- Jira Question
    print("\n-- Test 3: Jira Question --")
    r_jira_q = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "What Jira projects are available?"}
    )
    assert_status("POST /assistant/ask Jira question", r_jira_q, {200})
    if r_jira_q.status_code == 200:
        d3 = r_jira_q.json()
        assert_true("Intent is JIRA", d3.get("intent") == IntentType.JIRA)
        assert_true("Answer exists", len(d3.get("answer", "")) > 0)

    # 4. Test 4 -- General Project Question
    print("\n-- Test 4: General Project Question --")
    r_gen_q = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "Give me a summary of this project."}
    )
    assert_status("POST /assistant/ask General question", r_gen_q, {200})
    if r_gen_q.status_code == 200:
        d4 = r_gen_q.json()
        assert_true("Intent is GENERAL_PROJECT", d4.get("intent") == IntentType.GENERAL_PROJECT)
        assert_true("Answer exists", len(d4.get("answer", "")) > 0)

    # 5. Test 5 -- Question Validation
    print("\n-- Test 5: Question Validation --")
    r_empty = requests.post(f"{BASE_URL}/assistant/ask", headers=hdrs(token_a), json={"question": ""})
    assert_status("Reject empty question (expect 422)", r_empty, {422})

    r_ws = requests.post(f"{BASE_URL}/assistant/ask", headers=hdrs(token_a), json={"question": "   \n  "})
    assert_status("Reject whitespace question (expect 422)", r_ws, {422})

    # 6. Test 6 -- Document Filter
    print("\n-- Test 6: Document Filter --")
    r_filter = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "What does the document say?", "document_id": doc_a_id}
    )
    assert_status("POST /assistant/ask with document_id filter", r_filter, {200})
    if r_filter.status_code == 200:
        d6 = r_filter.json()
        assert_true("Intent is DOCUMENT when document_id provided", d6.get("intent") == IntentType.DOCUMENT)
        all_match = all(s.get("document_id") == doc_a_id for s in d6.get("sources", []))
        assert_true("All sources match document_id filter", all_match)

    # 7. Test 7 -- Cross-User Document Filter
    print("\n-- Test 7: Cross-User Document Filter --")
    r_cross = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_b),
        json={"question": "eval", "document_id": doc_a_id}
    )
    assert_status("User B ask with User A's document_id (expect 404)", r_cross, {404})

    # 8. Test 8 -- User Isolation
    print("\n-- Test 8: User Isolation --")
    txt_b = "Confidential financial statements for User B."
    doc_b_id = setup_document(token_b, "fin.txt", txt_b.encode("utf-8"), "text/plain")

    r_iso = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "What are the confidential financial statements?"}
    )
    assert_status("User A assistant ask query", r_iso, {200})
    if r_iso.status_code == 200:
        sources_a = r_iso.json().get("sources", [])
        user_b_sources = [s for s in sources_a if s.get("document_id") == doc_b_id]
        assert_true("User B's document NEVER appears in User A's sources", len(user_b_sources) == 0)

    # 9. Test 9 -- Unauthenticated Request
    print("\n-- Test 9: Unauthenticated Request --")
    r_unauth = requests.post(f"{BASE_URL}/assistant/ask", json={"question": "test question"})
    assert_status("Unauthenticated POST /assistant/ask (expect 401)", r_unauth, {401})

    # 10. Test 10 -- Empty Document Context
    print("\n-- Test 10: Empty Document Context --")
    r_empty_ctx = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_c),
        json={"question": "What does the document say about astrophysics?"}
    )
    assert_status("User C ask with no indexed documents", r_empty_ctx, {200})
    if r_empty_ctx.status_code == 200:
        d10 = r_empty_ctx.json()
        assert_true("Sources list is empty", d10.get("sources") == [])
        assert_true("Answer indicates info not found", "couldn't find this information" in d10.get("answer", "").lower())
        assert_true("Retrieved count is 0", d10.get("retrieved_count") == 0)

    # 11. Test 11 -- Gemini Failure Handling
    print("\n-- Test 11: Gemini API Failure Handling --")
    failing_service = GeminiService(api_key="FORCE_ERROR")
    error_caught = False
    try:
        failing_service.generate_answer("test question", "some context")
    except GeminiServiceError as e:
        error_caught = True
        assert_true("GeminiServiceError raised on API error", True)
        assert_true("Error message does not leak secret keys", "FORCE_ERROR" not in str(e))
    if not error_caught:
        assert_true("GeminiServiceError raised on API error", False)

    # 12. Test 12 -- Source Structure Verification
    print("\n-- Test 12: Source Structure Verification --")
    r_src = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "What does the document say about model evaluation?"}
    )
    assert_status("POST /assistant/ask for source structure check", r_src, {200})
    if r_src.status_code == 200:
        srcs = r_src.json().get("sources", [])
        if srcs:
            s0 = srcs[0]
            assert_true("Source contains type", "type" in s0)
            assert_true("Source type is 'document'", s0.get("type") == "document")
            assert_true("Source contains filename", s0.get("filename") == "eval_guide.txt")
            assert_true("Source contains document_id", s0.get("document_id") == doc_a_id)

    # 13. Test 13 -- Intent Routing Verification
    print("\n-- Test 13: Intent Routing Verification --")
    assert_true("DOCUMENT intent classification", classify_intent("What does the document say?") == IntentType.DOCUMENT)
    assert_true("GITHUB intent classification", classify_intent("Show my GitHub repositories.") == IntentType.GITHUB)
    assert_true("JIRA intent classification", classify_intent("What Jira projects do I have?") == IntentType.JIRA)
    assert_true("GENERAL_PROJECT intent classification", classify_intent("Summarize my project.") == IntentType.GENERAL_PROJECT)

    # 14. Test 14 -- Existing RAG Regression
    print("\n-- Test 14: Existing RAG Regression --")
    r_rag_ret = requests.post(
        f"{BASE_URL}/rag/retrieve",
        headers=hdrs(token_a),
        json={"question": "model evaluation", "top_k": 5}
    )
    assert_status("POST /rag/retrieve regression test", r_rag_ret, {200})

    r_rag_ask = requests.post(
        f"{BASE_URL}/rag/ask",
        headers=hdrs(token_a),
        json={"question": "model evaluation", "top_k": 5}
    )
    assert_status("POST /rag/ask regression test", r_rag_ask, {200})

    # Summary
    print(f"\n{SEP}")
    print("  SUMMARY OF ASSERTIONS")
    print(f"  Total assertions: {total_assertions}")
    print(f"  Passed assertions: {passed_assertions}")
    print(f"  Failed assertions: {total_assertions - passed_assertions}")
    print(SEP)

    if total_assertions == passed_assertions:
        print(f"{SUCCESS} All AI Project Assistant tests passed successfully!")
    else:
        print(f"{ERROR} Some AI Project Assistant tests failed.")


if __name__ == "__main__":
    run_tests()
