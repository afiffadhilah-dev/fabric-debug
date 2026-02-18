# Answer Assessment - Comprehensive Analysis

Analyze this interview answer comprehensively in one pass.

## Context
**Question asked:** {question}

**Gap being addressed:** {gap_description}

**Gap category:** {gap_category}

**User's answer:** {answer}

---

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

## Output Format

Return ONLY valid JSON (no markdown, no explanation):

```json
{{
  "answer_type": "direct_answer" | "partial_answer" | "off_topic" | "clarification_request",
  "engagement_level": "engaged" | "disengaged",
  "detail_score": 1-5,
  "relevance_score": 0.0-1.0,
  "enthusiasm_detected": true | false,
  "reasoning": "Brief 1-sentence explanation of your assessment"
}}
```

**Example outputs:**

Answer: "I don't have banking apps BUT I built 5 mobile apps with 10k+ users"
```json
{{
  "answer_type": "direct_answer",
  "engagement_level": "engaged",
  "detail_score": 4,
  "relevance_score": 0.8,
  "enthusiasm_detected": false,
  "reasoning": "Offers relevant alternative experience with good specifics despite lacking exact requirement"
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
  "reasoning": "Single letter answer shows minimal effort and no attempt to address the question"
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
  "reasoning": "Minimal effort, no attempt to provide related information or alternatives"
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
  "reasoning": "User is asking for clarification, showing high engagement and willingness to answer properly"
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
  "reasoning": "Answer is completely unrelated to technical question and shows no attempt to engage with topic"
}}
```
