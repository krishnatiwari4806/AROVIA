"""Automated verification test suite for Personal AI Coach (Phase 2)."""

import json
import os
import sys
import urllib.error
import urllib.request

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def make_req(url, data=None, token=None, method="GET"):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    encoded = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=encoded, headers=headers, method=method
    )
    try:
        res = urllib.request.urlopen(req)
        return res.getcode(), json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def run_tests():
    print("==================================================")
    print("  AROVIA PERSONAL AI COACH END-TO-END VERIFICATION")
    print("==================================================")

    # 1. Login User A
    code, res_a = make_req(
        "http://127.0.0.1:8000/api/v1/auth/login",
        {
            "email": "lead.dev@arovia.io",
            "password": "AroviaLeadPass2026!@#",
        },
        method="POST",
    )
    assert code == 200, f"User A login failed: {res_a}"
    token_a = res_a["access_token"]
    print("[PASS] 1. Authenticated User A (HTTP 200)")

    # 2. Login or register User B (for isolation validation)
    code, res_b = make_req(
        "http://127.0.0.1:8000/api/v1/auth/login",
        {
            "email": "user_b_coach_test@arovia.io",
            "password": "AroviaDevPassword2026!@#",
        },
        method="POST",
    )
    if code != 200:
        code, res_b = make_req(
            "http://127.0.0.1:8000/api/v1/auth/register",
            {
                "full_name": "Candidate B",
                "email": "user_b_coach_test@arovia.io",
                "password": "AroviaDevPassword2026!@#",
            },
            method="POST",
        )
        assert code == 201, f"User B registration failed: {res_b}"
    token_b = res_b["access_token"]
    print("[PASS] 2. Authenticated User B (HTTP 200/201)")

    # 3. Retrieve or create interview session for User A
    code, sess_list = make_req(
        "http://127.0.0.1:8000/api/v1/interviews/sessions", token=token_a
    )
    assert code == 200, f"GET /interviews/sessions failed: {sess_list}"
    print(f"[PASS] 3. Retrieved User A interview sessions: {len(sess_list)} records (HTTP 200)")

    if not sess_list:
        code, new_sess = make_req(
            "http://127.0.0.1:8000/api/v1/interviews/sessions",
            {
                "target_role": "Principal Systems Architect",
                "seniority_level": "senior",
                "interview_focus": "System Design",
                "practice_mode": "quick",
            },
            token=token_a,
            method="POST",
        )
        assert code == 201, f"Session creation failed: {new_sess}"
        session_id_a = new_sess["id"]
    else:
        session_id_a = sess_list[0]["id"]
    print(f"   Target interview session ID: {session_id_a}")

    # 4. Initialize Coach Conversation with Auto-Debrief
    code, conv = make_req(
        "http://127.0.0.1:8000/api/v1/coach/conversation",
        {"session_id": session_id_a, "auto_debrief": True},
        token=token_a,
        method="POST",
    )
    assert code == 200, f"POST /coach/conversation failed: {conv}"
    conv_id = conv["id"]
    assert conv["session_id"] == session_id_a
    assert len(conv["messages"]) >= 1, "Expected initial debrief message in conversation"
    print(f"[PASS] 4. Initialized Coach Conversation with AI Debrief: {conv_id} ({len(conv['messages'])} msgs)")

    # 5. Interactive Follow-up Chat with Coach (POST /api/v1/coach/chat)
    code, chat_res = make_req(
        "http://127.0.0.1:8000/api/v1/coach/chat",
        {
            "conversation_id": conv_id,
            "message": "What were the primary architectural trade-offs I missed during the caching question?",
            "context_turn_index": 0,
        },
        token=token_a,
        method="POST",
    )
    assert code == 200, f"POST /coach/chat failed: {chat_res}"
    assert chat_res["user_message"]["sender"] == "user"
    assert chat_res["coach_message"]["sender"] == "coach"
    assert len(chat_res["coach_message"]["message_text"]) > 20
    print("[PASS] 5. Executed interactive coaching chat query with Gemini response")
    print(f"   Coach Response Snippet: {chat_res['coach_message']['message_text'][:80]}...")

    # 6. Retrieve Coach History (GET /api/v1/coach/history/{session_id})
    code, hist = make_req(
        f"http://127.0.0.1:8000/api/v1/coach/history/{session_id_a}",
        token=token_a,
    )
    assert code == 200, f"GET /coach/history failed: {hist}"
    assert hist["total_messages"] >= 3, f"Expected >= 3 messages (debrief + user + coach), got: {hist['total_messages']}"
    print(f"[PASS] 6. Verified persistent chronological history: {hist['total_messages']} messages in database")

    # 7. Security: Unauthenticated access rejected (HTTP 401)
    code, unauth_res = make_req(
        f"http://127.0.0.1:8000/api/v1/coach/history/{session_id_a}"
    )
    assert code == 401, f"Expected 401 for unauthenticated request, got: {code}"
    print("[PASS] 7. Security Guard: Unauthenticated access rejected with HTTP 401")

    # 8. Anti-IDOR Security: User B cannot retrieve User A's session coach history
    code, idor_res = make_req(
        f"http://127.0.0.1:8000/api/v1/coach/history/{session_id_a}",
        token=token_b,
    )
    assert code == 404, f"Expected 404 for cross-user session access, got: {code} {idor_res}"
    print(f"[PASS] 8. Security Guard: User B blocked from User A's session coach history (HTTP {code})")

    # 9. Anti-IDOR Security: User B cannot send messages into User A's coach conversation
    code, idor_chat = make_req(
        "http://127.0.0.1:8000/api/v1/coach/chat",
        {
            "conversation_id": conv_id,
            "message": "Unauthorized inquiry from User B",
        },
        token=token_b,
        method="POST",
    )
    assert code == 404, f"Expected 404 for cross-user chat injection, got: {code} {idor_chat}"
    print(f"[PASS] 9. Security Guard: User B blocked from chatting in User A's conversation (HTTP {code})")

    print("\n==================================================")
    print("  ALL 9/9 AI COACH SYSTEM VERIFICATION CHECKS PASSED")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
