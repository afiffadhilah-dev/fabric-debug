"""
Update state node - consolidates tool results into state updates.
"""

from typing import Dict, Any, List, Optional
from agents.conversational.state import InterviewState, Skill, EngagementSignal, Gap
from agents.conversational.conditions import get_gap_identifier
from sqlmodel import Session
from utils.database import get_engine
from repositories.message_repository import MessageRepository


def update_state_node(state: InterviewState) -> Dict[str, Any]:
    """
    Update state based on tool execution results.

    Consolidates:
    - New skills extracted from conversation
    - Engagement assessment
    - Gap resolution status
    - Completeness score recalculation

    Returns:
        Dictionary with updates:
        - extracted_skills: merged skill list
        - engagement_signals: appended engagement signal
        - resolved_gaps: updated list
        - completeness_score: recalculated score
        - consecutive_low_quality: updated counter
    """
    tool_results = state.get("tool_results", {})
    extracted_skills = list(state.get("extracted_skills", []))
    engagement_signals = list(state.get("engagement_signals", []))
    resolved_gaps = list(state.get("resolved_gaps", []))
    identified_gaps = list(state.get("identified_gaps", []))  # ✅ Initialize early
    current_gap = state.get("current_gap")
    consecutive_low_quality = state.get("consecutive_low_quality", 0)

    # Track if we added NEW information for gap resolution checking
    new_attributes_added = []

    # Process skill extraction results
    if "skills" in tool_results:
        new_skills = tool_results["skills"]

        # Filter out skills with no meaningful attributes
        def has_meaningful_data(skill):
            """Check if skill has at least one non-empty attribute"""
            for attr in ["duration", "depth", "autonomy", "scale", "constraints", "production_vs_prototype"]:
                value = skill.get(attr)
                # Check if value exists and is not a placeholder
                if value and value.lower() not in ["unknown", "not specified", "none", "n/a", "", "null"]:
                    return True
            return False

        # Only keep skills with actual information
        meaningful_skills = [s for s in new_skills if has_meaningful_data(s)]

        if len(new_skills) > len(meaningful_skills):
            filtered_count = len(new_skills) - len(meaningful_skills)
            print(f"  -> Filtered out {filtered_count} skill(s) with no meaningful data")

        new_skills = meaningful_skills

        for new_skill in new_skills:
            # Check if skill already exists
            existing_skill = None
            for i, skill in enumerate(extracted_skills):
                if skill["name"].lower() == new_skill["name"].lower():
                    existing_skill = i
                    break

            if existing_skill is not None:
                # BEFORE merging: snapshot existing attributes for this skill
                existing = extracted_skills[existing_skill]
                before_state = {
                    "skill_name": existing["name"],
                    "duration": existing.get("duration"),
                    "depth": existing.get("depth"),
                    "autonomy": existing.get("autonomy"),
                    "scale": existing.get("scale"),
                    "constraints": existing.get("constraints"),
                    "production_vs_prototype": existing.get("production_vs_prototype")
                }

                # Merge with existing skill - update unknown attributes
                attributes_changed = []
                for attr in ["duration", "depth", "autonomy", "scale", "constraints", "production_vs_prototype"]:
                    new_value = new_skill.get(attr)
                    old_value = existing.get(attr)

                    if new_value and new_value != "unknown":
                        # Check if this is ACTUALLY new information
                        if old_value is None or old_value == "unknown":
                            # This is NEW information!
                            attributes_changed.append(attr)

                        # Update the attribute
                        existing[attr] = new_value

                # Track what changed
                if attributes_changed:
                    new_attributes_added.append({
                        "skill_name": existing["name"],
                        "attributes_added": attributes_changed
                    })
                    print(f"  -> NEW INFO: {existing['name']} - added {', '.join(attributes_changed)}")

                # Append evidence
                if new_skill.get("evidence"):
                    existing["evidence"] += "\n" + new_skill["evidence"]

                # Update confidence (take higher)
                existing["confidence_score"] = max(
                    existing.get("confidence_score", 0),
                    new_skill.get("confidence_score", 0)
                )
            else:
                # Add new skill
                skill: Skill = {
                    "name": new_skill["name"],
                    "confidence_score": new_skill.get("confidence_score", 1.0),
                    "duration": new_skill.get("duration"),
                    "depth": new_skill.get("depth"),
                    "autonomy": new_skill.get("autonomy"),
                    "scale": new_skill.get("scale"),
                    "constraints": new_skill.get("constraints"),
                    "production_vs_prototype": new_skill.get("production_vs_prototype"),
                    "evidence": new_skill.get("evidence", "")
                }
                extracted_skills.append(skill)

                # Track new skill as new information
                filled_attrs = [attr for attr in ["duration", "depth", "autonomy", "scale", "constraints", "production_vs_prototype"]
                               if skill.get(attr) and skill.get(attr) != "unknown"]
                if filled_attrs:
                    new_attributes_added.append({
                        "skill_name": skill["name"],
                        "attributes_added": filled_attrs
                    })
                    print(f"  -> NEW SKILL: {skill['name']} with {', '.join(filled_attrs)}")

    # Process engagement assessment
    answer_text = state.get("answer_text") or ""  # Handle None case
    answer_type = "direct_answer"  # Default
    engagement_level = "engaged"  # Default
    engagement_data = {}  # For database persistence

    # Check for skip intent first (predefined mode only)
    # SINGLE SOURCE OF TRUTH: This is where skip state is updated in current_gap
    skip_detected = tool_results.get("skip_detected", False)
    skip_reason = tool_results.get("skip_reason", None)

    if skip_detected:
        # User explicitly skipped - DON'T count as low engagement
        # This is a valid user choice, not disengagement
        print(f"  🚫 SKIP DETECTED: {skip_reason}")
        print(f"  -> Skip is NOT counted as low engagement - maintaining counter at {consecutive_low_quality}")
        
        # Mark the gap as skipped in predefined mode (updates current_gap/identified_gaps)
        mode = state.get("mode", "dynamic_gap")
        if mode == "predefined_questions":
            current_gap = state.get("current_gap")
            if current_gap:
                current_gap["skipped"] = True
                current_gap["skip_reason"] = skip_reason
                print(f"  -> Marked current_gap as skipped: {current_gap.get('question_id')}")
                
                # IMPORTANT: Explicitly update identified_gaps to ensure state persistence
                # Find and update the matching gap in identified_gaps list
                for gap in identified_gaps:
                    if gap.get("question_id") == current_gap.get("question_id"):
                        gap["skipped"] = True
                        gap["skip_reason"] = skip_reason
                        print(f"  -> Updated identified_gaps: gap marked as skipped")
                        break
    
    elif "engagement" in tool_results:
        # Agent called engagement assessment tool
        engagement_data = tool_results["engagement"]
        answer_type = engagement_data.get("answer_type", "direct_answer")
        engagement_level = engagement_data.get("engagement_level", "engaged")

        # Create engagement signal
        signal: EngagementSignal = {
            "answer_length": engagement_data.get("answer_length", len(answer_text)),
            "relevance_score": engagement_data.get("relevance_score", 0.5),
            "detail_score": engagement_data.get("detail_score", 0.5),
            "enthusiasm_detected": engagement_data.get("enthusiasm_detected", False),
            "engagement_level": engagement_level
        }
        engagement_signals.append(signal)

        # CRITICAL LOGIC:
        # - Skip requests = User choice, NOT disengagement → Don't count (handled above)
        # - Clarification requests = HIGH engagement → Reset (user is actively participating)
        # - Off-topic = Not answering the question → Increment (pattern of avoidance)
        # - Disengaged direct/partial answer → Increment (showing fatigue/disinterest)
        # - Engaged direct/partial answer → Reset (good participation)

        if answer_type == "clarification_request":
            consecutive_low_quality = 0
            print(f"  -> User requested clarification - RESET engagement counter")
        elif answer_type == "off_topic":
            consecutive_low_quality += 1
            print(f"  -> Off-topic answer - INCREMENT counter to {consecutive_low_quality}")
        elif engagement_level == "disengaged":
            consecutive_low_quality += 1
            print(f"  -> Disengaged answer - INCREMENT counter to {consecutive_low_quality}")
        else:
            consecutive_low_quality = 0
            print(f"  -> Engaged answer - RESET engagement counter")

        # Track answer type in current gap's probe history (for intelligent probe limits)
        if current_gap:
            if "probe_history" not in current_gap:
                current_gap["probe_history"] = []
            current_gap["probe_history"].append(answer_type)
            print(f"  -> Probe history for current gap: {current_gap['probe_history']}")

    else:
        # Agent didn't call engagement tool - use minimal fallback for OBVIOUS disengagement
        # Only catch extreme cases to avoid false positives
        answer_lower = answer_text.lower().strip()

        # Very conservative list - only catch explicit refusals/disengagement
        obvious_disengagement = [
            "i cant", "i can't", "i cannot",
            "cant tell", "can't tell", "cannot tell",
            "no", "nope",
            "idk", "dunno",
            "dont know", "don't know"
        ]

        is_obviously_disengaged = answer_lower in obvious_disengagement

        if is_obviously_disengaged:
            consecutive_low_quality += 1
            engagement_level = "disengaged"
            answer_type = "partial_answer"
            print(f"  -> Fallback: Obvious disengagement pattern detected - INCREMENT counter to {consecutive_low_quality}")

            # Create minimal engagement signal
            signal: EngagementSignal = {
                "answer_length": len(answer_text),
                "relevance_score": 0.2,
                "detail_score": 0.1,
                "enthusiasm_detected": False,
                "engagement_level": "disengaged"
            }
            engagement_signals.append(signal)

            # Create minimal engagement_data for DB persistence
            engagement_data = {
                "answer_type": answer_type,
                "engagement_level": engagement_level,
                "detail_score": 1,
                "relevance_score": 0.2,
                "enthusiasm_detected": False,
                "reasoning": "Fallback heuristic: obvious disengagement phrase",
                "answer_length": len(answer_text)
            }
        else:
            # Agent decided engagement check wasn't needed - assume engaged
            consecutive_low_quality = 0
            engagement_level = "engaged"
            print(f"  -> No engagement check needed - assuming engaged, RESET counter")

    # =========================================================================
    # PERSIST ANSWER TO DATABASE
    # =========================================================================
    session_id = state.get("session_id")

    # Persist answer to DB using a properly scoped session
    try:
        # Build rich metadata for answer
        skills_extracted = [skill["name"] for skill in tool_results.get("skills", [])]

        meta = {
            "answer_type": answer_type,
            "engagement_level": engagement_level,
            "detail_score": engagement_data.get("detail_score", 0),
            "relevance_score": engagement_data.get("relevance_score", 0.5),
            "enthusiasm_detected": engagement_data.get("enthusiasm_detected", False),
            "reasoning": engagement_data.get("reasoning", ""),
            "answer_length": engagement_data.get("answer_length", len(answer_text)),
            "gap_id": str(id(current_gap)) if current_gap else None,
            "skills_extracted": skills_extracted,
            "gap_resolved": False  # Will be updated after gap check
        }

        # Add criteria assessment for predefined mode
        criteria_data = tool_results.get("criteria")
        if criteria_data:
            meta["criteria_assessment"] = {
                "answer_quality": criteria_data.get("answer_quality"),
                "criteria_assessed": criteria_data.get("criteria_assessed", []),
                "reasoning": criteria_data.get("reasoning", "")
            }

        # Use a properly scoped session — all DB ops INSIDE the with block
        engine = get_engine()
        with Session(engine) as db_session:
            local_repo = MessageRepository(db_session)
            local_repo.create(
                session_id=session_id,
                role="user",
                content=answer_text,
                meta=meta
            )

        print(f"  -> Persisted answer to database (session_id={session_id})")

    except Exception as e:
        print(f"  -> WARNING: Failed to persist answer to database: {e}")
        # Continue anyway - don't fail the interview if DB is down

    # Check gaps for resolution - MODE-AWARE LOGIC
    mode = state.get("mode", "dynamic_gap")

    # DYNAMIC GAP RE-RANKING: Boost gaps for skills user volunteered unprompted
    if mode == "dynamic_gap":
        current_question = state.get("current_question")
        asked_skill_name = current_question.get("skill_name") if current_question else None

        # Find skills mentioned that are NOT the skill we asked about
        unprompted_skills = []
        for skill_info in new_attributes_added:
            skill_name = skill_info["skill_name"]
            if asked_skill_name and skill_name.lower() != asked_skill_name.lower():
                unprompted_skills.append(skill_name)

        if unprompted_skills:
            print(f"\n🎯 DYNAMIC RE-RANKING: User volunteered unprompted skills: {', '.join(unprompted_skills)}")

            # Boost severity for gaps related to unprompted skills
            identified_gaps_list = list(state.get("identified_gaps", []))
            boosted_count = 0

            for gap in identified_gaps_list:
                gap_context = gap.get("context", "").lower()
                gap_desc = gap.get("description", "").lower()

                for unprompted_skill in unprompted_skills:
                    if unprompted_skill.lower() in gap_context or unprompted_skill.lower() in gap_desc:
                        # Boost severity by 0.2 (capped at 1.0)
                        old_severity = gap.get("severity", 0.5)
                        gap["severity"] = min(1.0, old_severity + 0.2)
                        print(f"   Boosted '{unprompted_skill}' gap severity: {old_severity:.2f} → {gap['severity']:.2f}")
                        boosted_count += 1
                        break  # Only boost once per gap

            if boosted_count > 0:
                # Re-sort gaps by severity (highest first)
                identified_gaps_list.sort(key=lambda g: g.get("severity", 0.0), reverse=True)
                identified_gaps = identified_gaps_list
                print(f"   Re-sorted gaps: {boosted_count} gap(s) boosted, highest severity now: {identified_gaps[0].get('severity', 0):.2f}")
            else:
                identified_gaps = identified_gaps_list
        else:
            identified_gaps = state.get("identified_gaps", [])
    else:
        identified_gaps = state.get("identified_gaps", [])

    if mode == "predefined_questions":
        # PREDEFINED MODE: Resolve current gap with relaxed criteria
        # Use criteria assessment if available, fall back to engagement
        if current_gap:
            current_gap_id = get_gap_identifier(current_gap)
            already_resolved = any(get_gap_identifier(g) == current_gap_id for g in resolved_gaps)

            if not already_resolved:
                # Get criteria assessment (from parse_answer) or engagement data
                criteria_data = tool_results.get("criteria", {})
                answer_quality = criteria_data.get("answer_quality", 0)
                probes_attempted = current_gap.get("probes_attempted", 0)
                max_probes = current_gap.get("max_probes", 2)

                # Fall back to engagement if no criteria assessment
                if not answer_quality:
                    logger.warning("answer_quality missing, answer_quality set to 0")
                    answer_quality = 0

                # Check if this gap was pre-filled (interview_filled) with low confidence
                # If so, combine the evidence and update confidence
                was_interview_filled = current_gap.get("interview_filled", False)
                original_confidence = current_gap.get("coverage_confidence", 0.0)

                if was_interview_filled and answer_quality >= 2:
                    # Combine evidence from cross-gap detection + direct answer
                    from tools.evidence_combiner import evaluate_combined_evidence

                    original_evidence = current_gap.get("interview_evidence", "")
                    answer_text = state.get("answer_text", "")
                    criteria = current_gap.get("what_assesses", [])

                    combined_result = evaluate_combined_evidence(
                        original_evidence=original_evidence,
                        new_evidence=answer_text,
                        criteria=criteria,
                        original_confidence=original_confidence
                    )

                    # Update gap with combined evidence
                    current_gap["coverage_confidence"] = combined_result["combined_confidence"]
                    current_gap["interview_evidence"] = combined_result["combined_evidence"]

                    print(f"  -> 🔄 Evidence combined: redundant={combined_result['is_redundant']}, "
                          f"confidence={original_confidence:.2f} → {combined_result['combined_confidence']:.2f}")

                    if combined_result.get("new_information_added"):
                        print(f"     New info: {', '.join(combined_result['new_information_added'][:3])}")

                # Relaxed resolution logic:
                # 1. Good answer (quality >= 3) -> resolve
                # 2. Decent answer after 2 tries (quality >= 2 and probes >= 2) -> resolve
                # 3. Max probes reached -> resolve anyway (move on)
                should_resolve = (
                    answer_quality >= 3 or
                    (probes_attempted >= 2 and answer_quality >= 2) or
                    probes_attempted >= max_probes
                )

                if should_resolve:
                    resolved_gaps.append(current_gap)
                    reason = "good answer" if answer_quality >= 3 else (
                        "decent after probes" if answer_quality >= 2 else "max probes reached"
                    )
                    print(f"  -> ✅ Gap resolved: {current_gap_id} ({reason}, quality={answer_quality})")
                else:
                    print(f"  -> ⏳ Current gap still open: {current_gap_id} (quality={answer_quality}, probes={probes_attempted}/{max_probes})")
            else:
                print(f"  -> ✅ Gap already resolved: {current_gap_id}")

        # CROSS-GAP COVERAGE: Mark other gaps as interview_filled if this answer covered them
        cross_coverage = tool_results.get("cross_coverage", [])
        all_predefined_gaps = list(state.get("all_predefined_gaps", []))

        if cross_coverage:
            cross_filled_count = 0
            for coverage in cross_coverage:
                if coverage.get("covered") and coverage.get("confidence", 0) >= 0.7:
                    gap_id = coverage.get("question_id")

                    # Update in identified_gaps
                    for gap in identified_gaps:
                        if gap.get("question_id") == gap_id:
                            gap["interview_filled"] = True
                            gap["interview_evidence"] = coverage.get("evidence", "")
                            gap["coverage_confidence"] = coverage.get("confidence", 0.0)
                            break

                    # Also update in all_predefined_gaps (for completeness calculation)
                    for gap in all_predefined_gaps:
                        if gap.get("question_id") == gap_id:
                            gap["interview_filled"] = True
                            gap["interview_evidence"] = coverage.get("evidence", "")
                            gap["coverage_confidence"] = coverage.get("confidence", 0.0)
                            cross_filled_count += 1
                            print(f"  -> 📝 Cross-gap filled: {coverage.get('category')} "
                                  f"(confidence={coverage.get('confidence', 0):.2f})")
                            break

            if cross_filled_count > 0:
                print(f"  -> 🎯 {cross_filled_count} additional gaps covered by this answer!")
    else:
        # DYNAMIC GAP MODE: Check all gaps based on attributes added
        newly_resolved = []
        for gap in identified_gaps:
            # Skip already resolved gaps
            gap_id = get_gap_identifier(gap)
            if any(get_gap_identifier(g) == gap_id for g in resolved_gaps):
                continue

            # Check if this gap is now resolved
            if check_gap_resolved(gap, new_attributes_added):
                resolved_gaps.append(gap)
                newly_resolved.append(gap_id)
                print(f"  -> ✅ Gap resolved: {gap_id}")

        # Check current gap specifically
        if current_gap:
            current_gap_id = get_gap_identifier(current_gap)
            current_gap_resolved = any(get_gap_identifier(g) == current_gap_id for g in resolved_gaps)
            if not current_gap_resolved:
                print(f"  -> ⏳ Current gap still open: {current_gap_id}")

    # Count gaps resolved this turn (for multi-gap acknowledgment)
    gaps_resolved_this_turn = len(newly_resolved) if mode == "dynamic_gap" else 0

    # Recalculate completeness score (MODE-AWARE)
    all_predefined_gaps_updated = []  # Will be set in predefined mode

    if mode == "predefined_questions":
        # Predefined mode: Calculate based on resolved questions
        # Get all_predefined_gaps - may have been updated in cross-gap section
        try:
            # If cross-gap section ran, all_predefined_gaps is already updated
            all_predefined_gaps_updated = all_predefined_gaps
        except NameError:
            # No cross-gap section ran, get from state
            all_predefined_gaps_updated = list(state.get("all_predefined_gaps", []))

        completeness_score = calculate_completeness_predefined(all_predefined_gaps_updated, resolved_gaps)
        interview_filled_count = sum(1 for g in all_predefined_gaps_updated if g.get("interview_filled", False))
        print(f"State update: {len(resolved_gaps)}/{len(all_predefined_gaps_updated)} questions resolved, "
              f"{interview_filled_count} cross-filled, completeness: {completeness_score:.2%}")
    else:
        all_predefined_gaps = []  # Not used in dynamic mode
        # Dynamic gap mode: Calculate based on skill attributes
        completeness_score = calculate_completeness(extracted_skills)
        print(f"State update: {len(extracted_skills)} skills, {len(resolved_gaps)} resolved gaps, completeness: {completeness_score:.2%}")

        # Log multi-gap resolution
        if gaps_resolved_this_turn >= 2:
            print(f"🎯 Multi-gap resolution: {gaps_resolved_this_turn} gaps resolved in single answer!")

    print(f"Consecutive low quality: {consecutive_low_quality}")

    result = {
        "extracted_skills": extracted_skills,
        "engagement_signals": engagement_signals,
        "resolved_gaps": resolved_gaps,
        "identified_gaps": identified_gaps,  # Return re-sorted gaps
        "completeness_score": completeness_score,
        "consecutive_low_quality": consecutive_low_quality,
        "gaps_resolved_this_turn": gaps_resolved_this_turn
    }

    # For predefined mode, also return updated all_predefined_gaps
    if mode == "predefined_questions" and all_predefined_gaps_updated:
        result["all_predefined_gaps"] = all_predefined_gaps_updated

    return result


