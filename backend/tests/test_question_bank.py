"""Unit tests for the AROVIA Structured Question Bank and Competency Architecture."""

import pytest
from app.services.interview_presets import ROLE_PRESETS, SENIORITY_LEVELS, FOCUS_AREAS
from app.services.question_bank import (
    BACKEND_BANK,
    FRONTEND_BANK,
    FULLSTACK_BANK,
    DEVOPS_BANK,
    DATA_BANK,
    ML_BANK,
    MOBILE_BANK,
    BEHAVIORAL_BANK,
    SYSTEM_DESIGN_BANK,
    UNIVERSAL_FOLLOWUPS,
    normalize_role_key,
    normalize_seniority_key,
    normalize_focus_key,
    get_competency_stages,
    get_fallback_question,
    get_fallback_followup,
    get_all_question_ids,
)


class TestRoleAndSeniorityResolution:
    """Test A & B: Normalization and resolution of roles, seniorities, and focus areas."""

    def test_role_normalization_canonical_presets(self):
        preset_ids = [p.role_id for p in ROLE_PRESETS]
        for role_id in preset_ids:
            normalized = normalize_role_key(role_id)
            assert normalized == role_id, f"Role preset '{role_id}' did not normalize to itself"

    @pytest.mark.parametrize(
        "raw_role,expected",
        [
            ("Backend Engineer", "backend-engineer"),
            ("Frontend React Developer", "frontend-engineer"),
            ("Full Stack Web Developer", "fullstack-engineer"),
            ("DevOps & Cloud SRE", "devops-cloud-engineer"),
            ("Data Engineer (ETL)", "data-engineer"),
            ("Machine Learning / AI Engineer", "ml-engineer"),
            ("Mobile iOS Flutter Developer", "mobile-engineer"),
            ("", "backend-engineer"),
            ("Unknown Role", "backend-engineer"),
        ],
    )
    def test_role_normalization_variations(self, raw_role, expected):
        assert normalize_role_key(raw_role) == expected

    @pytest.mark.parametrize(
        "raw_sen,expected",
        [
            ("junior", "junior"),
            ("Junior (0-2 years)", "junior"),
            ("entry-level", "junior"),
            ("mid", "mid"),
            ("Mid-Level (3-5 years)", "mid"),
            ("senior", "senior"),
            ("Senior (5+ years)", "senior"),
            ("Staff / Principal", "senior"),
            ("", "mid"),
        ],
    )
    def test_seniority_normalization(self, raw_sen, expected):
        assert normalize_seniority_key(raw_sen) == expected

    @pytest.mark.parametrize(
        "raw_focus,expected",
        [
            ("Technical Core", "Technical Core"),
            ("System Design", "System Design"),
            ("System Architecture", "System Design"),
            ("Behavioral", "Behavioral"),
            ("Behavioral & STAR", "Behavioral"),
            ("HR / Soft Skills", "Behavioral"),
            ("", "Technical Core"),
        ],
    )
    def test_focus_normalization(self, raw_focus, expected):
        assert normalize_focus_key(raw_focus) == expected


