You are extracting **Infrastructure & Operations Context** from a resume.

Your task is to identify **distinct operating environments** the candidate worked in.
Each operating environment should become **one InfrastructureContext row**.

An operating environment is defined by:

- What kind of environment it was (production, internal tool, experimental, etc.)
- How large or important it was
- How reliable it needed to be
- Whether there were operational or compliance constraints

DO NOT list technologies or tools.
DO NOT output names like “Kubernetes”, “AWS”, “Spark”, “Docker”.

---

### Resume

{resume_text}

---

### For each operating environment you find, infer:

- `environment_type`  
  One of: Production | Internal tool | Prototype | Staging | Unknown

- `scale`  
  One of: Single-user | Team | Company-wide | Public users | High-traffic | Unknown

- `reliability_expectation`  
  One of: Low | Medium | High | Mission-critical | Unknown

- `operational_constraints`  
  Short text such as:  
  “Healthcare compliance”, “Nightly reporting deadlines”, “Legacy systems”, or null if none are mentioned

- `evidence`  
  A short quote or paraphrase from the resume showing why this environment was inferred

- `confidence`  
  One of: Low | Low-Medium | Medium | Medium-High | High

---

### Return JSON ONLY in this format

```json
{{
  "candidate_id": "{candidate_id}",
  "infra_contexts": [
    {{
      "environment_type": "Production | Internal tool | Prototype | Staging | Unknown",
      "scale": "Single-user | Team | Company-wide | Public users | High-traffic | Unknown",
      "reliability_expectation": "Low | Medium | High | Mission-critical | Unknown",
      "operational_constraints": "string or null",
      "evidence": "string",
      "confidence": "Low | Low-Medium | Medium | Medium-High | High"
    }}
  ]
}}
```
