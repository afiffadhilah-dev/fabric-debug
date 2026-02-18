You are extracting **Business & Domain Context** from interview answers.

Your task is to identify **distinct business environments** the candidate has worked in.
Each business environment should become **one DomainContext row**.

A business environment is defined by:

- The industry
- What kind of product or system it was
- Who used it
- How it supported the business
- Whether regulation or compliance applied
- How critical it was to the business

DO NOT list technologies, tools, programming languages, or infrastructure.
DO NOT output vague labels like “Business” or “Domain”.

---

### Interview Answers

{answers}

---

### For each distinct business environment you find, infer:

- `industry`  
  (e.g. Healthcare, Fintech, E-commerce, SaaS, Logistics)

- `product_type`  
  (e.g. Analytics platform, Internal tool, Customer-facing app, Reporting system)

- `business_model`  
  (e.g. B2B, B2C, Enterprise, Internal)

- `customer_type`  
  (e.g. Hospitals, Insurance providers, Finance teams, Executives, Consumers)

- `regulatory_or_compliance_context`  
  (e.g. Healthcare, Financial, PII, None mentioned)

- `business_criticality`  
  (e.g. Low, Moderate, High, Revenue-impacting, Compliance-critical)

- `evidence`  
  A short quote or paraphrase from the interview showing why this classification is valid.

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