class TestCompetencyStagesAndQuestionBank:
    """Test C, D, E, G: Competency stages, core questions, follow-ups, and non-empty guarantees."""

    @pytest.mark.parametrize("preset", ROLE_PRESETS)
    @pytest.mark.parametrize("sen", ["junior", "mid", "senior"])
    def test_all_preset_roles_and_seniorities_return_stages(self, preset, sen):
        stages = get_competency_stages(role=preset.role_id, seniority=sen, focus="Technical Core")
        assert len(stages) >= 1, f"Expected stages for role={preset.role_id}, sen={sen}"
        
        for idx, stage in enumerate(stages):
            assert stage.stage_index == idx, f"Stage index mismatch in stage {stage.stage_name}"
            assert len(stage.stage_name) > 0
            assert len(stage.competency_title) > 0
            assert len(stage.description) > 0
            assert len(stage.core_questions) >= 1, f"Stage {stage.stage_name} has no core questions"

    @pytest.mark.parametrize("focus_id", ["System Design", "Behavioral"])
    @pytest.mark.parametrize("sen", ["junior", "mid", "senior"])
    def test_specialized_focus_areas_return_stages(self, focus_id, sen):
        stages = get_competency_stages(role="backend-engineer", seniority=sen, focus=focus_id)
        assert len(stages) >= 1
        for stage in stages:
            assert len(stage.core_questions) >= 1

    def test_core_questions_structure_and_followups(self):
        all_banks = [
            BACKEND_BANK,
            FRONTEND_BANK,
            FULLSTACK_BANK,
            DEVOPS_BANK,
            DATA_BANK,
            ML_BANK,
            MOBILE_BANK,
            BEHAVIORAL_BANK,
            SYSTEM_DESIGN_BANK,
        ]
        for bank in all_banks:
            for sen_level, stages in bank.items():
                for stage in stages:
                    for q in stage.core_questions:
                        assert len(q.id) > 0
                        assert len(q.question_text) > 10, f"Question text too short: {q.id}"
                        assert len(q.ideal_answer) > 10, f"Ideal answer too short: {q.id}"
                        assert len(q.primary_concept) > 0
                        assert q.difficulty in ["foundational", "intermediate", "advanced", "junior", "mid", "senior"]
                        for f in q.follow_ups:
                            assert len(f.id) > 0
                            assert len(f.prompt) > 10, f"Follow-up prompt too short: {f.id}"
                            assert len(f.target_probe) > 0
                            assert len(f.ideal_focus) > 0


class TestGlobalQuestionIDUniqueness:
    """Test F: Global uniqueness of all QuestionTemplate and FollowUpTemplate IDs."""

    def test_all_question_ids_are_globally_unique(self):
        ids_seen = set()
        duplicates = []

        all_banks = [
            BACKEND_BANK,
            FRONTEND_BANK,
            FULLSTACK_BANK,
            DEVOPS_BANK,
            DATA_BANK,
            ML_BANK,
            MOBILE_BANK,
            BEHAVIORAL_BANK,
            SYSTEM_DESIGN_BANK,
        ]

        for bank in all_banks:
            for sen_level, stages in bank.items():
                for stage in stages:
                    for q in stage.core_questions:
                        if q.id in ids_seen:
                            duplicates.append(q.id)
                        ids_seen.add(q.id)
                        for f in q.follow_ups:
                            if f.id in ids_seen:
                                duplicates.append(f.id)
                            ids_seen.add(f.id)

        for uf in UNIVERSAL_FOLLOWUPS:
            if uf.id in ids_seen:
                duplicates.append(uf.id)
            ids_seen.add(uf.id)

        assert not duplicates, f"Found duplicate question/followup IDs: {duplicates}"
        assert len(ids_seen) == len(get_all_question_ids())
        assert len(ids_seen) > 30, f"Expected substantial question catalog, got {len(ids_seen)}"


class TestFallbackCandidateSelection:
    """Test H: Fallback question and follow-up selection for supported combinations."""

    @pytest.mark.parametrize("preset", ROLE_PRESETS)
    @pytest.mark.parametrize("sen", ["junior", "mid", "senior"])
    def test_fallback_question_resolution(self, preset, sen):
        q = get_fallback_question(role=preset.role_id, seniority=sen, stage_index=0)
        assert q is not None
        assert len(q.question_text) > 10
        assert q.id != "univ.fallback.core.01", f"Should have found domain question for {preset.role_id}"

    def test_fallback_question_exclusion_advancement(self):
        stages = get_competency_stages(role="backend-engineer", seniority="mid")
        first_q = stages[0].core_questions[0]
        
        # When first question is excluded, it should advance to next question/stage
        second_q = get_fallback_question(
            role="backend-engineer",
            seniority="mid",
            stage_index=0,
            excluded_question_ids={first_q.id},
        )
        assert second_q.id != first_q.id

    def test_fallback_followup_retrieval(self):
        f = get_fallback_followup(role="backend-engineer", seniority="senior")
        assert f is not None
        assert len(f.prompt) > 10
        assert len(f.target_probe) > 0

    def test_universal_fallback_when_exhausted(self):
        all_ids = get_all_question_ids()
        q = get_fallback_question(
            role="backend-engineer",
            seniority="mid",
            stage_index=0,
            excluded_question_ids=all_ids,
        )
        # When all excluded, target stage question or universal fallback is returned
        assert q is not None
        assert len(q.question_text) > 0
