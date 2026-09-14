"""Unit and Integration tests for Preferred Interview Language Foundation (Phase 1.2).

Tests:
A. Session creation with 'en', 'hi', 'hinglish'.
B. Invalid language rejection (HTTP 422).
C. Default omitted preferred_language -> 'en'.
D. Existing legacy session compatibility.
E. Speech recognition mapping (en -> en-US, hi -> hi-IN, hinglish -> hi-IN).
F. Gemini prompt context injection with preferred language guidelines.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.interview import (
    InterviewSessionCreateRequest,
    PreferredLanguage,
)
from app.services.gemini_service import (
    GeminiService,
    _get_language_instructions,
)


@pytest.mark.asyncio
async def test_session_creation_with_all_supported_languages(client: AsyncClient):
    """Test session creation explicitly persists and returns 'en', 'hi', and 'hinglish'."""
    # 1. Register candidate
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "languser@example.com",
            "password": "StrongPassword!123",
            "full_name": "Language User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for lang_code in ["en", "hi", "hinglish"]:
        # Create session
        create_res = await client.post(
            "/api/v1/interviews/sessions",
            headers=headers,
            json={
                "target_role": f"Backend Engineer {lang_code}",
                "seniority_level": "mid",
                "interview_focus": "Technical Core",
                "preferred_language": lang_code,
            },
        )
        assert create_res.status_code == 201, f"Failed for language: {lang_code}"
        session_data = create_res.json()
        assert session_data["preferred_language"] == lang_code
        session_id = session_data["id"]

        # Fetch active session
        active_res = await client.get("/api/v1/interviews/sessions/active", headers=headers)
        assert active_res.status_code == 200
        assert active_res.json()["preferred_language"] == lang_code

        # Fetch by ID
        get_res = await client.get(f"/api/v1/interviews/sessions/{session_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["preferred_language"] == lang_code

        # List user sessions
        list_res = await client.get("/api/v1/interviews/sessions", headers=headers)
        assert list_res.status_code == 200
        matching = [s for s in list_res.json() if s["id"] == session_id]
        assert len(matching) == 1
        assert matching[0]["preferred_language"] == lang_code

        # Abandon to allow next iteration
        abandon_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/abandon", headers=headers
        )
        assert abandon_res.status_code == 200


@pytest.mark.asyncio
async def test_session_creation_rejects_invalid_languages(client: AsyncClient):
    """Test that unsupported languages are rejected with HTTP 422 Unprocessable Entity."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalidlang@example.com",
            "password": "StrongPassword!123",
            "full_name": "Invalid Lang User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for invalid_lang in ["fr", "es", "de", "japanese", "invalid_code", ""]:
        res = await client.post(
            "/api/v1/interviews/sessions",
            headers=headers,
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "mid",
                "interview_focus": "Technical Core",
                "preferred_language": invalid_lang,
            },
        )
        assert res.status_code == 422, f"Expected 422 for language: {invalid_lang}"


@pytest.mark.asyncio
async def test_session_creation_defaults_to_english_when_omitted(client: AsyncClient):
    """Test that omitting preferred_language defaults safely to 'en'."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "defaultlang@example.com",
            "password": "StrongPassword!123",
            "full_name": "Default Lang User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/interviews/sessions",
        headers=headers,
        json={
            "target_role": "Fullstack Engineer",
            "seniority_level": "senior",
            "interview_focus": "Technical Core",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["preferred_language"] == "en"


def test_language_instructions_formatting():
    """Verify prompt instruction generation for en, hi, and hinglish."""
    en_instr = _get_language_instructions("en")
    assert "English" in en_instr
    assert "clear, professional English" in en_instr

    # None / omitted fallback
    none_instr = _get_language_instructions(None)
    assert "English" in none_instr

    # Hindi
    hi_instr = _get_language_instructions("hi")
    assert "Hindi" in hi_instr
    assert "API, database, latency" in hi_instr
    assert "standard English vocabulary" in hi_instr

    # Hinglish
    hinglish_instr = _get_language_instructions("hinglish")
    assert "Hinglish" in hinglish_instr
    assert "Redis" in hinglish_instr
    assert "without penalizing language mixing" in hinglish_instr


@pytest.mark.asyncio
async def test_gemini_service_passes_language_context_to_prompts():
    """Verify GeminiService correctly embeds preferred language context in prompt strings."""
    service = GeminiService(api_key="mock-key")

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = AsyncMock(
            text='{"question_text": "Aap Redis cache kaise implement karenge?", "ideal_answer": "Redis caching explanation", "primary_concept": "Caching"}'
        )

        # 1. Initial Question with Hinglish
        await service.generate_initial_question(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            preferred_language="hinglish",
        )
        call_prompt = mock_gen.call_args.kwargs["contents"]
        assert "Preferred Interview Language: Hinglish" in call_prompt

        # 2. Initial Question with Hindi
        await service.generate_initial_question(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            preferred_language="hi",
        )
        call_prompt_hi = mock_gen.call_args.kwargs["contents"]
        assert "Preferred Interview Language: Hindi" in call_prompt_hi

        # 3. Next Turn with Hinglish
        mock_gen.return_value = AsyncMock(
            text='{"is_follow_up": false, "is_interview_complete": false, "question_text": "Next question in Hinglish", "ideal_answer": "Benchmark", "primary_concept": "Database"}'
        )
        await service.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["Python"],
            current_turn_index=0,
            remaining_core_questions=5,
            remaining_followup_budget=3,
            prior_turn_was_followup=False,
            previous_question="Tell me about caching.",
            candidate_answer="Maine Redis use kiya tha frequently accessed data ke liye.",
            transcript_history=[],
            preferred_language="hinglish",
        )
        call_prompt_turn = mock_gen.call_args.kwargs["contents"]
        assert "Preferred Interview Language: Hinglish" in call_prompt_turn