def check_gap_resolved(gap: Gap, new_attributes_added: List[Dict[str, Any]]) -> bool:
    """
    Check if a gap has been resolved based on NEW information added this turn.

    A gap is resolved if we learned meaningful new attributes for the skill this gap is tracking.

    Args:
        gap: The gap being checked
        new_attributes_added: List of dicts with format:
            [{"skill_name": "Python", "attributes_added": ["duration", "scale"]}, ...]

    Returns:
        True if we added at least one new attribute for this gap's skill
    """
    if not new_attributes_added:
        # No new information added this turn
        return False

    # Extract skill name from gap context or description
    gap_context = gap.get("context", "")
    gap_description = gap.get("description", "")

    # Find if any new attributes were added for the skill this gap is tracking
    for item in new_attributes_added:
        skill_name = item["skill_name"]

        # Check if this skill is mentioned in the gap
        if skill_name.lower() in gap_context.lower() or skill_name.lower() in gap_description.lower():
            attributes_added = item["attributes_added"]

            if len(attributes_added) >= 1:
                # We added at least one new attribute for this skill
                # Gap is resolved!
                print(f"     Resolved because we learned: {', '.join(attributes_added)}")
                return True

    # No new information for this gap's skill
    return False


def calculate_completeness(skills: List[Skill]) -> float:
    """
    Calculate completeness score based on skill attribute coverage (for dynamic_gap mode).

    Completeness = (total known attributes) / (total possible attributes)
    """
    if not skills:
        return 0.0

    total_attributes = len(skills) * 6
    known_count = 0

    for skill in skills:
        attrs = [
            skill.get("duration"),
            skill.get("depth"),
            skill.get("autonomy"),
            skill.get("scale"),
            skill.get("constraints"),
            skill.get("production_vs_prototype")
        ]

        for attr in attrs:
            if attr and attr != "unknown":
                known_count += 1

    return known_count / total_attributes if total_attributes > 0 else 0.0


