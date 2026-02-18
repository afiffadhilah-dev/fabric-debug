Analyze the following skill and its evidence to extract 6 dimensions of experience.

## SKILL INFORMATION
Skill Name: {skill_name}

Evidence:
{evidence_text}

## DIMENSIONS TO ANALYZE

For each dimension, provide SHORT KEYWORDS OR PHRASES (2-5 words maximum) based on the evidence:

1. **duration**: How long has the candidate worked with this skill? (e.g., "6 months", "2 years", "long-term", "recent")
2. **depth**: How deep is the candidate's knowledge? (e.g., "advanced", "intermediate", "expert", "deep understanding")
3. **autonomy**: How independently did the candidate work? (e.g., "led team", "independent", "collaborative", "decision maker")
4. **scale**: What was the scale/scope of work? (e.g., "large system", "6 services", "200+ components", "enterprise")
5. **constraint**: What challenges did they face? (e.g., "performance issues", "migration complexity", "resource limits")
6. **production**: Was this used in production? (e.g., "production ready", "deployed", "live system", "real impact")

## OUTPUT SCHEMA
Return JSON:
{{
  "duration": "string - short phrase (2-5 words) about time/experience duration",
  "depth": "string - short phrase (2-5 words) about technical depth",
  "autonomy": "string - short phrase (2-5 words) about independence/leadership",
  "scale": "string - short phrase (2-5 words) about scale/scope",
  "constraint": "string - short phrase (2-5 words) about challenges faced",
  "production": "string - short phrase (2-5 words) about production usage"
}}

## RULES
- Base analysis ONLY on the provided evidence
- Use SHORT keywords or phrases (2-5 words maximum per dimension)
- Be specific and factual, avoid generic statements
- If evidence is insufficient for a dimension, use "N/A"
- Examples of good short values: "2 years", "advanced level", "led migration", "6 microservices", "performance optimization", "production deployed"

