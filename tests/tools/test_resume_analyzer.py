"""
Quick test for resume analyzer tool.
"""

from tools.resume_analyzer import analyze_resume_for_question

# Test case 1: Resume WITH sufficient evidence
comprehensive_resume = """
John Doe - Senior Software Engineer

EXPERIENCE:
Tech Company Inc. (2021-Present)
- Led a team of 5 engineers, conducting weekly 1:1s and mentoring 2 junior developers
- Made architecture decisions for the authentication system using OAuth 2.0
- Resolved team conflicts around technology choices through collaborative workshops
- Managed sprint planning and deliverables for a team handling 10M DAU

LEADERSHIP HIGHLIGHTS:
- Promoted from Senior Engineer to Tech Lead in 2022
- Coached team members on React best practices and code review standards
- Owned hiring decisions for 3 new team members
"""

# Test case 2: Resume WITHOUT sufficient evidence (vague)
vague_resume = """
Jane Smith - Software Engineer

EXPERIENCE:
Software Company (2020-Present)
- Experienced in team collaboration
- Worked on various projects
- Good communication skills
"""

# Test question
question = "What leadership experience do you have, and how have you led or mentored others?"
what_assesses = [
    "People leadership vs. individual contribution",
    "Coaching and decision-making skills"
]
expected_pattern = "A strong candidate describes mentoring, code/design reviews, how many people they led, decision ownership, conflict resolution, and enabling team performance rather than just holding a title."

print("=" * 80)
print("TEST 1: Comprehensive Resume (should be FILLED)")
print("=" * 80)
result1 = analyze_resume_for_question(
    resume=comprehensive_resume,
    question=question,
    what_assesses=what_assesses,
    expected_pattern=expected_pattern
)

print(f"Is Filled: {result1['is_filled']}")
print(f"Confidence: {result1['confidence']}")
print(f"Missing Criteria: {result1['missing_criteria']}")
if result1.get('evidence'):
    print(f"Evidence: {result1['evidence'][:200]}...")
print()

print("=" * 80)
print("TEST 2: Vague Resume (should NOT be FILLED)")
print("=" * 80)
result2 = analyze_resume_for_question(
    resume=vague_resume,
    question=question,
    what_assesses=what_assesses,
    expected_pattern=expected_pattern
)

print(f"Is Filled: {result2['is_filled']}")
print(f"Confidence: {result2['confidence']}")
print(f"Missing Criteria: {result2['missing_criteria']}")
print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✓ Test 1 passed: {result1['is_filled'] == True}")
print(f"✓ Test 2 passed: {result2['is_filled'] == False}")
print()
