"""
Identify gaps node - analyzes resume to find missing skill information.
"""

from typing import Dict, Any, List
from agents.conversational.state import InterviewState, Gap, Skill
from tools.extraction_tools import extract_skills_from_conversation


def identify_gaps_node(state: InterviewState) -> Dict[str, Any]:
    """
    Analyze resume to identify skill gaps.

    Uses SkillAnalyzer to extract skills with 6 attributes.
    For each attribute marked as "unknown", creates a gap.

    Returns:
        Dictionary with updates:
        - identified_gaps: List[Gap]
        - extracted_skills: List[Skill]
        - completeness_score: float
    """
    resume_text = state["resume_text"]

    # Extract skills with attributes from resume
    skills = extract_skills_from_conversation(resume_text, conversation_history=[])

    # Convert to Skill TypedDict format
    extracted_skills: List[Skill] = []
    for skill in skills:
        extracted_skills.append({
            "name": skill["name"],
            "confidence_score": skill.get("confidence_score", 1.0),
            "duration": skill.get("duration"),
            "depth": skill.get("depth"),
            "autonomy": skill.get("autonomy"),
            "scale": skill.get("scale"),
            "constraints": skill.get("constraints"),
            "production_vs_prototype": skill.get("production_vs_prototype"),
            "evidence": skill.get("evidence", "")
        })

    # Identify gaps (attributes marked as "unknown")
    identified_gaps: List[Gap] = []

    for skill in extracted_skills:
        unknown_attrs = []

        # Check each of the 6 attributes
        if skill.get("duration") == "unknown":
            unknown_attrs.append("duration")
        if skill.get("depth") == "unknown":
            unknown_attrs.append("depth")
        if skill.get("autonomy") == "unknown":
            unknown_attrs.append("autonomy")
        if skill.get("scale") == "unknown":
            unknown_attrs.append("scale")
        if skill.get("constraints") == "unknown":
            unknown_attrs.append("constraints")
        if skill.get("production_vs_prototype") == "unknown":
            unknown_attrs.append("production_vs_prototype")

        # Create gap if there are unknown attributes
        if unknown_attrs:
            # Calculate severity based on number of unknowns and confidence
            num_unknowns = len(unknown_attrs)
            confidence = skill.get("confidence_score", 0.5)

            # High priority: 3+ unknowns or high confidence skill
            # Medium priority: 2-3 unknowns
            # Low priority: 1 unknown or low confidence
            if num_unknowns >= 3 and confidence >= 0.7:
                severity = 0.9
            elif num_unknowns >= 2:
                severity = 0.6
            else:
                severity = 0.3

            # Create gap
            gap: Gap = {
                "category": "technical_skill",
                "description": f"Missing {', '.join(unknown_attrs)} for {skill['name']}",
                "severity": severity,
                "context": f"{skill['name']} skill - need: {', '.join(unknown_attrs)}",
                "probes_attempted": 0,
                "max_probes": 3,
                "probe_history": []  # Track answer types for intelligent probe limits
            }
            identified_gaps.append(gap)

    # Sort gaps by severity (highest first)
    identified_gaps.sort(key=lambda g: g["severity"], reverse=True)

    # Calculate initial completeness score
    # Completeness = (total attributes - unknown attributes) / total attributes
    total_attributes = len(extracted_skills) * 6 if extracted_skills else 1
    unknown_count = sum(len([
        attr for attr in [
            skill.get("duration"),
            skill.get("depth"),
            skill.get("autonomy"),
            skill.get("scale"),
            skill.get("constraints"),
            skill.get("production_vs_prototype")
        ] if attr == "unknown"
    ]) for skill in extracted_skills)

    completeness_score = max(0.0, (total_attributes - unknown_count) / total_attributes)

    print(f"Identified {len(extracted_skills)} skills with {len(identified_gaps)} gaps")
    print(f"Initial completeness: {completeness_score:.2%}")

    return {
        "identified_gaps": identified_gaps,
        "extracted_skills": extracted_skills,
        "completeness_score": completeness_score
    }