def calculate_completeness_predefined(
    all_predefined_gaps: List[Any],
    resolved_gaps: List[Any]
) -> float:
    """
    Calculate completeness score for predefined_questions mode.

    Completeness = (resume_filled + interview_filled + resolved_in_interview) / (total_questions - skipped)

    A gap can be "completed" in three ways:
    1. resume_filled: Resume already answered the question
    2. interview_filled: A previous answer covered this question (cross-gap detection)
    3. Resolved: Directly answered through Q&A

    IMPORTANT: Skipped questions are EXCLUDED from scoring!
    - They don't count as "completed" (user chose not to answer)
    - They don't count in total_questions denominator (reduces total expected)
    - This prevents completeness score from being penalized for user skips

    Args:
        all_predefined_gaps: All predefined questions (includes resume_filled, interview_filled, skipped flags)
        resolved_gaps: Gaps that were resolved during the interview via direct Q&A

    Returns:
        Completeness score (0.0-1.0) - only considers non-skipped gaps
    """
    if not all_predefined_gaps:
        return 0.0

    # FILTER OUT SKIPPED GAPS - they don't count towards scoring
    active_gaps = [g for g in all_predefined_gaps if not g.get("skipped", False)]
    
    if not active_gaps:
        # All gaps were skipped - return 0 or special case?
        print("  ⚠️  All gaps were skipped - completeness score set to 0.0")
        return 0.0

    total_questions = len(active_gaps)

    # Count resume-filled questions
    resume_filled_count = sum(1 for g in active_gaps if g.get("resume_filled", False))

    # Count interview-resolved questions (direct Q&A)
    resolved_identifiers = {get_gap_identifier(gap) for gap in resolved_gaps}
    interview_resolved_count = len(resolved_identifiers)

    # Count interview-filled questions (cross-gap detection)
    # IMPORTANT: Exclude gaps that are also in resolved_gaps to avoid double-counting
    # A gap can be interview_filled AND later resolved via direct Q&A
    interview_filled_count = sum(
        1 for g in active_gaps
        if g.get("interview_filled", False)
        and get_gap_identifier(g) not in resolved_identifiers  # Don't double-count!
    )

    # Total completed = resume_filled + interview_filled (not resolved) + interview_resolved
    completed_count = resume_filled_count + interview_filled_count + interview_resolved_count

    completeness = completed_count / total_questions if total_questions > 0 else 0.0

    return completeness
