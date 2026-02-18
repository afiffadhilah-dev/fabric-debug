You are extracting **Business & Domain Context** from a resume.

Your task is to identify **distinct business environments** the candidate has worked in.
Each environment should become **one DomainContext row**.

A business environment is defined by:

- The industry
- The type of product or system
- Who it served
- How the business made money or used it
- Whether regulation or compliance applied
- How critical the system was to the business

DO NOT list technologies, tools, programming languages, or infrastructure.
DO NOT output vague labels like “Business”, “Domain”, or “Platform”.

---

### Resume

{resume_text}

---

### For each distinct business environment you find, infer:

- `industry`  
  (e.g. Healthcare, Fintech, E-commerce, SaaS, Logistics)

- `product_type`  
  (e.g. Analytics platform, Internal tool, Customer-facing web app, Data platform)

- `business_model`  
  (e.g. B2B, B2C, Enterprise, Internal, Marketplace)

- `customer_type`  
  (e.g. Hospitals, Insurance providers, Finance teams, Executives, Consumers, Internal teams)

- `regulatory_or_compliance_context`  
  (e.g. Healthcare, Financial, PII, None mentioned)

- `business_criticality`  
  (e.g. Low, Moderate, High, Revenue-impacting, Compliance-critical)

- `evidence`  
  A short quote or paraphrase from the resume that supports this classification.

- `confidence`  
  One of: Low | Low-Medium | Medium | Medium-High | High

---

### Return JSON ONLY in this format

```json
{{
  "candidate_id": "{candidate_id}",
  "domain_contexts": [
    {{
      "industry": "string or null",
      "product_type": "string or null",
      "business_model": "string or null",
      "customer_type": "string or null",
      "regulatory_or_compliance_context": "string or null",
      "business_criticality": "string or null",
      "evidence": "string",
      "confidence": "Low | Low-Medium | Medium | Medium-High | High"
    }}
  ]
}}
```
