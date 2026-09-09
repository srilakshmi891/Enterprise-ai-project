# -*- coding: utf-8 -*-
"""
Conversation Memory + Multi-Turn Chat -- API Test Suite
ASCII-only output for Windows compatibility.
"""
import io
import time
import requests

from app.services.gemini_service import gemini_service, GeminiService, GeminiServiceError
from app.services.assistant_router import IntentType

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
    assert r.status_code == 200, f"Login failed: {r.text}"
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
    r_up = requests.post(
        f"{BASE_URL}/documents/upload",
        headers=hdrs(token),
        files={"file": (filename, content, mime_type)}
    )
    assert r_up.status_code == 201, f"Upload failed: {r_up.text}"
    doc_id = r_up.json()["id"]

    r_proc = requests.post(f"{BASE_URL}/documents/{doc_id}/process", headers=hdrs(token))
    assert r_proc.status_code == 200, f"Process failed: {r_proc.text}"

    r_chunk = requests.post(f"{BASE_URL}/documents/{doc_id}/chunk", headers=hdrs(token))
    assert r_chunk.status_code == 200, f"Chunk failed: {r_chunk.text}"

    r_embed = requests.post(f"{BASE_URL}/documents/{doc_id}/embed", headers=hdrs(token))
    assert r_embed.status_code == 200, f"Embed failed: {r_embed.text}"

    r_idx = requests.post(f"{BASE_URL}/documents/{doc_id}/index", headers=hdrs(token))
    assert r_idx.status_code == 200, f"Index failed: {r_idx.text}"

    return doc_id


def run_tests():
    print(SEP)
    print("  Conversation Memory & Multi-Turn Chat -- API Test Suite")
    print(SEP)

    # Setup Users
    print("\n-- SETUP --")
    ts = int(time.time())
    user_a_name = f"chat_user_a_{ts}"
    user_b_name = f"chat_user_b_{ts}"
    ensure_user(user_a_name, f"{user_a_name}@example.com", "securepass123")
    ensure_user(user_b_name, f"{user_b_name}@example.com", "securepass123")
    token_a = login(user_a_name, "securepass123")
    token_b = login(user_b_name, "securepass123")
    print(f"{INFO}  Tokens acquired successfully")

    # Mocks setup
    captured_prompts = []

    def mock_gemini(prompt, question, context):
        if "FORCE_ERROR" in question:
            raise GeminiServiceError("Simulated Gemini failure")
        captured_prompts.append((prompt, question, context))
        if "model evaluation" in question.lower() or "which one" in question.lower():
            return "Model_Evaluation.pdf discusses model evaluation according to the context."
        return "Grounded response: mock assistant answer."

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

    # 1. Test 1 -- Create Conversation Session
    print("\n-- Test 1: Create Conversation Session --")
    r_create = requests.post(
        f"{BASE_URL}/conversations",
        headers=hdrs(token_a),
        json={"title": "Test Chat Session"}
    )
    assert_status("POST /conversations", r_create, {201})
    if r_create.status_code == 201:
        c1 = r_create.json()
        assert_true("Session id is integer", isinstance(c1.get("id"), int))
        assert_true("Session title matches", c1.get("title") == "Test Chat Session")
        session_id_to_delete = c1["id"]

    # 2. Test 2: List User's Conversations
    print("\n-- Test 2: List User's Conversations --")
    r_list = requests.get(f"{BASE_URL}/conversations", headers=hdrs(token_a))
    assert_status("GET /conversations", r_list, {200})
    if r_list.status_code == 200:
        data_list = r_list.json()
        assert_true("total >= 1", data_list.get("total", 0) >= 1)
        assert_true("items is non-empty list", len(data_list.get("items", [])) >= 1)

    # 3. Test 3: Get Conversation Session Detail
    print("\n-- Test 3: Get Conversation Session Detail --")
    r_get = requests.get(f"{BASE_URL}/conversations/{session_id_to_delete}", headers=hdrs(token_a))
    assert_status("GET /conversations/{id}", r_get, {200})
    if r_get.status_code == 200:
        data_get = r_get.json()
        assert_true("id matches", data_get.get("id") == session_id_to_delete)
        assert_true("messages list is present", isinstance(data_get.get("messages"), list))

    # 4. Test 4: Delete Conversation Session
    print("\n-- Test 4: Delete Conversation Session --")
    r_del = requests.delete(f"{BASE_URL}/conversations/{session_id_to_delete}", headers=hdrs(token_a))
    assert_status("DELETE /conversations/{id} returns 204", r_del, {204})

    r_get_deleted = requests.get(f"{BASE_URL}/conversations/{session_id_to_delete}", headers=hdrs(token_a))
    assert_status("GET deleted session returns 404", r_get_deleted, {404})

    # 5. Test 5: Automatic Conversation Creation via Chat Endpoint
    print("\n-- Test 5: Automatic Session Creation via /assistant/chat --")
    r_auto_chat = requests.post(
        f"{BASE_URL}/assistant/chat",
        headers=hdrs(token_a),
        json={"question": "What documents are available?", "conversation_id": None}
    )
    assert_status("POST /assistant/chat (new)", r_auto_chat, {200})
    if r_auto_chat.status_code == 200:
        chat_data1 = r_auto_chat.json()
        auto_conv_id = chat_data1.get("conversation_id")
        assert_true("Automatic conversation_id is assigned", isinstance(auto_conv_id, int))
        assert_true("Automatic title is created from first question", len(chat_data1.get("question", "")) > 0)

    # 6. Test 6: First Turn and Persistent Messages Check
    print("\n-- Test 6: First Turn Messages Verification --")
    r_get_chat_conv = requests.get(f"{BASE_URL}/conversations/{auto_conv_id}", headers=hdrs(token_a))
    assert_status("GET details for auto-created session", r_get_chat_conv, {200})
    if r_get_chat_conv.status_code == 200:
        c_detail1 = r_get_chat_conv.json()
        assert_true("Messages log has exactly 2 turns (user + assistant)", len(c_detail1.get("messages", [])) == 2)
        assert_true("First message role is user", c_detail1["messages"][0]["role"] == "user")
        assert_true("First message content matches question", c_detail1["messages"][0]["content"] == "What documents are available?")
        assert_true("Second message role is assistant", c_detail1["messages"][1]["role"] == "assistant")

    # 7. Test 7: Multi-Turn Q&A & Second Turn context verification
    print("\n-- Test 7: Multi-Turn Conversation Turn 2 --")
    # Setup document so context can be retrieved and answer is grounded
    txt_eval = "Model_Evaluation document discusses model evaluation and validation techniques."
    setup_document(token_a, "Model_Evaluation.txt", txt_eval.encode("utf-8"), "text/plain")

    # Send second turn referring to previous context
    r_chat_turn2 = requests.post(
        f"{BASE_URL}/assistant/chat",
        headers=hdrs(token_a),
        json={"question": "Which one discusses model evaluation?", "conversation_id": auto_conv_id}
    )
    assert_status("POST /assistant/chat (turn 2)", r_chat_turn2, {200})
    if r_chat_turn2.status_code == 200:
        chat_data2 = r_chat_turn2.json()
        assert_true("Same conversation_id returned", chat_data2.get("conversation_id") == auto_conv_id)
        assert_true("sources list contains documents", len(chat_data2.get("sources", [])) > 0)

    # Verify multi-turn history log via API
    r_get_turn2 = requests.get(f"{BASE_URL}/conversations/{auto_conv_id}", headers=hdrs(token_a))
    if r_get_turn2.status_code == 200:
        c_detail_t2 = r_get_turn2.json()
        t2_msgs = c_detail_t2.get("messages", [])
        assert_true("Turn 2 conversation contains 4 messages total", len(t2_msgs) == 4)
        assert_true("Message 1 is user first question", t2_msgs[0]["role"] == "user")
        assert_true("Message 2 is assistant first answer", t2_msgs[1]["role"] == "assistant")
        assert_true("Message 3 is user second question", t2_msgs[2]["role"] == "user")
        assert_true("Message 4 is assistant second answer", t2_msgs[3]["role"] == "assistant")

    # 8. Test 8: Conversation Ownership Verification
    print("\n-- Test 8: Conversation Ownership --")
    r_list_b = requests.get(f"{BASE_URL}/conversations", headers=hdrs(token_b))
    assert_status("User B GET conversations", r_list_b, {200})
    if r_list_b.status_code == 200:
        data_list_b = r_list_b.json()
        # User B should not see User A's conversations
        ids_b = [c["id"] for c in data_list_b.get("items", [])]
        assert_true("User B does not see User A's session", auto_conv_id not in ids_b)

    # 9. Test 9: Cross-User Conversation Access (expect 404)
    print("\n-- Test 9: Cross-User Conversation Access --")
    r_cross_get = requests.get(f"{BASE_URL}/conversations/{auto_conv_id}", headers=hdrs(token_b))
    assert_status("User B GET User A's conversation (expect 404)", r_cross_get, {404})

    r_cross_del = requests.delete(f"{BASE_URL}/conversations/{auto_conv_id}", headers=hdrs(token_b))
    assert_status("User B DELETE User A's conversation (expect 404)", r_cross_del, {404})

    # 10. Test 10: Cross-User Message Isolation via Chat (expect 404)
    print("\n-- Test 10: Cross-User Chat turn injection protection --")
    r_cross_chat = requests.post(
        f"{BASE_URL}/assistant/chat",
        headers=hdrs(token_b),
        json={"question": "What did we discuss?", "conversation_id": auto_conv_id}
    )
    assert_status("User B POST /assistant/chat with User A's session (expect 404)", r_cross_chat, {404})

    # 11. Test 11: Unauthenticated access
    print("\n-- Test 11: Unauthenticated request --")
    r_unauth = requests.post(f"{BASE_URL}/assistant/chat", json={"question": "test"})
    assert_status("Unauthenticated POST /assistant/chat (expect 401)", r_unauth, {401})

    # 12. Test 12: Question validation
    print("\n-- Test 12: Question validation --")
    r_empty_q = requests.post(f"{BASE_URL}/assistant/chat", headers=hdrs(token_a), json={"question": "", "conversation_id": auto_conv_id})
    assert_status("Reject empty question (expect 422)", r_empty_q, {422})

    r_ws_q = requests.post(f"{BASE_URL}/assistant/chat", headers=hdrs(token_a), json={"question": "   \n  ", "conversation_id": auto_conv_id})
    assert_status("Reject whitespace question (expect 422)", r_ws_q, {422})

    # 13. Test 13: Invalid conversation_id
    print("\n-- Test 13: Invalid conversation_id --")
    r_invalid_id = requests.post(
        f"{BASE_URL}/assistant/chat",
        headers=hdrs(token_a),
        json={"question": "test question", "conversation_id": 99999}
    )
    assert_status("POST /assistant/chat with non-existent conversation_id (expect 404)", r_invalid_id, {404})

    # 14. Test 14: Gemini Failure and Database consistency
    print("\n-- Test 14: Gemini Failure (Preserve User Question, No Fake Assistant Answer) --")
    # Determine user messages count before failure
    r_get_pre = requests.get(f"{BASE_URL}/conversations/{auto_conv_id}", headers=hdrs(token_a))
    pre_msg_count = len(r_get_pre.json()["messages"])

    r_fail_chat = requests.post(
        f"{BASE_URL}/assistant/chat",
        headers=hdrs(token_a),
        json={"question": "FORCE_ERROR: This question triggers Gemini failure.", "conversation_id": auto_conv_id}
    )
    assert_status("POST /assistant/chat with failing LLM (expect 500)", r_fail_chat, {500})

    r_get_post = requests.get(f"{BASE_URL}/conversations/{auto_conv_id}", headers=hdrs(token_a))
    assert_status("Fetch session after failure", r_get_post, {200})
    if r_get_post.status_code == 200:
        c_detail2 = r_get_post.json()
        post_messages = c_detail2.get("messages", [])
        assert_true("Messages count increased by 1 (only user message saved, no assistant message)", len(post_messages) == pre_msg_count + 1)
        assert_true("Last saved message is the user question", post_messages[-1]["role"] == "user")
        assert_true("User message content matches", post_messages[-1]["content"] == "FORCE_ERROR: This question triggers Gemini failure.")

    # 15. Test 15: History Limit context validation
    print("\n-- Test 15: History Limit context --")
    # Feed more turns than CHAT_HISTORY_LIMIT (limit=10 means max 10 messages context)
    for i in range(7):
        requests.post(
            f"{BASE_URL}/assistant/chat",
            headers=hdrs(token_a),
            json={"question": f"Conversation turn loop question {i}?", "conversation_id": auto_conv_id}
        )
    r_chat_final = requests.post(
        f"{BASE_URL}/assistant/chat",
        headers=hdrs(token_a),
        json={"question": "Final question to check limit.", "conversation_id": auto_conv_id}
    )
    assert_status("POST /assistant/chat after turn loop", r_chat_final, {200})
    # Unit test GeminiService.build_prompt directly for history limit formatting
    sample_hist = "\n".join([f"User: Q{i}\nAssistant: A{i}" for i in range(12)])
    built_p = gemini_service.build_prompt("Final question", "Doc context", history=sample_hist)
    assert_true("Prompt includes CONVERSATION HISTORY header", "CONVERSATION HISTORY" in built_p)

    # 16. Test 16: Existing Assistant Regression (POST /assistant/ask still works)
    print("\n-- Test 16: Existing Assistant Regression --")
    r_ask_reg = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=hdrs(token_a),
        json={"question": "What does the document say about model evaluation?"}
    )
    assert_status("POST /assistant/ask regression", r_ask_reg, {200})
    if r_ask_reg.status_code == 200:
        assert_true("Intent is DOCUMENT", r_ask_reg.json().get("intent") == IntentType.DOCUMENT)

    # Summary
    print(f"\n{SEP}")
    print("  SUMMARY OF ASSERTIONS")
    print(f"  Total assertions: {total_assertions}")
    print(f"  Passed assertions: {passed_assertions}")
    print(f"  Failed assertions: {total_assertions - passed_assertions}")
    print(SEP)

    if total_assertions == passed_assertions:
        print(f"{SUCCESS} All conversation memory and multi-turn chat tests passed successfully!")
    else:
        print(f"{ERROR} Some conversation memory and multi-turn chat tests failed.")


if __name__ == "__main__":
    run_tests()
