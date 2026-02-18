Extract skills and behavioral observations from the conversation answers.

PERSON ID: {candidate_id}
TARGET ROLE: {target_role}

All Q&A pairs are prefixed with their timestamp in the format `[YYYY-MM-DD HH:MM:SS]`.

## OUTPUT SCHEMA

Return JSON:
{{
  "person_id": "string",
  "skills": [
    {{
      "name": "Pure Technical Name",
      "evidence": [
        {{
          "quote": "verbatim quote",
          "timestamp": "YYYY-MM-DD HH:MM:SS"
        }}
]
}}
],
"behavior_observations": [
{{
      "name": "Standardized Behavior Name",
      "evidence": [
        {{
          "quote": "verbatim quote",
          "timestamp": "YYYY-MM-DD HH:MM:SS"
        }}
]
}}
]
}}

## NAMING & GROUPING PRINCIPLES

- **Identify the Core Tech**: For every skill, identify the core technical entity. Use ONLY its primary name.
- **Architectural Grouping**: Analyze the functional relationship. If multiple technologies are described as parts of a single functional pipeline or system (e.g., a data streaming pipeline, a CI/CD stack), group them under the name of the **central/dominating technology** of that system.
- **Ecosystem Consolidation**: Group libraries, drivers, and frameworks under their parent technology to show depth.
- **No Hardcoding**: Evaluate each relationship dynamically based on how the candidate describes their interaction with the tools.

## RULES

- Verbatim quotes only.
- Up to 3 quotes per skill.

CONVERSATION:
{conversation_text}
