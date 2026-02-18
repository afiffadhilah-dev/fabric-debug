"""
LLM-based parser to convert document text into structured predefined question sets.
"""
from typing import Dict, Any, List
from utils.llm_service import LLMService


class PredefinedQuestionParser:
    """Parse document text into structured predefined question data using LLM"""

    def __init__(self):
        self.llm_service = LLMService()

    def parse_document(self, document_text: str, role_name: str, role_level: str) -> Dict[str, Any]:
        """
        Parse a document containing interview questions into structured format.

        Args:
            document_text: Raw text extracted from the document
            role_name: Name of the role (e.g., "Fullstack Developer")
            role_level: Level of the role (e.g., "Senior", "Junior")

        Returns:
            Dictionary containing structured question set data with schema:
            {
                "questions": [
                    {
                        "category": str,
                        "question_text": str,
                        "what_assesses": [str],
                        "expected_answer_pattern": str,
                        "order": int,
                        "is_required": bool
                    }
                ]
            }
        """
        system_prompt = self._get_system_prompt()
        human_prompt = self._get_human_prompt(document_text, role_name, role_level)

        schema = self._get_response_schema()

        result = self.llm_service.generate_json(
            system_prompt=system_prompt,
            human_prompt=human_prompt,
            schema=schema
        )

        return result

    def _get_system_prompt(self) -> str:
        """System prompt for the LLM"""
        return """You are an expert at parsing interview question documents into structured data.

Your task is to extract interview questions from a document and format them into a structured JSON format.

CRITICAL INSTRUCTIONS FOR CATEGORIES:
1. Use MAIN SECTION HEADINGS ONLY as categories (typically in ALL CAPS or primary headers)
2. DO NOT use sub-section headings as categories
3. If a main section has multiple questions or sub-sections, ALL questions under it share the SAME category
4. Example:
   - Main section: "FRONTEND DEVELOPMENT" → category = "FRONTEND DEVELOPMENT"
   - Sub-section: "Language & Preferences" → still use "FRONTEND DEVELOPMENT" as category
   - All questions under this section use "FRONTEND DEVELOPMENT"

Other requirements:
1. Extract what each question assesses (the competencies/skills) from "What this assesses" sections
2. Extract the expected answer pattern from "Expected answer" sections
3. Maintain the original sequential order of questions (order field: 0, 1, 2, ...)
4. Mark all questions as required unless explicitly stated otherwise
5. Each question must be a separate entry with its own order number

Be thorough and accurate. Preserve the hierarchical structure by using consistent main categories."""

    def _get_human_prompt(self, document_text: str, role_name: str, role_level: str) -> str:
        """Human prompt with the document text"""
        return f"""Parse the following interview question document for the role: {role_name} ({role_level})

Document content:
{document_text}

IMPORTANT: Use MAIN SECTION HEADINGS as categories. Examples from the document:
- "GENERAL INFORMATION" → category
- "LEADERSHIP EXPERIENCE" → category
- "FRONTEND DEVELOPMENT" → category (even if it has sub-sections like "Language & Preferences")
- "MOBILE DEVELOPMENT" → category (even if it has sub-sections like "Flutter & iOS Specifics")
- "DATABASE EXPERIENCE" → category (even if it has sub-sections like "Database Types", "Messaging & Topology")

Extract all questions and format them according to the schema. Each question should include:
- category: MAIN section heading only (in ALL CAPS)
- question_text: The exact question to ask
- what_assesses: List of competencies/skills from "What this assesses" section
- expected_answer_pattern: Text from "Expected answer" section
- order: Sequential number starting from 0 (increment for EACH question)
- is_required: true (default for all questions unless explicitly stated otherwise)"""

    def _get_response_schema(self) -> Dict[str, Any]:
        """JSON schema for the response"""
        return {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Category or topic of the question"
                            },
                            "question_text": {
                                "type": "string",
                                "description": "The actual question to ask"
                            },
                            "what_assesses": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of competencies/skills assessed"
                            },
                            "expected_answer_pattern": {
                                "type": "string",
                                "description": "Guidance on expected answer"
                            },
                            "order": {
                                "type": "integer",
                                "description": "Sequential order of the question"
                            },
                            "is_required": {
                                "type": "boolean",
                                "description": "Whether this question is required"
                            }
                        },
                        "required": [
                            "category",
                            "question_text",
                            "what_assesses",
                            "expected_answer_pattern",
                            "order",
                            "is_required"
                        ]
                    }
                }
            },
            "required": ["questions"]
        }
