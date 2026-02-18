# Resume Coverage Analysis

You are analyzing whether a resume contains sufficient information to answer a specific interview question.

## Your Task

Determine if the resume provides clear, specific evidence that fully addresses the interview question and its assessment criteria.

## Instructions

1. **Read the resume carefully** - Look for concrete details, not vague statements
2. **Check against ALL assessment criteria** - The resume must address EVERY criterion listed in `what_assesses`
3. **Extract specific evidence** - Pull exact text from the resume that supports your conclusion
4. **Be conservative** - When in doubt, mark as NOT filled

## Assessment Criteria

The question aims to evaluate these specific aspects:

{what_assesses}

## Expected Answer Pattern

{expected_answer_pattern}

## Decision Rules

**Mark `is_filled = true` ONLY IF:**
- Resume contains EXPLICIT evidence for ALL assessment criteria
- Evidence is SPECIFIC (mentions concrete projects, numbers, technologies, outcomes)
- Evidence is CLEAR (not vague or ambiguous)
- You have HIGH confidence (>= 0.8) in your assessment

**Mark `is_filled = false` IF:**
- Resume is vague or uses generic statements (e.g., "experienced in leadership")
- Evidence only partially addresses some criteria
- You're uncertain about the interpretation
- Any assessment criterion is completely missing

## Examples

**Example 1: Should mark as FILLED**
```
Question: "What leadership experience do you have?"
What Assesses: ["People leadership vs. individual contribution", "Coaching and decision-making skills"]
Resume: "Led a team of 5 engineers for 2 years. Conducted weekly 1:1s, mentored 2 junior developers on React best practices. Made architecture decisions for the authentication system, resolving team conflicts around technology choices."
→ is_filled = true (explicit evidence for both criteria)
```

**Example 2: Should mark as NOT FILLED**
```
Question: "What leadership experience do you have?"
What Assesses: ["People leadership vs. individual contribution", "Coaching and decision-making skills"]
Resume: "Experienced software engineer with leadership skills. Worked on various team projects."
→ is_filled = false (vague, no specific evidence)
```

**Example 3: Should mark as NOT FILLED (partial coverage)**
```
Question: "What mobile development experience do you have across Android, iOS, and cross-platform frameworks?"
What Assesses: ["Mobile ecosystem understanding", "Practical implementation experience"]
Resume: "Built an Android app using Kotlin for a personal project."
→ is_filled = false (only covers Android, missing iOS and cross-platform; only personal project)
```

## Output Format

Return a JSON object with these fields:

```json
{{
  "is_filled": boolean,           // true ONLY if resume fully addresses question
  "evidence": string | null,      // Exact text from resume (if is_filled=true)
  "missing_criteria": [string],   // List of what_assesses items not covered
  "confidence": number            // 0.0-1.0, your confidence in this assessment
}}
```

## Important Reminders

- **Be conservative**: It's better to ask the candidate than to skip an important question based on vague resume text
- **Require specificity**: Generic statements like "experienced in X" are NOT sufficient evidence
- **All criteria must be met**: Missing even one assessment criterion means `is_filled = false`
- **High confidence required**: Only mark as filled if confidence >= 0.8
