# Skill Attributes Extraction

You are analyzing a resume and conversation to extract technical skills with detailed attributes.

For each skill mentioned in the resume or conversation, extract the following 6 attributes:

1. **Duration**: How long they've used the skill (e.g., "3 years", "6 months", "2+ years")
2. **Depth**: Complexity level and aspects implemented (e.g., "basic CRUD operations", "advanced query optimization", "architectural design")
3. **Autonomy**: Ownership level and independence (e.g., "solo project", "led team of 5", "contributed to team", "self-directed")
4. **Scale**: Impact size (e.g., "10M users", "enterprise-scale", "startup MVP", "100K requests/day")
5. **Constraints**: Limitations or challenges encountered (e.g., "legacy system integration", "tight deadlines", "limited resources", "regulatory compliance")
6. **Production vs Prototype**: Indicate whether this was production-ready code or a prototype
   - Values: "production", "prototype", "PoC", or "unknown"

## Important Rules:

- If an attribute is **not explicitly mentioned** in the resume or conversation, mark it as **"unknown"**
- Do not infer or guess - only extract what is explicitly stated
- For each skill, provide evidence (direct quotes or paraphrased context from the source)
- Multiple projects using the same skill should be consolidated into one entry

## Output Format:

Return a JSON object with the following structure:

```json
{{
  "skills": [
    {{
      "name": "Python",
      "duration": "3 years",
      "depth": "advanced web frameworks, async programming",
      "autonomy": "led team of 3 developers",
      "scale": "5M monthly active users",
      "constraints": "legacy Django codebase",
      "production_vs_prototype": "production",
      "evidence": "Built scalable API serving 5M users using Django and async patterns",
      "confidence_score": 0.9
    }},
    {{
      "name": "React",
      "duration": "unknown",
      "depth": "component development, hooks",
      "autonomy": "unknown",
      "scale": "unknown",
      "constraints": "unknown",
      "production_vs_prototype": "unknown",
      "evidence": "Developed user interface components using React hooks",
      "confidence_score": 0.7
    }}
  ]
}}
```

## Confidence Score Guidelines:

- **0.9-1.0**: Multiple pieces of evidence, specific details, production context
- **0.7-0.8**: Clear mention with some details
- **0.5-0.6**: Brief mention, limited context
- **0.3-0.4**: Implied or inferred skill

Now extract skills from the following sources:
