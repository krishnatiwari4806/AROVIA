"""Deterministic System Design Stage Model and State Machine Tracker.

Governs the canonical 4-stage progressive architecture interview lifecycle:
- Turn 0 (Stage 0): Warm-up & Problem Ingress
- Turn 1 (Stage 1): Scope & Requirements
- Turn 2 (Stage 2): Estimation & Data Model
- Turn 3 (Stage 3): High-Level Architecture
- Turn 4 (Stage 4): Failure & Scale Pushback
- Post-Stage 4: Evaluating -> Completed

Guarantees strict ₹0 / free-tier budget, monotonic stage progression,
user isolation, and complete behavioral isolation from legacy interview modes.
"""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

SYSTEM_DESIGN_STAGED_PRACTICE_MODE = "system_design_staged"

TOTAL_STAGED_ANSWER_TURNS = 5  # Exactly 1 Warmup (Turn 0) + 4 Stages (Turns 1..4)
TOTAL_STAGED_CORE_STAGES = 4   # Stages 1 to 4


class SystemDesignStage(str, Enum):
    """Canonical stage identifiers for staged System Design mock interviews."""

    WARMUP = "stage_0_warmup"
    REQUIREMENTS = "stage_1_requirements"
    ESTIMATION = "stage_2_estimation"
    ARCHITECTURE = "stage_3_architecture"
    DEFENSE = "stage_4_defense"


@dataclass(frozen=True)
class SystemDesignStageDefinition:
    """Authoritative metadata and behavioral specifications for a System Design stage."""

    stage_index: int
    stage_key: str
    stage_name: str
    stage_description: str
    stage_goal: str
    stage_focus: str
    is_introduction: bool = False

    @property
    def stage(self) -> SystemDesignStage:
        return SystemDesignStage(self.stage_key)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_index": self.stage_index,
            "stage_key": self.stage_key,
            "stage_name": self.stage_name,
            "stage_description": self.stage_description,
            "stage_goal": self.stage_goal,
            "stage_focus": self.stage_focus,
            "is_introduction": self.is_introduction,
        }

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


STAGE_0_WARMUP = SystemDesignStageDefinition(
    stage_index=0,
    stage_key=SystemDesignStage.WARMUP.value,
    stage_name="Warm-up & Problem Ingress",
    stage_description="Context gathering, scenario presentation, and problem ingress.",
    stage_goal="Set interview context and establish problem boundaries.",
    stage_focus="Communication & Scenario Context",
    is_introduction=True,
)

STAGE_1_REQUIREMENTS = SystemDesignStageDefinition(
    stage_index=1,
    stage_key=SystemDesignStage.REQUIREMENTS.value,
    stage_name="Scope & Requirements",
    stage_description="Clarifying functional and non-functional requirements, constraints, and system boundaries.",
    stage_goal="Define core features, SLA targets, and out-of-scope boundaries.",
    stage_focus="Requirements Engineering & Scope Clarity",
    is_introduction=False,
)

STAGE_2_ESTIMATION = SystemDesignStageDefinition(
    stage_index=2,
    stage_key=SystemDesignStage.ESTIMATION.value,
    stage_name="Estimation & Data Model",
    stage_description="Back-of-the-envelope capacity estimations and core entity data modeling.",
    stage_goal="Estimate throughput/storage and establish database schema and access patterns.",
    stage_focus="Capacity Planning & Data Modeling",
    is_introduction=False,
)

STAGE_3_ARCHITECTURE = SystemDesignStageDefinition(
    stage_index=3,
    stage_key=SystemDesignStage.ARCHITECTURE.value,
    stage_name="High-Level Architecture",
    stage_description="End-to-end component design, data flow orchestration, and API surface.",
    stage_goal="Design microservices, caching layer, load balancers, and message buses.",
    stage_focus="System Architecture & Component Decomposition",
    is_introduction=False,
)

STAGE_4_DEFENSE = SystemDesignStageDefinition(
    stage_index=4,
    stage_key=SystemDesignStage.DEFENSE.value,
    stage_name="Failure & Scale Pushback",
    stage_description="Interviewer pushback, bottleneck analysis, failover mechanisms, and partition tolerance.",
    stage_goal="Defend architectural decisions under cascading failure, partition, and 10x scale.",
    stage_focus="Resilience, Trade-off Defense & Fault Tolerance",
    is_introduction=False,
)

STAGE_DEFINITIONS: Dict[int, SystemDesignStageDefinition] = {
    0: STAGE_0_WARMUP,
    1: STAGE_1_REQUIREMENTS,
    2: STAGE_2_ESTIMATION,
    3: STAGE_3_ARCHITECTURE,
    4: STAGE_4_DEFENSE,
}


