import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, END

from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from utils.data_loader import DataLoader


class BaseState(TypedDict):
    input_text: str
    target_role: str
    extracted_skills: Dict[str, Any]
    merged_skills: Dict[str, Any]
    error: str


class BaseSummarizationAgent(ABC):
    """
    Base agent for skills extraction and analysis.
    """

    extract_prompt: str
    merge_prompt: str
    text_key: str
    data_subdir: str

    def __init__(
        self,
        llm_service: LLMService = None,
        prompt_loader: PromptLoader = None,
        data_loader: DataLoader = None
    ):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.data_loader = data_loader or DataLoader()
        self.llm_fast = llm_service or LLMService.fast()
        self.llm_deep = LLMService.deep()
        self.data_dir = Path(__file__).parent.parent.parent / "data" / self.data_subdir
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(BaseState)
        graph.add_node("extract", self._extract_node)
        graph.add_node("merge", self._merge_node)
        graph.set_entry_point("extract")
        graph.add_edge("extract", "merge")
        graph.add_edge("merge", END)
        return graph.compile()

    def _get_skill_schema(self) -> Dict[str, Any]:
        """Schema for individual skill entry"""
        return {
            "name_raw": "string",
            "name_normalized": "string",
            "evidence": "string",
            "confidence_score": "number",
            "proficiency_level": "string"
        }

    def _get_output_schema(self) -> Dict[str, Any]:
        skill_schema = self._get_skill_schema()
        return {
            "detected_role": "string",
            "technical_tools": [skill_schema],
            "methodologies": [skill_schema],
            "domain_knowledge": [skill_schema],
            "soft_skills": [skill_schema]
        }

    def _normalize_role(self, role: str) -> str:
        if not role or role.lower() == "auto":
            return "Auto-detect"
        if " " in role or role[0].isupper():
            return role
        return role.replace("_", " ").title()

    def _extract_node(self, state: BaseState) -> Dict[str, Any]:
        target_role = state.get("target_role", "auto")
        role_display = self._normalize_role(target_role)

        system_prompt = self.prompt_loader.load("system", mode="summarization")
        human_prompt = self.prompt_loader.load(
            self.extract_prompt,
            mode="summarization",
            target_role=role_display,
            **{self.text_key: state["input_text"]}
        )

        result = self.llm_fast.generate_json(
            system_prompt=system_prompt,
            human_prompt=human_prompt,
            schema=self._get_output_schema()
        )

        if result is None:
            return {
                "extracted_skills": self._empty_skills_result(),
                "error": "Failed to extract skills"
            }

        return {
            "extracted_skills": {
                "detected_role": result.get("detected_role", role_display),
                "technical_tools": result.get("technical_tools", []),
                "methodologies": result.get("methodologies", []),
                "domain_knowledge": result.get("domain_knowledge", []),
                "soft_skills": result.get("soft_skills", [])
            }
        }

    def _merge_node(self, state: BaseState) -> Dict[str, Any]:
        extracted_skills = state.get("extracted_skills", {})

        if not extracted_skills or self._is_empty_skills(extracted_skills):
            return {"merged_skills": self._empty_skills_result()}

        system_prompt = self.prompt_loader.load("system", mode="summarization")
        human_prompt = self.prompt_loader.load(
            self.merge_prompt,
            mode="summarization",
            extracted_skills=json.dumps(extracted_skills, indent=2, ensure_ascii=False)
        )

        result = self.llm_deep.generate_json(
            system_prompt=system_prompt,
            human_prompt=human_prompt,
            schema=self._get_output_schema()
        )

        if result is None:
            return {"merged_skills": extracted_skills}

        return {
            "merged_skills": {
                "detected_role": result.get("detected_role", extracted_skills.get("detected_role", "unknown")),
                "technical_tools": self._deduplicate(result.get("technical_tools", [])),
                "methodologies": self._deduplicate(result.get("methodologies", [])),
                "domain_knowledge": self._deduplicate(result.get("domain_knowledge", [])),
                "soft_skills": self._deduplicate(result.get("soft_skills", []))
            }
        }

    def _empty_skills_result(self) -> Dict[str, Any]:
        return {
            "detected_role": "unknown",
            "technical_tools": [],
            "methodologies": [],
            "domain_knowledge": [],
            "soft_skills": []
        }

    def _is_empty_skills(self, skills: Dict[str, Any]) -> bool:
        return (
            not skills.get("technical_tools") and
            not skills.get("methodologies") and
            not skills.get("domain_knowledge") and
            not skills.get("soft_skills")
        )

    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged = {}
        for entry in results:
            normalized = entry.get("name_normalized", "")
            if not normalized:
                continue
            if normalized in merged:
                existing = merged[normalized]
                new_evidence = entry.get("evidence", "")
                if new_evidence and new_evidence not in existing["evidence"]:
                    existing["evidence"] = f"{existing['evidence']} | {new_evidence}"
                existing["confidence_score"] = max(
                    existing["confidence_score"],
                    entry.get("confidence_score", 0)
                )
                existing_level = existing.get("proficiency_level", "intermediate")
                new_level = entry.get("proficiency_level", "intermediate")
                level_order = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
                if level_order.get(new_level, 2) > level_order.get(existing_level, 2):
                    existing["proficiency_level"] = new_level
            else:
                merged[normalized] = {
                    "name_raw": entry.get("name_raw", normalized),
                    "name_normalized": normalized,
                    "evidence": entry.get("evidence", ""),
                    "confidence_score": entry.get("confidence_score", 0),
                    "proficiency_level": entry.get("proficiency_level", "intermediate")
                }
        return list(merged.values())

    def save_results(self, results: Dict[str, Any], filename: str = "output.json") -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.data_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return output_path

    def _run_pipeline(self, input_text: str, target_role: str = "auto") -> Dict[str, Any]:
        if not input_text or not input_text.strip():
            return self._empty_skills_result()

        initial_state: BaseState = {
            "input_text": input_text,
            "target_role": target_role,
            "extracted_skills": {},
            "merged_skills": {},
            "error": ""
        }
        final_state = self.graph.invoke(initial_state)
        return final_state["merged_skills"]

    @abstractmethod
    def analyze(self, *args, **kwargs) -> Dict[str, Any]:
        pass

    async def analyze_async(self, *args, **kwargs) -> Dict[str, Any]:
        return self.analyze(*args, **kwargs)
