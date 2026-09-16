"""
End-to-End Gemini Quota Budget & Feasibility Integration Tests (Task 5).

Verifies exact Gemini call counts and budgets across realistic candidate journeys (A through E),
ensuring zero passive/hidden calls, zero refresh/dashboard calls, deterministic reuse of DB state,
and safe headroom under the observed 20 RPD free-tier quota.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch
import docx
import pytest
from httpx import AsyncClient

from app.schemas.evaluation import ImprovementItem, SessionEvaluationReport, StrengthItem
from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.schemas.resume import ParsedResumeData
from app.services.gemini_service import GeminiService, ParsedJobDescription


def create_sample_docx(text: str) -> bytes:
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


SAMPLE_DOCX = create_sample_docx("Candidate Alex, Senior Python Engineer with 5 years experience in FastAPI, Postgres, and Docker.")


def make_mock_session_eval():
    return SessionEvaluationReport(
        turns_evaluation=[],
        top_strengths=[
            StrengthItem(title="Async Concurrency", description="Demonstrated clear understanding of FastAPI event loops.")
        ],
        top_improvements=[
            ImprovementItem(
                title="Database Pooling",
                description="Could explain connection pool sizing in more depth.",
                actionable_recommendation="Review SQLAlchemy AsyncEngine connection pooling docs.",
            )
        ],
        executive_summary="Solid demonstration of core technical capabilities.",
    )


async def _register_user(client: AsyncClient, email: str) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword!123",
            "full_name": "Test Candidate",
        },
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_journey_a_quick_interview_zero_coach_chat_budget(client: AsyncClient):
    """
    JOURNEY A:
    1. Resume upload (1 Gemini call)
    2. Quick interview session creation (0 Gemini calls)
    3. Start interview (Turn 0 intro template: 0 Gemini calls)
    4. Answer Turn 0 -> generates Q1 (1 Gemini call)
    5. Answer Turn 1 -> generates Q2 (1 Gemini call)
    6. Answer Turn 2 -> generates Q3 (1 Gemini call)
    7. Answer Turn 3 (last planned core question in quick mode) -> completes (1 Gemini call)
    8. Post-session evaluation -> computes report (1 Gemini call)
    9. Open Coach -> generates initial debrief (1 Gemini call, 0 chat)
    10. Dashboard & navigation refresh -> (0 Gemini calls)
    
    Total Gemini Calls: 1 (resume) + 4 (turns) + 1 (eval) + 1 (coach) = 7 calls (min 7, max 8 with follow-up).
    """
    call_log = []

    async def mock_parse_resume(*args, **kwargs):
        call_log.append("parse_resume")
        return ParsedResumeData(
            skills=["Python", "FastAPI"],
            experience_years=3.0,
            domains=["Backend"],
            education=[],
            summary="Python developer",
            projects=[],
            work_history=[],
        )

    async def mock_gen_initial_q(*args, **kwargs):
        call_log.append("generate_initial_question")
        return GeneratedQuestion(
            question_text="How do async event loops work in FastAPI?",
            ideal_answer="Asyncio loop handles non-blocking IO via cooperative multitasking.",
            primary_concept="Async IO",
        )

    turn_counter = 0

    async def mock_eval_and_gen_next(*args, **kwargs):
        nonlocal turn_counter
        turn_counter += 1
        call_log.append(f"evaluate_and_generate_next_turn_{turn_counter}")
        is_complete = turn_counter >= 3
        return NextTurnDecision(
            is_follow_up=False,
            question_text=f"Question {turn_counter + 1} on backend architecture" if not is_complete else "",
            ideal_answer="Explanation of architecture",
            primary_concept="Architecture",
            is_interview_complete=is_complete,
        )

    async def mock_eval_session(*args, **kwargs):
        call_log.append("evaluate_interview_session")
        return make_mock_session_eval()

    async def mock_coach_debrief(*args, **kwargs):
        call_log.append("generate_initial_debrief")
        return "### AI Coach Debrief\n\nGreat demonstration of FastAPI core principles."

    headers = await _register_user(client, "journey_a@arovia.io")

    with patch("app.services.gemini_service.GeminiService.parse_resume", side_effect=mock_parse_resume), \
         patch("app.services.gemini_service.GeminiService.generate_initial_question", side_effect=mock_gen_initial_q), \
         patch("app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn", side_effect=mock_eval_and_gen_next), \
         patch("app.services.gemini_service.GeminiService.evaluate_interview_session", side_effect=mock_eval_session), \
         patch("app.services.coach_ai_service.CoachAIService.generate_initial_debrief", side_effect=mock_coach_debrief):

        # 1. Upload Resume
        upload_resp = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.docx", SAMPLE_DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        assert upload_resp.status_code == 201
        resume_id = upload_resp.json()["resume"]["id"]
        assert len(call_log) == 1
        assert call_log[-1] == "parse_resume"

        # 2. Create Interview Session (Quick mode: 3 core questions)
        sess_resp = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "mid",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
                "resume_id": resume_id,
            },
            headers=headers,
        )
        assert sess_resp.status_code == 201
        session_id = sess_resp.json()["id"]
        assert len(call_log) == 1  # 0 new calls

        # 3. Start Interview (Turn 0 template)
        start_resp = await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)
        assert start_resp.status_code == 200
        turn0_id = start_resp.json()["id"]
        assert len(call_log) == 1  # Turn 0 is template-based, 0 calls

        # 4. Answer Turn 0 (Intro) -> triggers initial question generation
        ans0_resp = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
            json={"candidate_answer": "Hi, I am Alex with 3 years experience building Python APIs."},
            headers=headers,
        )
        assert ans0_resp.status_code == 200
        assert len(call_log) == 2
        assert call_log[-1] == "generate_initial_question"
        next_turn_id = ans0_resp.json()["next_turn"]["id"]

        # 5. Answer Core Turn 1
        ans1_resp = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{next_turn_id}/answer",
            json={"candidate_answer": "FastAPI uses an async event loop to handle concurrent I/O efficiently."},
            headers=headers,
        )
        assert ans1_resp.status_code == 200
        assert len(call_log) == 3
        next_turn_id = ans1_resp.json()["next_turn"]["id"]

        # 6. Answer Core Turn 2
        ans2_resp = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{next_turn_id}/answer",
            json={"candidate_answer": "Database connections are pooled using SQLAlchemy async engine."},
            headers=headers,
        )
        assert ans2_resp.status_code == 200
        assert len(call_log) == 4
        next_turn_id = ans2_resp.json()["next_turn"]["id"]

        # 7. Answer Core Turn 3 (Final planned core question -> complete session)
        ans3_resp = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{next_turn_id}/answer",
            json={"candidate_answer": "We deploy services inside Docker containers orchestrating with K8s."},
            headers=headers,
        )
        assert ans3_resp.status_code == 200
        assert ans3_resp.json()["is_interview_complete"] is True
        assert len(call_log) == 5

        # 8. Post-session Evaluation
        eval_resp = await client.post(f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers)
        assert eval_resp.status_code == 200
        assert len(call_log) == 6
        assert call_log[-1] == "evaluate_interview_session"

        # 9. Open Coach (initial debrief generated)
        coach_resp = await client.post(
            "/api/v1/coach/conversation",
            json={"session_id": session_id, "auto_debrief": True},
            headers=headers,
        )
        assert coach_resp.status_code == 200
        assert len(call_log) == 7
        assert call_log[-1] == "generate_initial_debrief"

        # 10. Verify GET/refresh endpoints produce 0 calls
        await client.get(f"/api/v1/coach/history/{session_id}", headers=headers)
        await client.get(f"/api/v1/interviews/sessions/{session_id}/evaluation", headers=headers)
        await client.get("/api/v1/progress", headers=headers)
        await client.get("/api/v1/progress/insight", headers=headers)
        await client.get("/api/v1/resumes/me", headers=headers)

        assert len(call_log) == 7  # EXACTLY 7 calls for Journey A


@pytest.mark.asyncio
async def test_journey_b_quick_interview_five_coach_messages(client: AsyncClient):
    """
    JOURNEY B:
    1. Resume upload (1 call)
    2. Quick interview (4 turns = 4 calls)
    3. Final evaluation (1 call)
    4. Coach initial debrief (1 call)
    5. 5 Coach chat messages (5 calls)
    
    Total Gemini Calls: 1 + 4 + 1 + 1 + 5 = 12 calls (min 12, max 13 with follow-up).
    """
    call_log = []

    async def mock_parse_resume(*args, **kwargs):
        call_log.append("parse_resume")
        return ParsedResumeData(
            skills=["Python"], experience_years=2.0, domains=["Backend"], education=[], summary="", projects=[], work_history=[]
        )

    async def mock_gen_initial_q(*args, **kwargs):
        call_log.append("generate_initial_question")
        return GeneratedQuestion(question_text="Q1", ideal_answer="Ans1", primary_concept="C1")

    turn_counter = 0

    async def mock_eval_and_gen_next(*args, **kwargs):
        nonlocal turn_counter
        turn_counter += 1
        call_log.append(f"evaluate_and_generate_next_turn_{turn_counter}")
        is_complete = turn_counter >= 3
        return NextTurnDecision(
            is_follow_up=False,
            question_text=f"Q{turn_counter + 1}" if not is_complete else "",
            ideal_answer="Ans",
            primary_concept="Concept",
            is_interview_complete=is_complete,
        )

    async def mock_eval_session(*args, **kwargs):
        call_log.append("evaluate_interview_session")
        return make_mock_session_eval()

    async def mock_coach_debrief(*args, **kwargs):
        call_log.append("generate_initial_debrief")
        return "### Coach Debrief\n\nWell done."

    async def mock_coach_chat(*args, **kwargs):
        call_log.append("generate_chat_reply")
        return {
            "coach_response": "Here is detailed advice for your interview question.",
            "suggested_followups": ["Follow up 1", "Follow up 2"],
        }

    headers = await _register_user(client, "journey_b@arovia.io")

    with patch("app.services.gemini_service.GeminiService.parse_resume", side_effect=mock_parse_resume), \
         patch("app.services.gemini_service.GeminiService.generate_initial_question", side_effect=mock_gen_initial_q), \
         patch("app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn", side_effect=mock_eval_and_gen_next), \
         patch("app.services.gemini_service.GeminiService.evaluate_interview_session", side_effect=mock_eval_session), \
         patch("app.services.coach_ai_service.CoachAIService.generate_initial_debrief", side_effect=mock_coach_debrief), \
         patch("app.services.coach_ai_service.CoachAIService.generate_chat_reply", side_effect=mock_coach_chat):

        # Upload
        up_res = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.docx", SAMPLE_DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        resume_id = up_res.json()["resume"]["id"]

        # Setup Quick
        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick", "resume_id": resume_id},
            headers=headers,
        )
        session_id = sess_res.json()["id"]

        # Start & Answer Turns
        start_res = await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)
        curr_turn_id = start_res.json()["id"]

        for i in range(4):
            ans_res = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/turns/{curr_turn_id}/answer",
                json={"candidate_answer": f"Answer for turn {i}"},
                headers=headers,
            )
            if not ans_res.json()["is_interview_complete"]:
                curr_turn_id = ans_res.json()["next_turn"]["id"]

        # Eval
        await client.post(f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers)

        # Coach Init
        coach_init_res = await client.post("/api/v1/coach/conversation", json={"session_id": session_id, "auto_debrief": True}, headers=headers)
        conversation_id = coach_init_res.json()["id"]

        # 5 Coach Chat Messages
        for i in range(5):
            c_res = await client.post(
                "/api/v1/coach/chat",
                json={"conversation_id": conversation_id, "message": f"How do I improve on question {i+1}?"},
                headers=headers,
            )
            assert c_res.status_code == 200

        # Verification: 1 + 4 + 1 + 1 + 5 = 12 calls
        assert len(call_log) == 12
        assert call_log.count("generate_chat_reply") == 5


@pytest.mark.asyncio
async def test_journey_c_full_interview_five_coach_messages(client: AsyncClient):
    """
    JOURNEY C:
    1. Resume upload (1 call)
    2. Full interview (Turn 0 answer + 6 core turns = 7 turns = 7 calls)
    3. Final evaluation (1 call)
    4. Coach initial debrief (1 call)
    5. 5 Coach chat messages (5 calls)
    
    Total Gemini Calls: 1 + 7 + 1 + 1 + 5 = 15 calls (min 15, max 18 with 3 follow-ups).
    """
    call_log = []

    async def mock_parse_resume(*args, **kwargs):
        call_log.append("parse_resume")
        return ParsedResumeData(
            skills=["Python", "System Design"], experience_years=6.0, domains=["Backend"], education=[], summary="", projects=[], work_history=[]
        )

    async def mock_gen_initial_q(*args, **kwargs):
        call_log.append("generate_initial_question")
        return GeneratedQuestion(question_text="Full Q1", ideal_answer="Ans1", primary_concept="C1")

    turn_counter = 0

    async def mock_eval_and_gen_next(*args, **kwargs):
        nonlocal turn_counter
        turn_counter += 1
        call_log.append(f"evaluate_and_generate_next_turn_{turn_counter}")
        is_complete = turn_counter >= 6  # 6 core questions
        return NextTurnDecision(
            is_follow_up=False,
            question_text=f"Full Q{turn_counter + 1}" if not is_complete else "",
            ideal_answer="Ans",
            primary_concept="Concept",
            is_interview_complete=is_complete,
        )

    async def mock_eval_session(*args, **kwargs):
        call_log.append("evaluate_interview_session")
        return make_mock_session_eval()

    async def mock_coach_debrief(*args, **kwargs):
        call_log.append("generate_initial_debrief")
        return "### Coach Debrief\n\nDetailed full interview debrief."

    async def mock_coach_chat(*args, **kwargs):
        call_log.append("generate_chat_reply")
        return {"coach_response": "Advice", "suggested_followups": []}

    headers = await _register_user(client, "journey_c@arovia.io")

    with patch("app.services.gemini_service.GeminiService.parse_resume", side_effect=mock_parse_resume), \
         patch("app.services.gemini_service.GeminiService.generate_initial_question", side_effect=mock_gen_initial_q), \
         patch("app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn", side_effect=mock_eval_and_gen_next), \
         patch("app.services.gemini_service.GeminiService.evaluate_interview_session", side_effect=mock_eval_session), \
         patch("app.services.coach_ai_service.CoachAIService.generate_initial_debrief", side_effect=mock_coach_debrief), \
         patch("app.services.coach_ai_service.CoachAIService.generate_chat_reply", side_effect=mock_coach_chat):

        up_res = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.docx", SAMPLE_DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        resume_id = up_res.json()["resume"]["id"]

        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={"target_role": "Backend Lead", "seniority_level": "senior", "interview_focus": "System Design", "practice_mode": "full", "resume_id": resume_id},
            headers=headers,
        )
        session_id = sess_res.json()["id"]

        start_res = await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)
        curr_turn_id = start_res.json()["id"]

        # 7 turns (Turn 0 answer + 6 questions)
        for i in range(7):
            ans_res = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/turns/{curr_turn_id}/answer",
                json={"candidate_answer": f"In-depth answer for full interview turn {i}"},
                headers=headers,
            )
            if not ans_res.json()["is_interview_complete"]:
                curr_turn_id = ans_res.json()["next_turn"]["id"]

        await client.post(f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers)
        coach_init_res = await client.post("/api/v1/coach/conversation", json={"session_id": session_id, "auto_debrief": True}, headers=headers)
        conversation_id = coach_init_res.json()["id"]

        for i in range(5):
            await client.post(
                "/api/v1/coach/chat",
                json={"conversation_id": conversation_id, "message": f"Message {i+1}"},
                headers=headers,
            )

        # 1 resume + 7 turns + 1 eval + 1 coach debrief + 5 coach chat = 15 calls
        assert len(call_log) == 15


@pytest.mark.asyncio
async def test_journey_d_existing_resume_reused(client: AsyncClient):
    """
    JOURNEY D:
    1. Existing resume reused (0 Gemini calls for resume parsing)
    2. Quick interview (4 turns = 4 calls)
    3. Final evaluation (1 call)
    4. Coach initial debrief (1 call)
    5. 5 Coach chat messages (5 calls)
    
    Total Gemini Calls: 0 + 4 + 1 + 1 + 5 = 11 calls.
    """
    call_log = []

    async def mock_parse_resume(*args, **kwargs):
        call_log.append("parse_resume")
        return ParsedResumeData(
            skills=["Python", "PostgreSQL"], experience_years=4.0, domains=["Backend"], education=[], summary="", projects=[], work_history=[]
        )

    async def mock_gen_initial_q(*args, **kwargs):
        call_log.append("generate_initial_question")
        return GeneratedQuestion(question_text="Q1", ideal_answer="Ans1", primary_concept="C1")

    turn_counter = 0

    async def mock_eval_and_gen_next(*args, **kwargs):
        nonlocal turn_counter
        turn_counter += 1
        call_log.append(f"evaluate_and_generate_next_turn_{turn_counter}")
        is_complete = turn_counter >= 3
        return NextTurnDecision(
            is_follow_up=False,
            question_text=f"Q{turn_counter + 1}" if not is_complete else "",
            ideal_answer="Ans",
            primary_concept="Concept",
            is_interview_complete=is_complete,
        )

    async def mock_eval_session(*args, **kwargs):
        call_log.append("evaluate_interview_session")
        return make_mock_session_eval()

    async def mock_coach_debrief(*args, **kwargs):
        call_log.append("generate_initial_debrief")
        return "### Coach Debrief\n\nWell done."

    async def mock_coach_chat(*args, **kwargs):
        call_log.append("generate_chat_reply")
        return {"coach_response": "Advice", "suggested_followups": []}

    headers = await _register_user(client, "journey_d@arovia.io")

    with patch("app.services.gemini_service.GeminiService.parse_resume", side_effect=mock_parse_resume):
        # Pre-upload resume
        up_res = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.docx", SAMPLE_DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        resume_id = up_res.json()["resume"]["id"]

    # Clear call log so we measure the journey itself
    call_log.clear()

    with patch("app.services.gemini_service.GeminiService.generate_initial_question", side_effect=mock_gen_initial_q), \
         patch("app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn", side_effect=mock_eval_and_gen_next), \
         patch("app.services.gemini_service.GeminiService.evaluate_interview_session", side_effect=mock_eval_session), \
         patch("app.services.coach_ai_service.CoachAIService.generate_initial_debrief", side_effect=mock_coach_debrief), \
         patch("app.services.coach_ai_service.CoachAIService.generate_chat_reply", side_effect=mock_coach_chat):

        # Setup Quick reusing resume_id
        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick", "resume_id": resume_id},
            headers=headers,
        )
        session_id = sess_res.json()["id"]

        start_res = await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)
        curr_turn_id = start_res.json()["id"]

        for i in range(4):
            ans_res = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/turns/{curr_turn_id}/answer",
                json={"candidate_answer": f"Answer for turn {i}"},
                headers=headers,
            )
            if not ans_res.json()["is_interview_complete"]:
                curr_turn_id = ans_res.json()["next_turn"]["id"]

        await client.post(f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers)
        coach_init_res = await client.post("/api/v1/coach/conversation", json={"session_id": session_id, "auto_debrief": True}, headers=headers)
        conversation_id = coach_init_res.json()["id"]

        for i in range(5):
            await client.post(
                "/api/v1/coach/chat",
                json={"conversation_id": conversation_id, "message": f"Message {i+1}"},
                headers=headers,
            )

        # 0 resume calls + 4 turn calls + 1 eval call + 1 coach debrief + 5 coach chat = 11 calls
        assert len(call_log) == 11
        assert "parse_resume" not in call_log


@pytest.mark.asyncio
async def test_journey_e_existing_resume_plus_custom_jd(client: AsyncClient):
    """
    JOURNEY E:
    1. Existing resume reused (0 calls)
    2. Custom JD parsed (1 call)
    3. Quick interview (4 turns = 4 calls)
    4. Final evaluation (1 call)
    5. Coach initial debrief (1 call)
    6. 5 Coach chat messages (5 calls)
    
    Total Gemini Calls: 0 + 1 + 4 + 1 + 1 + 5 = 12 calls.
    """
    call_log = []

    async def mock_parse_resume(*args, **kwargs):
        return ParsedResumeData(
            skills=["Python"], experience_years=3.0, domains=["Backend"], education=[], summary="", projects=[], work_history=[]
        )

    async def mock_parse_jd(*args, **kwargs):
        call_log.append("parse_job_description")
        return ParsedJobDescription(
            role_title="Senior Distributed Systems Engineer",
            required_skills=["Python", "Distributed Systems"],
            domain_focus="High Throughput APIs",
        )

    async def mock_gen_initial_q(*args, **kwargs):
        call_log.append("generate_initial_question")
        return GeneratedQuestion(question_text="Q1", ideal_answer="Ans1", primary_concept="C1")

    turn_counter = 0

    async def mock_eval_and_gen_next(*args, **kwargs):
        nonlocal turn_counter
        turn_counter += 1
        call_log.append(f"evaluate_and_generate_next_turn_{turn_counter}")
        is_complete = turn_counter >= 3
        return NextTurnDecision(
            is_follow_up=False,
            question_text=f"Q{turn_counter + 1}" if not is_complete else "",
            ideal_answer="Ans",
            primary_concept="Concept",
            is_interview_complete=is_complete,
        )

    async def mock_eval_session(*args, **kwargs):
        call_log.append("evaluate_interview_session")
        return make_mock_session_eval()

    async def mock_coach_debrief(*args, **kwargs):
        call_log.append("generate_initial_debrief")
        return "### Coach Debrief\n\nWell done."

    async def mock_coach_chat(*args, **kwargs):
        call_log.append("generate_chat_reply")
        return {"coach_response": "Advice", "suggested_followups": []}

    headers = await _register_user(client, "journey_e@arovia.io")

    with patch("app.services.gemini_service.GeminiService.parse_resume", side_effect=mock_parse_resume):
        up_res = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.docx", SAMPLE_DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        resume_id = up_res.json()["resume"]["id"]

    call_log.clear()

    with patch("app.services.gemini_service.GeminiService.parse_job_description", side_effect=mock_parse_jd), \
         patch("app.services.gemini_service.GeminiService.generate_initial_question", side_effect=mock_gen_initial_q), \
         patch("app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn", side_effect=mock_eval_and_gen_next), \
         patch("app.services.gemini_service.GeminiService.evaluate_interview_session", side_effect=mock_eval_session), \
         patch("app.services.coach_ai_service.CoachAIService.generate_initial_debrief", side_effect=mock_coach_debrief), \
         patch("app.services.coach_ai_service.CoachAIService.generate_chat_reply", side_effect=mock_coach_chat):

        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Distributed Systems Engineer",
                "seniority_level": "senior",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
                "resume_id": resume_id,
                "custom_job_desc": "Senior engineer wanted for high-throughput distributed systems.",
            },
            headers=headers,
        )
        session_id = sess_res.json()["id"]
        assert len(call_log) == 1
        assert call_log[-1] == "parse_job_description"

        start_res = await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)
        curr_turn_id = start_res.json()["id"]

        for i in range(4):
            ans_res = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/turns/{curr_turn_id}/answer",
                json={"candidate_answer": f"Answer for turn {i}"},
                headers=headers,
            )
            if not ans_res.json()["is_interview_complete"]:
                curr_turn_id = ans_res.json()["next_turn"]["id"]

        await client.post(f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers)
        coach_init_res = await client.post("/api/v1/coach/conversation", json={"session_id": session_id, "auto_debrief": True}, headers=headers)
        conversation_id = coach_init_res.json()["id"]

        for i in range(5):
            await client.post(
                "/api/v1/coach/chat",
                json={"conversation_id": conversation_id, "message": f"Message {i+1}"},
                headers=headers,
            )

        # 1 JD call + 4 turn calls + 1 eval call + 1 coach debrief + 5 coach chat = 12 calls
        assert len(call_log) == 12


@pytest.mark.asyncio
async def test_deterministic_and_passive_endpoints_produce_zero_gemini_calls(client: AsyncClient):
    """Verifies that progress, dashboard, refresh, and history endpoints make 0 Gemini calls."""
    headers = await _register_user(client, "zero_gemini@arovia.io")

    with patch("app.services.gemini_service.GeminiService.generate_initial_question", side_effect=RuntimeError("Passive Gemini call!")), \
         patch("app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn", side_effect=RuntimeError("Passive Gemini call!")), \
         patch("app.services.gemini_service.GeminiService.evaluate_interview_session", side_effect=RuntimeError("Passive Gemini call!")), \
         patch("app.services.gemini_service.GeminiService.parse_resume", side_effect=RuntimeError("Passive Gemini call!")), \
         patch("app.services.gemini_service.GeminiService.parse_job_description", side_effect=RuntimeError("Passive Gemini call!")):

        # Dashboard & progress endpoints
        prog_res = await client.get("/api/v1/progress", headers=headers)
        assert prog_res.status_code == 200

        insight_res = await client.get("/api/v1/progress/insight", headers=headers)
        assert insight_res.status_code == 200

        # Session listing
        sess_list_res = await client.get("/api/v1/interviews/sessions", headers=headers)
        assert sess_list_res.status_code == 200

        # Presets catalog
        presets_res = await client.get("/api/v1/interviews/presets")
        assert presets_res.status_code == 200


@pytest.mark.asyncio
async def test_gemini_429_fail_fast_and_503_bounded_retry():
    """Verifies that 429 fails fast with zero retries, and transient 503 is bounded to max 2 attempts."""
    from google.genai.errors import APIError

    service = GeminiService()

    # 1. 429 Fail Fast -> exactly 1 attempt, then immediately returns fallback question
    call_count_429 = 0
    mock_client_429 = MagicMock()
    
    async def raise_429(*args, **kwargs):
        nonlocal call_count_429
        call_count_429 += 1
        raise APIError(429, {"error": {"code": 429, "message": "RESOURCE_EXHAUSTED: Rate limit exceeded", "status": "RESOURCE_EXHAUSTED"}})

    mock_client_429.aio.models.generate_content = raise_429
    service._client = mock_client_429

    fallback_q = await service.generate_initial_question(
        target_role="Backend Engineer", seniority_level="mid", interview_focus="Technical Core"
    )
    assert call_count_429 == 1  # Exactly 1 attempt, zero retry amplification
    assert fallback_q.question_text is not None

    # 2. 503 Bounded Retry -> exactly 2 attempts, then falls back safely
    call_count_503 = 0
    mock_client_503 = MagicMock()

    async def raise_503(*args, **kwargs):
        nonlocal call_count_503
        call_count_503 += 1
        raise APIError(503, {"error": {"code": 503, "message": "UNAVAILABLE: Service temporarily unavailable", "status": "UNAVAILABLE"}})

    mock_client_503.aio.models.generate_content = raise_503
    service._client = mock_client_503

    fallback_q2 = await service.generate_initial_question(
        target_role="Backend Engineer", seniority_level="mid", interview_focus="Technical Core"
    )
    assert call_count_503 == 2  # Bounded to exactly 2 attempts
    assert fallback_q2.question_text is not None
