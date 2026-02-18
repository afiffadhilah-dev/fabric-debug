"""
Technical skill analysis tool.

Extracts skills with 6 key attributes from resume and conversation history.
"""

from typing import List, Dict, Any, Optional
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader


class SkillAnalyzer:
    """
    Analyzes technical skills from resume and conversation history.

    Extracts skills with 6 attributes:
    1. Duration - How long they've used the skill
    2. Depth - Complexity level and aspects implemented
    3. Autonomy - Ownership level and independence
    4. Scale - Impact size (users, traffic, components)
    5. Constraints - Limitations or challenges encountered
    6. Production vs Prototype - Production-ready or PoC
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_loader = PromptLoader()

    def analyze_skill_attributes(
        self,
        resume_text: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze skill attributes from resume and conversation.

        Args:
            resume_text: Resume or profile text
            conversation_history: Optional list of Q&A pairs
                Format: [{"question": "...", "answer": "..."}, ...]

        Returns:
            List of dictionaries with structure:
            {
                "name": "Python",
                "duration": "3 years" | "unknown",
                "depth": "advanced web frameworks" | "unknown",
                "autonomy": "led team of 3" | "unknown",
                "scale": "5M users" | "unknown",
                "constraints": "legacy system" | "unknown",
                "production_vs_prototype": "production" | "unknown",
                "evidence": "Supporting text from resume/conversation",
                "confidence_score": 0.9
            }
        """
        conversation_history = conversation_history or []

        # Use LLM to extract skill attributes
        skills_data = self._extract_skill_attributes_with_llm(
            resume_text,
            conversation_history
        )

        # Handle None response from LLM failure
        if skills_data is None:
            print("Warning: LLM returned None - using empty skill attributes")
            return []

        return skills_data.get('skills', [])

    async def analyze_skill_attributes_async(
        self,
        resume_text: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        ASYNC version of analyze_skill_attributes for parallel execution.

        Enables parallel extraction alongside other operations.
        """
        conversation_history = conversation_history or []

        skills_data = await self._extract_skill_attributes_with_llm_async(
            resume_text,
            conversation_history
        )

        if skills_data is None:
            print("Warning: LLM returned None - using empty skill attributes")
            return []

        return skills_data.get('skills', [])

    def _extract_skill_attributes_with_llm(
        self,
        resume_text: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to extract skill attributes from resume and conversation.

        Args:
            resume_text: Resume text
            conversation_history: List of Q&A pairs

        Returns:
            Dictionary with skills and their attributes, or None on error
        """
        # Build conversation context
        conversation_text = "\n\n".join([
            f"Q: {entry['question']}\nA: {entry['answer']}"
            for entry in conversation_history
        ])

        # Load system prompt
        system_prompt = self.prompt_loader.load("skill_attributes_extraction", mode="shared")

        # Build human prompt
        human_prompt = f"""
Resume:
{resume_text}

Conversation History:
{conversation_text if conversation_text else "No conversation yet"}

Extract skill attributes as per the system prompt instructions.
"""

        # Define JSON schema for validation
        schema = {
            "type": "object",
            "properties": {
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "duration": {"type": "string"},
                            "depth": {"type": "string"},
                            "autonomy": {"type": "string"},
                            "scale": {"type": "string"},
                            "constraints": {"type": "string"},
                            "production_vs_prototype": {
                                "type": "string",
                                "enum": ["production", "prototype", "PoC", "unknown"]
                            },
                            "evidence": {"type": "string"},
                            "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
                        },
                        "required": [
                            "name", "duration", "depth", "autonomy", "scale",
                            "constraints", "production_vs_prototype", "evidence", "confidence_score"
                        ]
                    }
                }
            },
            "required": ["skills"]
        }

        try:
            response = self.llm_service.generate_json(
                system_prompt=system_prompt,
                human_prompt=human_prompt,
                schema=schema
            )
            if response is None:
                print(f"Warning: LLM returned None for skill attributes extraction")
                return None
            return response
        except Exception as e:
            print(f"Error extracting skill attributes with LLM: {e}")
            return None

    async def _extract_skill_attributes_with_llm_async(
        self,
        resume_text: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """ASYNC version of _extract_skill_attributes_with_llm"""
        # Build conversation context
        conversation_text = "\n\n".join([
            f"Q: {entry['question']}\nA: {entry['answer']}"
            for entry in conversation_history
        ])

        # Load system prompt
        system_prompt = self.prompt_loader.load("skill_attributes_extraction", mode="shared")

        # Build human prompt
        human_prompt = f"""
Resume:
{resume_text}

Conversation History:
{conversation_text if conversation_text else "No conversation yet"}

Extract skill attributes as per the system prompt instructions.
"""

        # Define JSON schema (same as sync version)
        schema = {
            "type": "object",
            "properties": {
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "duration": {"type": "string"},
                            "depth": {"type": "string"},
                            "autonomy": {"type": "string"},
                            "scale": {"type": "string"},
                            "constraints": {"type": "string"},
                            "production_vs_prototype": {
                                "type": "string",
                                "enum": ["production", "prototype", "PoC", "unknown"]
                            },
                            "evidence": {"type": "string"},
                            "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
                        },
                        "required": [
                            "name", "duration", "depth", "autonomy", "scale",
                            "constraints", "production_vs_prototype", "evidence", "confidence_score"
                        ]
                    }
                }
            },
            "required": ["skills"]
        }

        try:
            response = await self.llm_service.generate_json_async(
                system_prompt=system_prompt,
                human_prompt=human_prompt,
                schema=schema
            )
            if response is None:
                print(f"Warning: LLM returned None for skill attributes extraction (async)")
                return None
            return response
        except Exception as e:
            print(f"Error extracting skill attributes with LLM (async): {e}")
            return None
