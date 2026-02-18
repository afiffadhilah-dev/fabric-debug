"""
Comprehensive answer assessment tool.

Evaluates multiple dimensions of user answers:
- Answer type (direct, partial, off-topic)
- Engagement level
- Detail score
- Relevance score
- Enthusiasm
"""

from typing import Dict, Any, List
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader


class AnswerAssessor:
    """
    Comprehensively assesses user answers across multiple dimensions.

    Uses LLM to determine:
    - Answer type: direct_answer, partial_answer, or off_topic
    - Engagement level: engaged or disengaged
    - Detail score: 1-5 rating
    - Relevance score: 0.0-1.0
    - Enthusiasm: true/false
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_loader = PromptLoader()

    def assess_answer(
        self,
        question: str,
        answer: str,
        gap: Dict[str, Any],
        what_assesses: List[str],
        category: str = "General",
        mode: str = "predefined_questions"
    ) -> Dict[str, Any]:
        """
        Comprehensively assess a user's answer.

        Args:
            question: The question that was asked
            answer: The user's answer
            gap: The gap this question was addressing (for context)

        Returns:
            Dictionary with structure:
            {
                "answer_type": "direct_answer" | "partial_answer" | "off_topic",
                "engagement_level": "engaged" | "disengaged",
                "detail_score": 1-5,
                "relevance_score": 0.0-1.0,
                "enthusiasm_detected": true | false,
                "reasoning": "Explanation of assessment"
            }
        """
        if mode == "predefined_questions":
            criteria_list = "\n".join([f"- {c}" for c in what_assesses])
            human_prompt = self.prompt_loader.load(
                "answer_and_criteria_assessment",
                mode="shared",
                question=question,
                answer=answer,
                gap_description=gap.get('description', 'Additional skill information'),
                gap_category=gap.get('category', 'technical_skill'),
                category=category,
                criteria_list=criteria_list
            )
            schema = {
                "type": "object",
                "properties": {
                    "answer_type": {
                        "type": "string",
                        "enum": ["direct_answer", "partial_answer", "off_topic", "clarification_request"]
                    },
                    "engagement_level": {
                        "type": "string",
                        "enum": ["engaged", "disengaged"]
                    },
                    "detail_score": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5
                    },
                    "relevance_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "enthusiasm_detected": {
                        "type": "boolean"
                    },
                    "answer_quality": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5
                    },
                    "criteria_assessed": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "criterion": {"type": "string"},
                                "demonstrated": {"type": "boolean"},
                                "evidence": {"type": "string"}
                            },
                            "required": ["criterion", "demonstrated", "evidence"]
                        }
                    },
                    "reasoning": {
                        "type": "string"
                    }
                },
                "required": [
                    "answer_type",
                    "engagement_level",
                    "detail_score",
                    "relevance_score",
                    "enthusiasm_detected",
                    "answer_quality",
                    "criteria_assessed",
                    "reasoning"
                ]
            }
        else:
            # Load and format prompt with variables
            human_prompt = self.prompt_loader.load(
                "answer_assessment",
                mode="shared",
                question=question,
                answer=answer,
                gap_description=gap.get('description', 'Additional skill information'),
                gap_category=gap.get('category', 'technical_skill')
            )

            # Define JSON schema
            schema = {
                "type": "object",
                "properties": {
                    "answer_type": {
                        "type": "string",
                        "enum": ["direct_answer", "partial_answer", "off_topic", "clarification_request"]
                    },
                    "engagement_level": {
                        "type": "string",
                        "enum": ["engaged", "disengaged"]
                    },
                    "detail_score": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5
                    },
                    "relevance_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "enthusiasm_detected": {
                        "type": "boolean"
                    },
                    "reasoning": {
                        "type": "string"
                    }
                },
                "required": [
                    "answer_type", "engagement_level", "detail_score",
                    "relevance_score", "enthusiasm_detected", "reasoning"
                ]
            }

        try:
            response = self.llm_service.generate_json(
                system_prompt="",  # Already included in human_prompt
                human_prompt=human_prompt,
                schema=schema
            )

            if response is None:
                # Fallback to basic heuristic if LLM fails
                print("  -> WARNING: LLM returned None - using basic heuristic for answer assessment")
                return self._basic_assessment_heuristic(answer)
            
            
            criteria = response.get("criteria_assessed", [])
            demonstrated = sum(1 for c in criteria if c.get("demonstrated"))

            if mode == "predefined_questions":
                # Debug output: show criteria assessment details
                print(f"  -> Criteria Assessment LLM Response:")
                print(f"     answer_quality: {response.get('answer_quality')}")
                print(f"     criteria_assessed: {demonstrated}/{len(criteria)} demonstrated")
                print(f"     reasoning: {response.get('reasoning', '')[:100]}...")

            # Debug: Show answer assessment details
            print(f"  -> Answer Assessment LLM Response:")
            print(f"     answer_type: {response.get('answer_type')}")
            print(f"     engagement_level: {response.get('engagement_level')}")
            print(f"     detail_score: {response.get('detail_score')}")
            print(f"     reasoning: {response.get('reasoning')}")

            # Add computed fields for backward compatibility
            response["answer_length"] = len(answer)

            return response
        except Exception as e:
            print(f"Error assessing answer with LLM: {e}")
            return self._basic_assessment_heuristic(answer)

    async def assess_answer_async(
        self,
        question: str,
        answer: str,
        gap: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ASYNC version of assess_answer for parallel execution."""
        # Load and format prompt with variables
        human_prompt = self.prompt_loader.load(
            "answer_assessment",
            mode="shared",
            question=question,
            answer=answer,
            gap_description=gap.get('description', 'Additional skill information'),
            gap_category=gap.get('category', 'technical_skill')
        )

        # Define JSON schema (same as sync)
        schema = {
            "type": "object",
            "properties": {
                "answer_type": {
                    "type": "string",
                    "enum": ["direct_answer", "partial_answer", "off_topic", "clarification_request"]
                },
                "engagement_level": {
                    "type": "string",
                    "enum": ["engaged", "disengaged"]
                },
                "detail_score": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5
                },
                "relevance_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "enthusiasm_detected": {
                    "type": "boolean"
                },
                "reasoning": {
                    "type": "string"
                }
            },
            "required": [
                "answer_type", "engagement_level", "detail_score",
                "relevance_score", "enthusiasm_detected", "reasoning"
            ]
        }

        try:
            response = await self.llm_service.generate_json_async(
                system_prompt="",  # Already included in human_prompt
                human_prompt=human_prompt,
                schema=schema
            )

            if response is None:
                print("  -> WARNING: LLM returned None - using basic heuristic (async)")
                return self._basic_assessment_heuristic(answer)

            # Debug: Show what LLM returned
            print(f"  -> Answer Assessment LLM Response:")
            print(f"     answer_type: {response.get('answer_type')}")
            print(f"     engagement_level: {response.get('engagement_level')}")
            print(f"     detail_score: {response.get('detail_score')}")
            print(f"     reasoning: {response.get('reasoning')}")

            # Add computed fields
            response["answer_length"] = len(answer)

            return response
        except Exception as e:
            print(f"Error assessing answer with LLM (async): {e}")
            return self._basic_assessment_heuristic(answer)

    def _basic_assessment_heuristic(self, answer: str) -> Dict[str, Any]:
        """
        Basic rule-based assessment as fallback.

        Used when LLM assessment fails.
        """
        answer_length = len(answer)
        word_count = len(answer.split())

        # Simple heuristics
        is_very_short = answer_length < 15
        is_disengaged_word = answer.lower().strip() in [
            "no", "yes", "idk", "dunno", "not sure", "maybe", "skip", "pass", "next"
        ]

        # Determine answer type
        if is_disengaged_word or word_count < 3:
            answer_type = "off_topic" if is_disengaged_word else "partial_answer"
        elif word_count < 10:
            answer_type = "partial_answer"
        else:
            answer_type = "direct_answer"

        # Determine engagement
        engagement_level = "disengaged" if (is_very_short or is_disengaged_word) else "engaged"

        # Detail score (1-5)
        if word_count < 5:
            detail_score = 1
        elif word_count < 15:
            detail_score = 2
        elif word_count < 30:
            detail_score = 3
        elif word_count < 50:
            detail_score = 4
        else:
            detail_score = 5

        return {
            "answer_type": answer_type,
            "engagement_level": engagement_level,
            "detail_score": detail_score,
            "relevance_score": 0.3 if is_disengaged_word else 0.6,
            "enthusiasm_detected": False if (is_very_short or is_disengaged_word) else True,
            "reasoning": "Fallback heuristic assessment due to LLM error",
            "answer_length": answer_length
        }