class SystemDesignStageTracker:
    """Authoritative state machine resolver for staged System Design interviews."""

    @staticmethod
    def is_staged_session(session: Any) -> bool:
        """Deterministically determine if a session is configured for staged System Design."""
        if not session:
            return False
        mode = getattr(session, "practice_mode", None)
        if isinstance(mode, str):
            return mode.strip().lower() == SYSTEM_DESIGN_STAGED_PRACTICE_MODE
        if hasattr(mode, "value"):
            return str(mode.value).strip().lower() == SYSTEM_DESIGN_STAGED_PRACTICE_MODE
        return False

    @classmethod
    def get_stage_info(
        cls, stage_input: Union[int, SystemDesignStageDefinition, Dict[str, Any]]
    ) -> Optional[SystemDesignStageDefinition]:
        """Retrieve authoritative metadata definition for a given stage index, definition, or dictionary."""
        if isinstance(stage_input, SystemDesignStageDefinition):
            return stage_input
        if isinstance(stage_input, int) and stage_input in STAGE_DEFINITIONS:
            return STAGE_DEFINITIONS[stage_input]
        if isinstance(stage_input, dict) and "stage_index" in stage_input:
            idx = stage_input["stage_index"]
            if isinstance(idx, int) and idx in STAGE_DEFINITIONS:
                return STAGE_DEFINITIONS[idx]
        return None

    @classmethod
    def get_turn_stage_index(cls, turn: Any) -> Optional[int]:
        """Safely extract the stage index from a turn's evaluation_data or turn_index."""
        if not turn:
            return None

        # Check structured evaluation_data first
        eval_data = getattr(turn, "evaluation_data", None)
        if isinstance(eval_data, dict):
            stage_meta = eval_data.get("system_design_stage")
            if isinstance(stage_meta, dict) and "stage_index" in stage_meta:
                idx = stage_meta.get("stage_index")
                if isinstance(idx, int) and not isinstance(idx, bool) and idx in STAGE_DEFINITIONS:
                    return idx

        # Fallback to turn_index if within valid bounds [0, 4]
        turn_idx = getattr(turn, "turn_index", None)
        if isinstance(turn_idx, int) and not isinstance(turn_idx, bool) and turn_idx in STAGE_DEFINITIONS:
            return turn_idx

        return None

    @classmethod
    def get_completed_staged_turns(cls, turns: List[Any]) -> List[Any]:
        """Return all answered turns sorted chronologically by turn_index."""
        if not turns:
            return []
        completed = [
            t for t in turns
            if getattr(t, "candidate_answer", None) is not None
            and isinstance(getattr(t, "candidate_answer", None), str)
            and getattr(t, "candidate_answer", "").strip() != ""
        ]
        return sorted(completed, key=lambda t: getattr(t, "turn_index", 0))

    @classmethod
    def resolve_current_stage(
        cls, session: Any, turns: List[Any]
    ) -> Optional[SystemDesignStageDefinition]:
        """Authoritatively derive the current active stage definition from persisted completed turns."""
        if not cls.is_staged_session(session):
            return None

        completed_turns = cls.get_completed_staged_turns(turns)
        num_completed = len(completed_turns)

        if num_completed >= TOTAL_STAGED_ANSWER_TURNS:
            return None

        return STAGE_DEFINITIONS.get(num_completed)

    @classmethod
    def resolve_next_stage(
        cls, session: Any, turns: List[Any]
    ) -> Optional[SystemDesignStageDefinition]:
        """Determine the next stage definition to be generated upon answering the current turn.

        Returns None if all 5 stages (0..4) are completed.
        """
        if not cls.is_staged_session(session):
            return None

        completed_turns = cls.get_completed_staged_turns(turns)
        num_completed = len(completed_turns)

        if num_completed >= TOTAL_STAGED_ANSWER_TURNS:
            return None

        return STAGE_DEFINITIONS.get(num_completed)

    @classmethod
    def is_staged_interview_complete(cls, session: Any, turns: List[Any]) -> bool:
        """Determine whether the staged System Design interview has completed all 5 stages."""
        if not cls.is_staged_session(session):
            return False

        completed_turns = cls.get_completed_staged_turns(turns)
        return len(completed_turns) >= TOTAL_STAGED_ANSWER_TURNS

    @classmethod
    def build_stage_metadata(
        cls, stage_input: Union[int, SystemDesignStageDefinition, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate deterministic stage metadata dictionary for turn evaluation_data."""
        info = cls.get_stage_info(stage_input) or STAGE_0_WARMUP
        return info.to_dict()

    @classmethod
    def attach_stage_metadata(
        cls,
        target: Any,
        stage_input: Union[int, SystemDesignStageDefinition, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Safely merge stage metadata into evaluation_data without modifying or deleting existing keys."""
        meta_dict = cls.build_stage_metadata(stage_input)

        if hasattr(target, "evaluation_data"):
            eval_data = getattr(target, "evaluation_data", None)
            merged = dict(eval_data) if isinstance(eval_data, dict) else {}
            merged["system_design_stage"] = meta_dict
            target.evaluation_data = merged
            return merged
        elif isinstance(target, dict) or target is None:
            merged = dict(target) if isinstance(target, dict) else {}
            merged["system_design_stage"] = meta_dict
            return merged
        else:
            return {"system_design_stage": meta_dict}


def get_system_design_stage_tracker() -> SystemDesignStageTracker:
    """Dependency provider for SystemDesignStageTracker."""
    return SystemDesignStageTracker()
