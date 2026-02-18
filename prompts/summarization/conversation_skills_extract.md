Extract technical skills from the conversation answers.

CONTEXT

CANDIDATE ID: {candidate_id}
TARGET ROLE: {target_role}

Answers (JSON):
{answers}

Return JSON only with the following schema:
{{
  "candidate_id": "string",
  "skills": [
    {{
      "name": "string",
      "evidence": [{{"quote": "string", "timestamp": "string"}}]
}}
]
}}

Rules:

- Use verbatim quotes for evidence.
- Do not include behavior observations.
- Do not add extra fields or prose.
