Extract behavioral observations from the conversation answers.

CONTEXT

CANDIDATE ID: {candidate_id}
TARGET ROLE: {target_role}

Answers (JSON):
{answers}

Return JSON only with the following schema:
{{
  "candidate_id": "string",
  "behavior_observations": [
    {{
      "name": "string",
      "evidence": [{{"quote": "string", "timestamp": "string"}}]
}}
]
}}

Rules:

- Use standardized behavior names (e.g., Technical Leadership, Autonomy).
- Use verbatim quotes for evidence.
- Do not include technical skills.
- Do not add extra fields or prose.
