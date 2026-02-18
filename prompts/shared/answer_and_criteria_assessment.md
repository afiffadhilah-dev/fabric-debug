Analyze the candidate’s interview answer in a single, comprehensive pass.

You are evaluating how well the answer addresses the interview question and the specified assessment criteria.

## Question Category
{category}

## Interview Question
{question}

## Assessment Criteria
Evaluate the answer based on the following criteria:
{criteria_list}

## Candidate Answer
{answer}

## Context
- Gap Being Addressed: {gap_description}
- Gap Category: {gap_category}

## Task: Assess Multiple Dimensions

### 1. ANSWER TYPE
Classify as ONE of:

**CHECK FOR CLARIFICATION FIRST** - this takes priority:

- **clarification_request**: User is asking for clarification or examples
  - **CRITICAL**: This is a HIGH engagement signal - user is trying to understand!
  - User doesn't understand the question and needs help
  - User wants examples or more context before answering
  - **Priority detection**: Check for these patterns FIRST before considering partial_answer:
    - "What do you mean?"
    - "What do you mean by that?"
    - "What do you mean by [term]?"
    - "Can you clarify?"
    - "Give me an example?"
    - "I don't get it, can you give me an example?"
    - "Can you rephrase that?"
    - "What kind of answer are you looking for?"
    - "I'm not sure what you're asking"
    - "What are you asking exactly?"
    - "Could you be more specific?"
  - **When this happens**: Provide clarification/examples and re-ask the question
  - **Engagement**: ALWAYS "engaged" (user is trying to understand)

Then check other types:

- **direct_answer**: Answer appropriately addresses the question
  - Short answers OK if question expects it (yes/no, numbers, facts)
  - Detailed answers for questions asking for examples/stories
  - Example: Q: "How many years?" A: "5 years" ✓ COMPLETE

- **partial_answer**: Relevant but incomplete OR minimal effort
  - Missing specific examples, outcomes, or details when expected
  - Vague when specifics were asked
  - Single letters or minimal text ("s", "n", "k", "idk", "dunno", "not sure")
  - Short dismissive answers when detail is expected
  - Example: Q: "Describe a situation" A: "Yes it happened" ✗ TOO BRIEF
  - Example: Q: "Tell me about Python" A: "s" ✗ MINIMAL EFFORT
  - Example: Q: "Your experience?" A: "idk" ✗ MINIMAL EFFORT

- **off_topic**: Completely unrelated to the question AND has some content
  - Discussing entirely different subjects
  - Example: Q: "Python experience?" A: "I like hiking" ✗ OFF TOPIC
  - Example: Q: "Database work?" A: "Let's talk about frontend instead" ✗ OFF TOPIC
  - **NOTE**: Single letters like "s" or "n" are NOT off-topic, they're partial_answer (minimal effort)

**IMPORTANT:** Don't judge by length alone! Consider what the question asks for.

**CRITICAL DISTINCTION:**
- "s" or "idk" = partial_answer + disengaged (minimal effort, not enough to be off-topic)
- "I prefer discussing React" = off_topic + engaged (changing subject, but engaged)
- "I like cats" (when asked about Python) = off_topic + disengaged (completely unrelated)

---

### 2. ENGAGEMENT LEVEL
Determine if candidate is **engaged** or **disengaged**.

**CRITICAL RULE**: If answer_type is "clarification_request", engagement level MUST be "engaged" (user is actively trying to understand).

**IMPORTANT**: Brief ≠ Disengaged! A concise answer that addresses the question IS engaged.

**ENGAGED** means candidate is trying to help, even if:
- Their answer is concise but relevant (addresses what was asked)
- They lack direct experience BUT offer alternatives
- They have constraints BUT explain them honestly
- They don't remember BUT offer approximations
- They redirect BUT stay on topic
- It's their first answer (people often warm up over time)

**Examples of ENGAGED answers:**
✓ "I'm a fullstack developer working on AI automation for CRM tools" (brief but on-topic!)
✓ "I don't have banking experience **BUT** I have 3 years mobile development"
✓ "Sorry, that's confidential, **but** I can describe the general approach we used"
✓ "I don't remember the exact number, **but** it was around 50 users"
✓ "I haven't worked with Docker specifically, **but** I've used similar containerization tools"
✓ "3 years of Python, mostly backend services" (concise but complete!)

**DISENGAGED** means candidate is REFUSING to engage or showing clear disinterest:
✗ "I don't have time for this" (refusing)
✗ "No" (single word with no elaboration when detail is expected)
✗ "I don't know" (with NO attempt to offer related info)
✗ "Can we skip this?" (avoidance)
✗ "idk" or "dunno" (minimal effort)
✗ "Whatever" or "I guess" (dismissive)

**KEY INSIGHT:**
- Look for transition words (BUT, HOWEVER, THOUGH) that signal engagement despite limitations!
- A short answer that ADDRESSES the question is still ENGAGED
- Only mark disengaged if there's clear avoidance, refusal, or minimal effort

---

### 3. DETAIL LEVEL
Score from 1-5:

- **1**: Bare minimum, almost no detail
- **2**: Some detail, but very surface level
- **3**: Adequate detail for understanding
- **4**: Good detail with specifics
- **5**: Rich with specifics, metrics, examples, context

**Consider:**
- Does answer match the detail level requested?
- Simple factual questions can score 5 with short answers
- Complex "describe/explain" questions need more detail for high scores

---

### 4. ENTHUSIASM
Detect if answer shows:
- Positive language and energy
- Willingness to elaborate
- Interest in the topic
- Excitement about experiences

