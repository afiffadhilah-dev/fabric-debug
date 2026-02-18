import json
from enum import Enum
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from config.settings import settings
from utils.language_config import SUPPORTED_LANGUAGES


def _apply_language_instruction(system_prompt: Optional[str], langcode: Optional[str]) -> Optional[str]:
    """
    Append a language instruction to the system prompt if langcode is set
    and is not English.

    Args:
        system_prompt: Original system prompt (may be None)
        langcode: ISO 639-1 language code (e.g. "id", "es")

    Returns:
        System prompt with language instruction appended, or original if no change needed
    """
    if not langcode or langcode.lower() == "en":
        return system_prompt

    language_name = SUPPORTED_LANGUAGES.get(langcode.lower(), langcode)
    instruction = (
        f"\n\nIMPORTANT: You MUST respond entirely in {language_name}. "
        "Do not use English unless quoting technical terms."
    )

    if system_prompt:
        return system_prompt + instruction
    return instruction.strip()


class LLMProvider(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

class LLMService:
    """
    Provider-agnostic LLM wrapper that supports:
    - OpenAI
    - OpenRouter (OpenAI-compatible)
    - Gemini
    - Ollama (local, OpenAI-compatible)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.model_name = model_name or settings.LLM_MODEL
        self.temperature = temperature

        self.model = self._load_provider_model()

    @classmethod
    def fast(cls) -> "LLMService":
        """Create LLM service with fast model for quick extraction"""
        return cls(model_name=settings.LLM_FAST_MODEL)

    @classmethod
    def deep(cls) -> "LLMService":
        """Create LLM service with deep model for thorough analysis"""
        return cls(model_name=settings.LLM_DEEP_MODEL)

    # ---------------------------------------------------------------------
    # Provider Loader
    # ---------------------------------------------------------------------
    def _load_provider_model(self):
        provider = self.provider

        # ★ OPENAI (native)
        if provider == "openai":
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
            )

        # ★ OPENROUTER (OpenAI-compatible API)
        if provider == "openrouter":
            return ChatOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                model=self.model_name,
                temperature=self.temperature,
            )

        # ★ OLLAMA (OpenAI-compatible)
        if provider == "ollama":
            return ChatOpenAI(
                api_key="ollama",  # not used
                base_url="http://localhost:11434/v1",
                model=self.model_name,
                temperature=self.temperature,
            )

        # ★ GOOGLE GEMINI
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
            )

        raise ValueError(f"Unsupported LLM provider: {provider}")

    # ---------------------------------------------------------------------
    # Main Text Generator
    # ---------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        langcode: Optional[str] = None
    ) -> str:
        """
        Generate raw text response from LLM

        Args:
            prompt: The main prompt/question
            system_prompt: Optional system prompt for context
            langcode: Optional ISO 639-1 language code for response language

        Returns:
            Raw text response from LLM
        """
        system_prompt = _apply_language_instruction(system_prompt, langcode)
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        try:
            response = self.model.invoke(messages)

            # LangChain models return text in different formats
            if isinstance(response.content, str):
                return response.content
            else:
                return response.content[0].get("text", "")

        except Exception as e:
            print("LLMService.generate error:", e)
            return ""

    # ---------------------------------------------------------------------
    # Main JSON Generator
    # ---------------------------------------------------------------------
    def generate_json(
        self,
        system_prompt: str,
        human_prompt: str,
        schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        messages = [
            SystemMessage(content=self._inject_json_rules(system_prompt, schema)),
            HumanMessage(content=human_prompt)
        ]

        try:
            # For providers that support response_format, pass it dynamically
            # This ensures JSON mode is only used when we actually need JSON
            if self.provider in ["openai", "openrouter"]:
                response = self.model.invoke(
                    messages,
                    response_format={"type": "json_object"}
                )
            else:
                # For Gemini and Ollama, rely on system prompt enforcement
                response = self.model.invoke(messages)

            # LangChain models return text in different formats
            if isinstance(response.content, str):
                content = response.content
            else:
                content = response.content[0].get("text", "")

            return json.loads(content)

        except Exception as e:
            print("LLMService.generate_json error:", e)
            return None

    # ---------------------------------------------------------------------
    # Async Text Generator (for parallel execution)
    # ---------------------------------------------------------------------
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        langcode: Optional[str] = None
    ) -> str:
        """
        Async version of generate() for parallel LLM calls

        This enables parallelization of independent LLM calls, drastically
        reducing total response time.

        Args:
            prompt: The main prompt/question
            system_prompt: Optional system prompt for context
            langcode: Optional ISO 639-1 language code for response language

        Returns:
            Raw text response from LLM
        """
        system_prompt = _apply_language_instruction(system_prompt, langcode)
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        try:
            response = await self.model.ainvoke(messages)

            # LangChain models return text in different formats
            if isinstance(response.content, str):
                return response.content
            else:
                return response.content[0].get("text", "")

        except Exception as e:
            print("LLMService.generate_async error:", e)
            return ""

    # ---------------------------------------------------------------------
    # Async JSON Generator (for parallel execution)
    # ---------------------------------------------------------------------
    async def generate_json_async(
        self,
        system_prompt: str,
        human_prompt: str,
        schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Async version of generate_json() for parallel LLM calls

        Args:
            system_prompt: System prompt with instructions
            human_prompt: Human prompt with question
            schema: Expected JSON schema

        Returns:
            Parsed JSON dict or None on error
        """
        messages = [
            SystemMessage(content=self._inject_json_rules(system_prompt, schema)),
            HumanMessage(content=human_prompt)
        ]

        try:
            # For providers that support response_format, pass it dynamically
            if self.provider in ["openai", "openrouter"]:
                response = await self.model.ainvoke(
                    messages,
                    response_format={"type": "json_object"}
                )
            else:
                # For Gemini and Ollama, rely on system prompt enforcement
                response = await self.model.ainvoke(messages)

            # LangChain models return text in different formats
            if isinstance(response.content, str):
                content = response.content
            else:
                content = response.content[0].get("text", "")

            return json.loads(content)

        except Exception as e:
            print("LLMService.generate_json_async error:", e)
            return None

    # ---------------------------------------------------------------------
    # JSON Enforcement Layer
    # ---------------------------------------------------------------------
    def _inject_json_rules(self, system_prompt: str, schema: Dict[str, Any]) -> str:
        """
        Ensures all providers return the correct JSON — especially Ollama and OpenRouter.
        """

        return f"""
{system_prompt}

You MUST return ONLY valid JSON matching this schema:

{json.dumps(schema, indent=2)}

Rules:
- Output **only** a JSON object.
- No commentary, no markdown, no code fences.
- Do not explain the JSON, only output it.
- Keys and structure must match the schema exactly.
"""

    # ---------------------------------------------------------------------
    # LangChain Agent Integration
    # ---------------------------------------------------------------------
    def get_langchain_llm(self):
        """
        Get the underlying LangChain LLM instance for agent use.

        This is useful when you need to pass the LLM to LangChain agents
        (like ReAct agents) that require a LangChain-compatible LLM.

        Returns:
            The LangChain ChatModel instance (ChatOpenAI, ChatGoogleGenerativeAI, etc.)

        Example:
            llm_service = LLMService()
            llm = llm_service.get_langchain_llm()
            agent = create_react_agent(llm, tools)
        """
        return self.model