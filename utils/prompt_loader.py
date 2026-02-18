"""
Utility to load and format prompt templates from markdown files

This keeps prompts clean and separated from code logic.
"""

from pathlib import Path
from typing import  Any


class PromptLoader:
    """Load and format prompt templates"""

    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize prompt loader

        Args:
            prompts_dir: Root directory containing prompt templates
        """
        # Get absolute path to prompts directory
        self.prompts_dir = Path(__file__).parent.parent / prompts_dir

    def load(
        self,
        template_name: str,
        mode: str = "shared",
        **kwargs: Any
    ) -> str:
        """
        Load and format a prompt template

        Args:
            template_name: Name of template file (without .md extension)
            mode: "project_mode", "resume_mode", or "shared"
            **kwargs: Variables to substitute in template

        Returns:
            Formatted prompt string

        Examples:
            loader = PromptLoader()

            # Load project mode first question
            prompt = loader.load(
                "first_question",
                mode="project_mode",
                project_name="Banking App",
                gap_description="React Native depth unclear",
                gap_context="Project requires React Native"
            )

            # Load shared explanation
            prompt = loader.load(
                "explanation",
                mode="shared",
                last_ai_message="What's your experience?",
                last_user_message="I don't understand",
                recent_conversation="..."
            )
        """
        # Build path to template file
        template_path = self.prompts_dir / mode / f"{template_name}.md"

        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {template_path}\n"
                f"Available modes: project_mode, resume_mode, shared"
            )

        # Read template
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Format template with provided variables
        try:
            formatted = template.format(**kwargs)
            return formatted
        except KeyError as e:
            raise ValueError(
                f"Missing required variable '{e.args[0]}' for template '{template_name}' in mode '{mode}'"
            )

    def load_project_mode(self, template_name: str, **kwargs) -> str:
        """Convenience method for project mode templates"""
        return self.load(template_name, mode="project_mode", **kwargs)

    def load_resume_mode(self, template_name: str, **kwargs) -> str:
        """Convenience method for resume mode templates"""
        return self.load(template_name, mode="resume_mode", **kwargs)

    def load_shared(self, template_name: str, **kwargs) -> str:
        """Convenience method for shared templates"""
        return self.load(template_name, mode="shared", **kwargs)