**True** if present, **False** if neutral/negative.

---

### 5. CRITERIA ASSESSED: 
For EACH criterion listed above, determine:
   - **demonstrated**: Was this criterion clearly demonstrated in the answer? (true/false)
   - **evidence**: If demonstrated, quote or summarize the specific part of the answer that shows it

---

### 6. ANSWER QUALITY (1-5): 
Overall quality of the answer, BASED PRIMARILY ON HOW MANY CRITERIA ARE CLEARLY DEMONSTRATED AND HOW STRONGLY THEY ARE SUPPORTED.
   - 1: No criteria demonstrated
   - 2: Less than half criteria weakly or vaguely demonstrated
   - 3: At least more than half criteria list clearly demonstrated, others missing or vague
   - 4: Most criteria clearly demonstrated with concrete evidence
   - 5: All criteria clearly demonstrated with strong, specific evidence

---
## Output Format

Return ONLY valid JSON (no markdown, no explanation):

```json
{{
  "answer_type": "direct_answer" | "partial_answer" | "off_topic" | "clarification_request",
  "engagement_level": "engaged" | "disengaged",
  "detail_score": 1-5,
  "relevance_score": 0.0-1.0,
  "enthusiasm_detected": true | false,
  "answer_quality": 1-5,
  "criteria_assessed": [
    {{
      "criterion": "Criterion name here",
      "demonstrated": true | false,
      "evidence": "Brief evidence from the candidate's answer showing how this criterion was met"
    }}
  ],
  "reasoning": "Brief 1-sentence explanation of your assessment"
}}
```

## Scoring Rules
- If a criterion is marked **demonstrated: true**, it MUST positively impact the quality score.
- If most or all criteria are demonstrated, the quality score should NOT be below 4.
- Do NOT give a high quality score if criteria are missing, even if the answer is well-written.
- Be fair but strict. Prioritize factual, explicit evidence over general or abstract statements.

## Example outputs

Answer: "I don't have banking apps BUT I built 5 mobile apps with 10k+ users"
```json
{{
  "answer_type": "direct_answer",
  "engagement_level": "engaged",
  "detail_score": 4,
  "relevance_score": 0.8,
  "enthusiasm_detected": false,
  "answer_quality": 4,
  "criteria_assessed": [
    {{
      "criterion": "Relevant experience",
      "demonstrated": true,
      "evidence": "Built 5 mobile apps with 10k+ users"
    }},
    {{
      "criterion": "Honesty about limitations",
      "demonstrated": true,
      "evidence": "States lack of direct banking app experience"
    }}
  ],
  "reasoning": "Provides strong alternative experience with concrete metrics while being transparent about missing exact domain experience"
}}
```

Answer: "s" (single letter, minimal effort)
```json
{{
  "answer_type": "partial_answer",
  "engagement_level": "disengaged",
  "detail_score": 1,
  "relevance_score": 0.0,
  "enthusiasm_detected": false,
  "answer_quality": 1,
  "criteria_assessed": [
    {{
      "criterion": "Relevance to question",
      "demonstrated": false,
      "evidence": "No meaningful content provided"
    }},
    {{
      "criterion": "Effort and engagement",
      "demonstrated": false,
      "evidence": "Single-letter response indicates minimal effort"
    }}
  ],
  "reasoning": "Single-letter response shows no attempt to address the question or demonstrate any relevant criteria"
}}
```

Answer: "idk" or "I don't know"
```json
{{
  "answer_type": "partial_answer",
  "engagement_level": "disengaged",
  "detail_score": 1,
  "relevance_score": 0.1,
  "enthusiasm_detected": false,
  "answer_quality": 1,
  "criteria_assessed": [
    {{
      "criterion": "Relevance to question",
      "demonstrated": false,
      "evidence": "Does not provide any information related to the question"
    }},
    {{
      "criterion": "Attempt to offer alternatives",
      "demonstrated": false,
      "evidence": "No additional context or related experience offered"
    }}
  ],
  "reasoning": "Minimal response with no supporting details or attempt to provide relevant or alternative information"
}}
```

Answer: "What do you mean by scale?"
```json
{{
  "answer_type": "clarification_request",
  "engagement_level": "engaged",
  "detail_score": 1,
  "relevance_score": 0.0,
  "enthusiasm_detected": false,
  "answer_quality": 3,
  "criteria_assessed": [
    {{
      "criterion": "Understanding of question",
      "demonstrated": true,
      "evidence": "Asks for clarification on the meaning of 'scale'"
    }},
    {{
      "criterion": "Engagement and willingness to respond",
      "demonstrated": true,
      "evidence": "Requests more context before answering"
    }}
  ],
  "reasoning": "User requests clarification to better understand the question, indicating active engagement and intent to answer properly"
}}
```

Answer: "I like cats" (when asked about Python experience)
```json
{{
  "answer_type": "off_topic",
  "engagement_level": "disengaged",
  "detail_score": 1,
  "relevance_score": 0.0,
  "enthusiasm_detected": false,
  "answer_quality": 1,
  "criteria_assessed": [
    {{
      "criterion": "Relevance to question",
      "demonstrated": false,
      "evidence": "Discusses personal preference unrelated to Python experience"
    }},
    {{
      "criterion": "Engagement with topic",
      "demonstrated": false,
      "evidence": "Does not attempt to address the technical subject"
    }}
  ],
  "reasoning": "Completely unrelated response that does not engage with the technical question or assessment criteria"
}}
```
