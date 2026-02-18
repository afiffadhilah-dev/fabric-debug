You are extracting **Infrastructure & Operations Context** from interview answers.

Your task is to identify **distinct operating environments** the candidate worked in.
Each operating environment must become **one InfrastructureContext row**.

An operating environment is defined by:

- What kind of environment it was
- How large it was
- How critical or reliable it needed to be
- What operational or regulatory constraints applied

DO NOT list tools or technologies as standalone items.
DO NOT output labels like “Kubernetes”, “Spark”, “AWS”.

---

### Answers

{answers}

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
  “Healthcare compliance”, “Nightly reporting deadlines”, “Regulated data”, “Legacy systems”, or null if not mentioned

- `evidence`  
  A short quote or paraphrase from the interview showing why this was inferred

- `confidence`  
  One of: Low | Low-Medium | Medium | Medium-High | High

---

### Return JSON ONLY in this format

```json
{{
  "candidate_id": "string",
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
