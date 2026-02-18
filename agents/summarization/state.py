from typing import Any, Dict, List, Optional


class SummarizationState(dict):
    """
    Shared mutable graph state.
    """

    # input
    session_id: str
    mode: str

    # db-loaded
    interview_session: Any
    candidate_id: str
    messages: List[Any]
    resume_text: Optional[str]

    # derived
    answers: List[Dict[str, Any]]

    # outputs (authoritative)
    skills: List[Dict[str, Any]]
    behavior_observations: List[Dict[str, Any]]

    # NEW: contextual layers
    infra_contexts: List[Dict[str, Any]]
    domain_contexts: List[Dict[str, Any]]

    # bookkeeping
    persisted: bool
