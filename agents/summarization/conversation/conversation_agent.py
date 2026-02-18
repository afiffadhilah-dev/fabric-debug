import json
from datetime import datetime
from typing import Any, Dict, List

from agents.summarization.utils.base_extractor import BaseSummarizationAgent


class ConversationAgent(BaseSummarizationAgent):
    """
    Agent for extracting skills from conversation content.
    
    Supports ANY role dynamically. Evidence focuses on raw verbatim 
    quotes and timestamps to preserve the depth of the conversation 
    without subjective scoring.
    """
    
    extract_prompt = "conversation_extract"
    merge_prompt = "conversation_merge"
    text_key = "conversation_text"
    data_subdir = "conversation"

    def _get_evidence_schema(self) -> Dict[str, Any]:
        """Simplified schema for evidence: just the proof."""
        return {
            "quote": "string",
            "timestamp": "string"
        }

    def _get_output_schema(self) -> Dict[str, Any]:
        evidence_schema = self._get_evidence_schema()
        item_schema = {
            "name": "string",
            "evidence": [evidence_schema],
        }
        return {
            "candidate_id": "string",
            "skills": [item_schema],
            "behavior_observations": [item_schema],
        }

    def _empty_skills_result(self, candidate_id: str = "") -> Dict[str, Any]:
        return {
            "candidate_id": candidate_id or "",
            "skills": [],
            "behavior_observations": [],
        }

    def _normalize_name(self, name: str) -> str:
        return (name or "").strip()

    def _is_empty_skills(self, skills: Dict[str, Any]) -> bool:
        return not skills.get("skills") and not skills.get("behavior_observations")

    def _deduplicate_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate entries by normalized name.
        Keep the most unique and informative evidence quotes.
        """
        merged: Dict[str, Dict[str, Any]] = {}
        
        for entry in entries or []:
            name = (entry.get("name") or "").strip()
            if not name:
                continue

            normalized = self._normalize_name(name)
            key = normalized.lower()
            
            evidence_items = []
            for ev in entry.get("evidence", []):
                quote = ev.get("quote", "")
                timestamp = ev.get("timestamp", "")
                
                if quote or timestamp:
                    evidence_items.append({
                        "quote": quote,
                        "timestamp": timestamp
                    })

            if key in merged:
                existing = merged[key]
                existing_quotes = {ev.get("quote", "").strip() for ev in existing["evidence"]}
                
                for ev in evidence_items:
                    quote_text = ev.get("quote", "").strip()
                    if quote_text and quote_text not in existing_quotes:
                        existing["evidence"].append(ev)
                        existing_quotes.add(quote_text)
            else:
                merged[key] = {"name": normalized, "evidence": evidence_items}

        # Keep top 3 most informative quotes per skill
        # LLM usually puts better ones first, so we just slice
        for item in merged.values():
            item["evidence"] = item["evidence"][:3]

        return list(merged.values())

    def _format_answers(self, answers: List[Dict[str, Any]]) -> str:
        """Format answers with question context for depth preservation"""
        parts = []
        for answer_data in answers:
            answer_text = answer_data.get("answer", "")
            question_text = answer_data.get("question", "")
            dt = answer_data.get("datetime")
            
            if isinstance(dt, str):
                dt_str = dt
            elif dt:
                dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if question_text:
                parts.append(f"[{dt_str}]\nQ: {question_text}\nA: {answer_text}")
            else:
                parts.append(f"[{dt_str}] {answer_text}")
        
        return "\n\n".join(parts)

    def load_conversation_data(self, filename: str = "input.json") -> Dict[str, Any]:
        return self.data_loader.load_conversation_data(filename)

    def analyze(
        self, 
        answers: List[Dict[str, Any]], 
        target_role: str = "auto",
        candidate_id: str = ""
    ) -> Dict[str, Any]:
        if not answers:
            return self._empty_skills_result(candidate_id)
            
        return self._run_pipeline(
            self._format_answers(answers),
            target_role=target_role,
            candidate_id=candidate_id,
        )

    def _extract_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        candidate_id = state.get("candidate_id", "") or ""
        target_role = state.get("target_role", "auto")
        
        system_prompt = self.prompt_loader.load("conversation_system", mode="summarization")
        human_prompt = self.prompt_loader.load(
            self.extract_prompt,
            mode="summarization",
            candidate_id=candidate_id,
            target_role=self._normalize_role(target_role),
            **{self.text_key: state["input_text"]}
        )

        result = self.llm_fast.generate_json(
            system_prompt=system_prompt,
            human_prompt=human_prompt,
            schema=self._get_output_schema()
        )

        if result is None:
            return {
                "extracted_skills": self._empty_skills_result(candidate_id),
                "error": "Failed to extract skills"
            }

        return {
            "extracted_skills": {
                "candidate_id": candidate_id or result.get("candidate_id", ""),
                "skills": self._deduplicate_entries(result.get("skills", [])),
                "behavior_observations": self._deduplicate_entries(
                    result.get("behavior_observations", [])
                ),
            }
        }

    def _merge_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        extracted_skills = state.get("extracted_skills", {})
        candidate_id = extracted_skills.get("candidate_id") or state.get("candidate_id") or ""

        if not extracted_skills or self._is_empty_skills(extracted_skills):
            return {"merged_skills": self._empty_skills_result(candidate_id)}

        system_prompt = self.prompt_loader.load("conversation_system", mode="summarization")
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
            merged = extracted_skills.copy()
            merged["candidate_id"] = candidate_id
            merged["skills"] = self._deduplicate_entries(merged.get("skills", []))
            merged["behavior_observations"] = self._deduplicate_entries(
                merged.get("behavior_observations", [])
            )
            return {"merged_skills": merged}

        return {
                "merged_skills": {
                "candidate_id": candidate_id or result.get("candidate_id", ""),
                "skills": self._deduplicate_entries(result.get("skills", [])),
                "behavior_observations": self._deduplicate_entries(
                    result.get("behavior_observations", [])
                ),
            }
        }

    def _run_pipeline(
        self,
        input_text: str,
        target_role: str = "auto",
        candidate_id: str = "",
    ) -> Dict[str, Any]:
        if not input_text or not input_text.strip():
            return self._empty_skills_result(candidate_id)

        initial_state = {
            "input_text": input_text,
            "target_role": target_role,
            "candidate_id": candidate_id or "",
            "extracted_skills": {},
            "merged_skills": {},
            "error": ""
        }
        final_state = self.graph.invoke(initial_state)
        merged = final_state["merged_skills"]
        merged["candidate_id"] = candidate_id or merged.get("candidate_id", "")
        return merged
