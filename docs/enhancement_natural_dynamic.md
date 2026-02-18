Plan: Dynamic Conversation Handling in Conversational Agent

 Executive Summary

 Good News: The conversational agent already has sophisticated dynamic conversation handling
 implemented! The exploration revealed that 4 out of 4 core requirements are already in production.     

 However, there are 6 enhancement opportunities to make the system even more intelligent and
 user-friendly.

 ---
 Current Implementation Status

 ✅ FULLY IMPLEMENTED Core Requirements

 1. Natural Flow - Full Message History Access

 - State Field: messages: Annotated[List[BaseMessage], add_messages]
 - Location: agents/conversational/state.py:132
 - How it works:
   - LangChain's add_messages reducer automatically accumulates all messages
   - Full conversation history flows through every node
   - Extraction tools receive conversation_messages parameter for context
   - Enables co-reference resolution ("same like Python")

 Evidence:
 # tools/extraction_tools.py:203-209
 conversation_text = "\n## Previous Conversation\n\n"
 for msg in conversation_messages[:-1]:
     role = "Interviewer" if msg.type == "ai" else "Candidate"
     conversation_text += f"{role}: {msg.content}\n"

 2. Multi-Requirement Answer Handling

 - Function: extract_all_skills_from_answer()
 - Location: tools/extraction_tools.py:171-278
 - Capabilities:
   - Extracts multiple attributes from single answer ("3 years in production with 50K users")
   - Detects multiple skills in one answer ("Both Python and React for 2 years")
   - Co-reference resolution ("same as Python" → looks up Python in conversation)
   - Smart merging preserves existing info, only updates new attributes

 Gap Resolution Logic:
 # agents/conversational/nodes/update_state.py:340-377
 def check_gap_resolved(gap, new_attributes_added):
     # Checks if newly learned attributes satisfy the gap
     for attr_update in new_attributes_added:
         if attr_update["skill_name"] == skill_from_gap:
             if gap_asks_for_attribute in attr_update["attributes_added"]:
                 return True

 3. User Clarifications & Engagement

 - Detection: answer_type: "clarification_request"
 - Location: tools/answer_assessor.py:72-75
 - Special Routing:
   - should_follow_up() condition detects clarification requests
   - Generates immediate follow-up via generate_follow_up_node
   - Smart: Extracts information BEFORE responding to clarification
   - Resets engagement counter (treats as high engagement)

 Critical Feature - Handles partial answers with clarification:
 # parse_answer.py:88-91
 # "3 years. what types of tasks do you mean?"
 #   → Extracts "3 years" AND notes clarification request

 4. Memory & Persistence

 - Checkpointer: PostgresSaver (singleton)
 - Location: agents/conversational/checkpointer.py
 - How it works:
   - Uses thread_id from InterviewSession.thread_id
   - LangGraph automatically loads previous state on invoke
   - Merges new input with loaded state
   - Persists updated state after execution
 - Resume Support: continue_interview() loads state and merges new answer

 Configuration:
 # service.py:171-178
 config = {
     "configurable": {"thread_id": thread_id},
     "callbacks": [langfuse_handler],
     "metadata": {...}
 }
 result = self.graph.invoke(initial_state, config)

 ---
 Enhancement Opportunities (6 items)

 Enhancement 1: Multi-Gap Resolution Acknowledgment

 Status: ⚠️ Partial

 Current Behavior:
 - System silently resolves multiple gaps
 - Next question jumps to different gap without acknowledgment

 Example:
 User: "I led Python projects for 3 years with 100K users in production"
 → Resolves: Python duration + scale + production_vs_prototype
 System: "Can you describe your React experience?" ❌ No acknowledgment

 Proposed Enhancement:
 - Detect when multiple gaps resolved in one answer
 - Generate acknowledgment before next question
 - Example: "Great! You've covered Python duration, scale, AND production context. Now let's talk about 
  React..."

 Implementation:
 - Modify update_state_node to track count of resolved gaps
 - Add state field: gaps_resolved_this_turn: int
 - Modify generate_question_node to check if previous turn resolved multiple gaps
 - If yes, prefix question with acknowledgment

 Files to modify:
 - agents/conversational/state.py - Add gaps_resolved_this_turn
 - agents/conversational/nodes/update_state.py - Count resolved gaps
 - agents/conversational/nodes/generate_question.py - Add acknowledgment logic

 ---
 Enhancement 2: Dynamic Gap Re-ranking

 Status: ⚠️ Missing

 Current Behavior:
 - Gaps sorted by severity at initialization only
 - No re-prioritization based on conversation flow

 Problem:
 User: "I also have Docker experience!"
 System: *ignores* "Tell me about Python depth" ❌ Misses conversation momentum

 Proposed Enhancement:
 - Re-calculate gap severity after each answer
 - Boost severity for skills user volunteered information about
 - Add "conversation momentum" factor to severity

 Implementation Strategy:
 1. Add severity boost logic in update_state_node
 2. If user mentions skill unprompted → boost related gaps by +0.2
 3. Re-sort identified_gaps by updated severity
 4. select_gap_node picks from re-sorted list

 Files to modify:
 - agents/conversational/nodes/update_state.py - Add severity boost logic
 - agents/conversational/nodes/helpers.py - Add detection for unprompted skills

 ---
 Enhancement 3: Partial Answer Acknowledgment in Follow-ups

 Status: ⚠️ Edge case

 Current Behavior:
 - System extracts partial info before follow-up ✅
 - Follow-up might not acknowledge what was captured

 Example:
 Question: "How long did you work with Python and what types of projects?"
 User: "3 years. What do you mean by types?"
 System: "By types, I mean..." ❓ Doesn't confirm "3 years" was recorded

 Proposed Enhancement:
 - Modify generate_follow_up.py to include extracted info in context
 - Follow-up should acknowledge: "Got it - 3 years. Regarding project types..."

 Implementation:
 - Pass tool_results["skills"] to follow-up generator
 - Update prompts/conversational/follow_up_clarification.md to include acknowledgment template
 - Variable: {extracted_info} = summary of what was captured

 Files to modify:
 - agents/conversational/nodes/generate_follow_up.py - Pass extracted skills
 - prompts/conversational/follow_up_clarification.md - Add acknowledgment template

 ---
 Enhancement 4: Conversational Transitions

 Status: ⚠️ Missing

 Current Behavior:
 - System jumps from one skill to another without transition

 Example:
 User: "Python depth is expert level"
 System: "How long have you used React?" ❌ Abrupt topic switch

 Proposed Enhancement:
 - Detect when switching skills (Python → React)
 - Add brief transition message
 - Example: "Thanks for the Python details. Let's talk about React now..."

 Implementation:
 1. Add state field: previous_skill: Optional[str]
 2. In generate_question_node, compare current_gap["skill"] with previous_skill
 3. If different → add transition phrase to question
 4. Update previous_skill in state

 Files to modify:
 - agents/conversational/state.py - Add previous_skill field
 - agents/conversational/nodes/generate_question.py - Add transition detection
 - prompts/conversational/generate_question.md - Add transition templates

 ---
 Enhancement 5: Stable Question-Answer Linking

 Status: ⚠️ Missing

 Current Issue:
 - gap_id uses Python's id() (memory address, not persistent)
 - No stable question_id saved to answer metadata

 From update_state.py:251-254:
 "gap_id": str(id(current_gap)) if current_gap else None,  # ❌ Not stable!

 Proposed Enhancement:
 - Use current_question["question_id"] as stable identifier
 - Save full question context to message metadata
 - Enable queries like: "Show all questions about Python duration"

 Implementation:
 1. Replace id(current_gap) with current_question["question_id"]
 2. Add question_context to message metadata
 3. Add database query helpers in models/message.py

 Files to modify:
 - agents/conversational/nodes/update_state.py - Use stable question_id
 - models/message.py - Add query methods (get_questions_by_skill, get_clarification_questions)

 ---
 Enhancement 6: Intelligent Probe Limit Adjustment

 Status: ⚠️ Basic

 Current Behavior:
 - max_probes: 3 hardcoded
 - No differentiation between probe failure reasons

 Problem:
 - User trying but needs clarification (3 clarification_requests) → Limit reached, system gives up ❌   
 - User doesn't know topic (3 off_topic answers) → System keeps asking ❌

 Proposed Enhancement:
 - Track probe failure reasons
 - Adjust max_probes based on answer history:
   - All clarification requests → Increase to 5 (user is engaged!)
   - All off_topic → Decrease to 2 (user doesn't have info)

 Implementation:
 1. Add probe_history: List[str] to Gap structure
 2. In update_state_node, append answer_type to gap's probe_history
 3. In select_gap_node, adjust effective max_probes:
   - If last 3 probes are "clarification_request" → max_probes += 2
   - If last 2 probes are "off_topic" → max_probes = probes_attempted (stop now)

 Files to modify:
 - agents/conversational/state.py - Add probe_history to Gap TypedDict
 - agents/conversational/nodes/select_gap.py - Add intelligent limit logic

 ---
 Implementation Priority

 Phase 1: User Experience Improvements (High Impact, Low Risk)

 1. Enhancement 1: Multi-gap acknowledgment
 2. Enhancement 3: Partial answer acknowledgment
 3. Enhancement 4: Conversational transitions

 Estimated changes: 4-5 files, mostly prompt and generation logic

 Phase 2: Intelligence Improvements (Medium Impact, Medium Complexity)

 4. Enhancement 2: Dynamic gap re-ranking
 5. Enhancement 6: Intelligent probe limits

 Estimated changes: 3-4 files, requires new logic in update_state and select_gap

 Phase 3: Infrastructure (Low User Impact, Enables Analytics)

 6. Enhancement 5: Stable question-answer linking

 Estimated changes: 2 files, database queries and metadata structure

 ---
 Critical Files Reference

 Core Workflow

 - agents/conversational/graph.py - LangGraph workflow definition
 - agents/conversational/service.py - Application service layer
 - agents/conversational/state.py - State TypedDict definition

 Node Implementations

 - agents/conversational/nodes/identify_gaps.py - Resume analysis, gap identification
 - agents/conversational/nodes/select_gap.py - Gap selection logic
 - agents/conversational/nodes/generate_question.py - Question generation
 - agents/conversational/nodes/parse_answer.py - Answer extraction
 - agents/conversational/nodes/update_state.py - State updates, gap resolution
 - agents/conversational/nodes/generate_follow_up.py - Follow-up handling

 Supporting Logic

 - agents/conversational/conditions.py - Routing conditions
 - agents/conversational/nodes/helpers.py - Utility functions
 - tools/extraction_tools.py - Multi-skill extraction
 - tools/answer_assessor.py - Engagement detection

 Persistence

 - agents/conversational/checkpointer.py - PostgreSQL state persistence

 ---
 Verification Plan

 Test Existing Implementation

 1. Full History Test:
   - Start interview with resume
   - User says "Python: 3 years"
   - User says "Same duration for React"
   - Verify: Does system extract React duration = 3 years? (co-reference)
 2. Multi-Requirement Test:
   - Ask about Python duration
   - User says "5 years leading a team of 10 in production environment"
   - Verify: Extracts duration, autonomy, scale, production_vs_prototype?
 3. Clarification Test:
   - Ask about skill depth
   - User says "What do you mean by depth?"
   - Verify: System generates clarification follow-up?
 4. Persistence Test:
   - Start interview, answer 2 questions
   - Stop application, restart application
   - Continue interview with same thread_id
   - Verify: Full conversation history preserved?

 Test Enhancements (After Implementation)

 5. Multi-Gap Acknowledgment:
   - Answer covers 3 gaps at once
   - Verify: System acknowledges all 3 before next question?
 6. Dynamic Re-ranking:
   - User volunteers Docker info unprompted
   - Verify: Next question about Docker (not original high-priority gap)?
 7. Partial Answer Acknowledgment:
   - User says "3 years. What types of projects?"
   - Verify: Follow-up says "Got it - 3 years. Regarding types..."?
 8. Conversational Transitions:
   - Answer Python question
   - System switches to React
   - Verify: Transition message present?
 9. Stable Linking:
   - Query: "Show all questions about Python"
   - Verify: Returns correct messages with stable IDs?
 10. Intelligent Probes:
   - User gives 3 clarification requests for same gap
   - Verify: System continues asking (doesn't give up)?

 ---
 Execution Plan: Verify First, Then Implement Enhancements

 User Choice: Verify existing features first, then implement enhancements based on findings.

 Phase A: Verification Tests (4 Core Features)

 Create comprehensive integration test: tests/integration/test_dynamic_conversation.py

 This test will verify all 4 core requirements using real database and LLM calls.

 Test Structure:

 """
 Integration test for dynamic conversation handling features.

 Tests:
 1. Full conversation history with co-reference resolution
 2. Multi-requirement answer detection (multiple skills/attributes at once)
 3. User clarification request handling
 4. State persistence and resume capability
 """

 def test_full_conversation_history():
     """Test 1: Verify full message history flows through nodes."""
     # Start interview
     # Answer Q1: "Python: 3 years"
     # Answer Q2: "Same duration for React"
     # ✅ Verify: Does system extract React duration = 3 years? (co-reference)

 def test_multi_requirement_extraction():
     """Test 2: Verify multi-skill/multi-attribute extraction from single answer."""
     # Question: "Tell me about your Python experience"
     # Answer: "5 years leading a team of 10 in production environment with 100K users"
     # ✅ Verify: Extracts duration, autonomy, scale, production_vs_prototype?
     # ✅ Verify: Multiple gaps resolved from one answer?

 def test_clarification_request_handling():
     """Test 3: Verify clarification requests get special treatment."""
     # Question: "What depth of Python knowledge do you have?"
     # Answer: "What do you mean by depth?"
     # ✅ Verify: Next message is clarification follow-up
     # ✅ Verify: Engagement counter NOT penalized
     # ✅ Verify: answer_type == "clarification_request" in metadata

 def test_partial_answer_with_clarification():
     """Test 3B: Edge case - partial answer + clarification."""
     # Question: "How long and what types of projects?"
     # Answer: "3 years. What do you mean by types?"
     # ✅ Verify: System extracts "3 years"
     # ✅ Verify: System generates follow-up about "types"
     # ⚠️  Check: Does follow-up acknowledge "3 years" was captured?

 def test_state_persistence_and_resume():
     """Test 4: Verify checkpointer preserves full state."""
     # Start interview, answer 2 questions
     # Get thread_id and session_id
     # Simulate app restart: Create NEW service instance
     # Continue with same thread_id
     # ✅ Verify: Full conversation history preserved
     # ✅ Verify: extracted_skills preserved
     # ✅ Verify: identified_gaps and resolved_gaps preserved
     # ✅ Verify: completeness_score preserved

 Running Verification Tests:

 # Ensure database is running
 make db-start

 # Run dynamic conversation test
 python tests/integration/test_dynamic_conversation.py

 # Output will show:
 # - Test results for each feature
 # - ✅ PASS or ❌ FAIL for each verification point
 # - Detailed logs of LLM calls and state transitions

 Verification Success Criteria:

 Test 1 - Full History:
 - ✅ System extracts React duration = 3 years when user says "same duration for React"
 - ✅ Co-reference resolution working

 Test 2 - Multi-Requirement:
 - ✅ Single answer extracts 4+ attributes: duration, autonomy, scale, production_vs_prototype
 - ✅ Multiple gaps marked as resolved in one turn

 Test 3 - Clarification:
 - ✅ answer_type == "clarification_request" detected
 - ✅ Next message is follow-up (not new question)
 - ✅ consecutive_low_quality == 0 (engagement counter reset)

 Test 3B - Partial + Clarification:
 - ✅ "3 years" extracted before follow-up
 - ⚠️  POTENTIAL GAP: Follow-up may not acknowledge "3 years"
   - If follow-up doesn't acknowledge → Add to enhancement list (Enhancement 3)

 Test 4 - Persistence:
 - ✅ After restart, all state fields preserved:
   - messages - full conversation
   - extracted_skills - all skills with attributes
   - identified_gaps + resolved_gaps
   - completeness_score
   - questions_asked

 ---
 Phase B: Implement Enhancements Based on Verification

 After verification tests pass (or reveal specific issues), implement enhancements in priority order.   

 Priority Tier 1: User Experience (High Impact, Low Risk)

 Enhancement 1: Multi-Gap Resolution Acknowledgment
 - Trigger: If Test 2 shows no acknowledgment when multiple gaps resolved
 - Effort: ~1-2 hours
 - Files: 3 files (state.py, update_state.py, generate_question.py)

 Enhancement 3: Partial Answer Acknowledgment in Follow-ups
 - Trigger: If Test 3B shows follow-up doesn't acknowledge partial answer
 - Effort: ~1 hour
 - Files: 2 files (generate_follow_up.py, prompt template)

 Enhancement 4: Conversational Transitions
 - Trigger: After verification passes (always implement)
 - Effort: ~1-2 hours
 - Files: 3 files (state.py, generate_question.py, prompt template)

 Estimated Total: ~4-5 hours for all Tier 1 enhancements

 ---
 Priority Tier 2: Intelligence (Medium Impact, Medium Complexity)

 Enhancement 2: Dynamic Gap Re-ranking
 - Trigger: After Tier 1 complete
 - Effort: ~2-3 hours
 - Files: 3 files (update_state.py, helpers.py, Gap structure)

 Enhancement 6: Intelligent Probe Limits
 - Trigger: After Enhancement 2 complete
 - Effort: ~2 hours
 - Files: 3 files (state.py, update_state.py, select_gap.py)

 Estimated Total: ~4-5 hours for Tier 2 enhancements

 ---
 Priority Tier 3: Infrastructure (Low User Impact, Enables Analytics)

 Enhancement 5: Stable Question-Answer Linking
 - Trigger: After Tier 1 and 2 complete OR if analytics needed urgently
 - Effort: ~1 hour
 - Files: 2 files (update_state.py, message.py)

 Estimated Total: ~1 hour

 ---
 Phase C: Verification of Enhancements

 After implementing each enhancement, add corresponding test to test_dynamic_conversation.py:

 def test_multi_gap_acknowledgment():
     """Verify Enhancement 1: Multi-gap acknowledgment."""
     # Answer covers 3 gaps
     # ✅ Next question includes acknowledgment phrase

 def test_partial_answer_acknowledgment():
     """Verify Enhancement 3: Partial answer acknowledgment."""
     # Answer "3 years. What types?"
     # ✅ Follow-up starts with "Got it - 3 years..."

 def test_conversational_transitions():
     """Verify Enhancement 4: Skill switch transitions."""
     # Switch from Python to React
     # ✅ Question includes transition: "Thanks for Python details. Now React..."

 # ... etc for other enhancements

 ---
 Implementation Details for Each Enhancement

 Enhancement 1: Multi-Gap Resolution Acknowledgment

 Changes:

 1. state.py - Add field:
 gaps_resolved_this_turn: int = 0

 2. update_state.py - Track resolved count (in check_gap_resolved section):
 # After resolving gaps (line ~377)
 gaps_resolved_this_turn = len([g for g in identified_gaps if g in resolved_gaps_this_turn])
 return {
     ...
     "gaps_resolved_this_turn": gaps_resolved_this_turn
 }

 3. generate_question.py - Add acknowledgment:
 # Check if previous turn resolved multiple gaps
 if state.get("gaps_resolved_this_turn", 0) >= 2:
     # Add to system prompt context
     acknowledgment = f"User answered {gaps_resolved_this_turn} requirements in one response.
 Acknowledge this briefly before asking next question."

 4. prompts/conversational/generate_question.md - Add acknowledgment template:
 {acknowledgment_context}
 # If provided, start with brief acknowledgment like:
 # "Great! You've covered Python duration, scale, and production context. Now let's discuss..."

 ---
 Enhancement 3: Partial Answer Acknowledgment

 Changes:

 1. generate_follow_up.py - Pass extracted info (line ~69):
 if answer_type == "clarification_request":
     follow_up_type = "clarification"

     # NEW: Get extracted skills from tool_results
     extracted_info = tool_results.get("skills", [])
     extracted_summary = summarize_extracted_info(extracted_info)  # Helper function

     system_context = prompt_loader.load(
         "follow_up_clarification",
         mode="conversational",
         original_question=original_question,
         extracted_info=extracted_summary  # NEW
     )

 2. prompts/conversational/follow_up_clarification.md - Use variable:
 {extracted_info}
 # If user provided partial answer before asking for clarification, acknowledge it first:
 # Example: "Got it - 3 years. Regarding project types..."

 ---
 Enhancement 4: Conversational Transitions

 Changes:

 1. state.py - Add field:
 previous_skill: Optional[str] = None

 2. generate_question.py - Detect skill switch:
 current_skill = current_gap["context"].split(" - ")[0] if current_gap else None
 previous_skill = state.get("previous_skill")

 skill_switched = (current_skill != previous_skill) and previous_skill is not None

 # Pass to prompt
 transition_needed = skill_switched

 3. update_state.py or generate_question.py - Update previous_skill:
 return {
     ...
     "previous_skill": current_skill
 }

 4. prompts/conversational/generate_question.md - Add transition template:
 {transition_needed}
 # If true, add brief transition phrase:
 # - "Thanks for the {previous_skill} details. Let's talk about {current_skill} now..."
 # - "Great insights on {previous_skill}. Moving on to {current_skill}..."

 ---
 Enhancement 2: Dynamic Gap Re-ranking

 Changes:

 1. update_state.py - Boost unprompted skills (after skill extraction):
 # Detect unprompted skills
 current_skill_name = current_question["skill_name"] if current_question else None
 for skill in new_skills_extracted:
     if skill["name"] != current_skill_name:
         # User volunteered this skill!
         boost_gaps_for_skill(identified_gaps, skill["name"], boost_amount=0.2)

 def boost_gaps_for_skill(gaps, skill_name, boost_amount):
     for gap in gaps:
         if skill_name in gap["context"]:
             gap["severity"] = min(1.0, gap["severity"] + boost_amount)

     # Re-sort by severity
     gaps.sort(key=lambda g: g["severity"], reverse=True)

 2. helpers.py - Add helper function:
 def boost_gaps_for_skill(gaps: List[Gap], skill_name: str, boost_amount: float):
     """Boost severity for gaps related to a skill."""
     # Implementation above

 ---
 Enhancement 6: Intelligent Probe Limits

 Changes:

 1. state.py - Add probe history to Gap:
 class Gap(TypedDict):
     category: str
     description: str
     severity: float
     context: str
     probes_attempted: int
     max_probes: int
     probe_history: List[str]  # NEW: ["direct_answer", "clarification_request", ...]

 2. update_state.py - Append answer_type to probe_history:
 # After assessing answer
 if current_gap:
     current_gap["probe_history"].append(answer_type)

 3. select_gap.py - Intelligent limit adjustment:
 def calculate_effective_max_probes(gap: Gap) -> int:
     """Adjust max_probes based on probe history."""
     base_max = gap["max_probes"]
     history = gap.get("probe_history", [])

     if len(history) < 2:
         return base_max

     # If last 3 are clarification requests → User is engaged, give more chances
     if history[-3:] == ["clarification_request"] * 3:
         return base_max + 2

     # If last 2 are off_topic → User doesn't have info, stop now
     if history[-2:] == ["off_topic"] * 2:
         return gap["probes_attempted"]  # Stop immediately

     return base_max

 # Use in gap selection
 effective_max = calculate_effective_max_probes(gap)
 if gap["probes_attempted"] < effective_max:
     # Continue asking

 ---
 Enhancement 5: Stable Question-Answer Linking

 Changes:

 1. update_state.py - Use stable IDs (line ~251):
 # BEFORE:
 "gap_id": str(id(current_gap)) if current_gap else None,  # ❌ Unstable

 # AFTER:
 "gap_id": current_gap["context"] if current_gap else None,  # ✅ Stable (e.g., "Python - duration")    
 "question_id": current_question["question_id"] if current_question else None,  # ✅ From
 QuestionContext
 "question_context": current_question if current_question else None,  # ✅ Full context

 2. models/message.py - Add query helpers:
 @classmethod
 def get_questions_by_skill(cls, session: Session, session_id: str, skill_name: str):
     """Get all questions asked about a specific skill."""
     # Query messages where role='assistant' and meta.question_context.skill_name == skill_name

 @classmethod
 def get_clarification_questions(cls, session: Session, session_id: str):
     """Get all questions that were clarification requests."""
     # Query messages where meta.answer_type == 'clarification_request'

 ---
 File Reference Summary

 Files to Modify for Enhancements:

 Tier 1 (UX):
 - agents/conversational/state.py - Add gaps_resolved_this_turn, previous_skill
 - agents/conversational/nodes/update_state.py - Track gaps resolved, update previous_skill
 - agents/conversational/nodes/generate_question.py - Add acknowledgment + transition logic
 - agents/conversational/nodes/generate_follow_up.py - Pass extracted info
 - prompts/conversational/generate_question.md - Add templates
 - prompts/conversational/follow_up_clarification.md - Add acknowledgment template

 Tier 2 (Intelligence):
 - agents/conversational/state.py - Add probe_history to Gap
 - agents/conversational/nodes/update_state.py - Boost gaps, append probe history
 - agents/conversational/nodes/helpers.py - Add boost function
 - agents/conversational/nodes/select_gap.py - Intelligent limit calculation

 Tier 3 (Infrastructure):
 - agents/conversational/nodes/update_state.py - Use stable IDs
 - models/message.py - Add query methods

 Testing:
 - tests/integration/test_dynamic_conversation.py - New comprehensive test file

 ---
 Timeline Estimate

 Verification Phase

 - Write test file: ~2 hours
 - Run tests, debug issues: ~1-2 hours
 - Document findings: ~30 minutes
 - Total: ~3-4 hours

 Enhancement Phase

 - Tier 1 (UX): ~4-5 hours
 - Tier 2 (Intelligence): ~4-5 hours
 - Tier 3 (Infrastructure): ~1 hour
 - Testing enhancements: ~2 hours
 - Total: ~11-13 hours

 Grand Total: ~14-17 hours (spread over 2-3 days)