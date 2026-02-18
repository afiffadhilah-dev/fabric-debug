from typing import Any, Dict, List
import json

from agents.summarization.utils.base_extractor import BaseSummarizationAgent


class ResumeAgent(BaseSummarizationAgent):
    """
    Agent for extracting skills from resume content.
    
    Supports ANY role dynamically - the LLM will intelligently
    determine relevant skills based on the target role context.
    """
    
    extract_prompt = "resume_extract"
    merge_prompt = "resume_merge"
    text_key = "resume_text"
    data_subdir = "resume"

    def _format_history(self, resume_history: List[Dict[str, str]]) -> str:
        parts = []
        for i, exchange in enumerate(resume_history, 1):
            question = exchange.get("question", "")
            answer = exchange.get("answer", "")
            parts.append(f"Q{i}: {question}\nA{i}: {answer}")
        return "\n\n".join(parts)

    def load_resume_data(self, filename: str = "input.json") -> Dict[str, Any]:
        return self.data_loader.load_resume_data(filename)

    def _get_output_schema(self) -> Dict[str, Any]:
        """Return schema matching prompts/summarization/resume_extract.md

        Top-level keys: candidate_id, skills, behavior_observations
        Each evidence item contains quote and timestamp.
        """
        evidence_schema = {"quote": "string", "timestamp": "string"}
        item_schema = {"name": "string", "evidence": [evidence_schema]}
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
                    evidence_items.append({"quote": quote, "timestamp": timestamp})

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

        # Merge child items into parent technologies using substring mapping
        # e.g., Spring Boot, Hibernate -> Java; Flask, FastAPI -> Python
        parent_map = {
            "Java": ["spring", "spring boot", "hibernate", "jpa"],
            "Python": ["flask", "fastapi", "django"],
            "Node.js": ["express", "nestjs", "node.js", "nodejs"],
            "React.js": ["react", "redux", "context api", "zustand"],
            "Docker": ["docker compose", "docker-compose", "docker"],
            "AWS": ["ec2", "s3", "lambda", "rds", "aws"],
            "GCP": ["compute engine", "cloud run", "gcp"],
        }

        # Helper to find parent for a given normalized name
        def find_parent_for(name_lc: str) -> str:
            for parent, subs in parent_map.items():
                for sub in subs:
                    if sub in name_lc:
                        return parent
            return ""

        # Apply merges
        # Build a list since we'll modify merged
        keys = list(merged.keys())
        for key in keys:
            entry = merged.get(key)
            name_lc = (entry.get("name", "") or "").lower()
            parent = find_parent_for(name_lc)
            if not parent:
                # also try splitting composite names like 'Hibernate, JPA'
                parts = [p.strip().lower() for p in name_lc.replace("/", ",").split(",")]
                for part in parts:
                    parent = find_parent_for(part)
                    if parent:
                        break

            if parent and parent.lower() != key:
                # ensure parent exists
                parent_key = parent.lower()
                if parent_key in merged:
                    parent_entry = merged[parent_key]
                else:
                    parent_entry = {"name": parent, "evidence": []}
                    merged[parent_key] = parent_entry

                # Move evidence items that are unique
                existing_quotes = {ev.get("quote", "").strip() for ev in parent_entry["evidence"]}
                for ev in entry["evidence"]:
                    q = ev.get("quote", "").strip()
                    if q and q not in existing_quotes:
                        parent_entry["evidence"].append(ev)
                        existing_quotes.add(q)

                # remove child entry
                if key in merged:
                    del merged[key]

        # Keep top 3 most informative quotes per skill (LLM tends to put best first)
        for item in merged.values():
            item["evidence"] = item["evidence"][:3]

        # Normalize output list: ensure keys correspond to the 'name' field
        result = []
        for v in merged.values():
            # If name is missing, fall back to first evidence or empty
            n = v.get("name") or ""
            result.append({"name": n, "evidence": v.get("evidence", [])})

        return result

        return list(merged.values())

    def _extract_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        candidate_id = state.get("candidate_id", "") or ""
        target_role = state.get("target_role", "auto")

        system_prompt = self.prompt_loader.load("system", mode="summarization")
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
                "behavior_observations": self._deduplicate_entries(result.get("behavior_observations", [])),
            }
        }

    def _merge_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        extracted_skills = state.get("extracted_skills", {})
        candidate_id = extracted_skills.get("candidate_id") or state.get("candidate_id") or ""

        if not extracted_skills or self._is_empty_skills(extracted_skills):
            return {"merged_skills": self._empty_skills_result(candidate_id)}

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
            merged = extracted_skills.copy()
            merged["candidate_id"] = candidate_id
            merged["skills"] = self._deduplicate_entries(merged.get("skills", []))
            merged["behavior_observations"] = self._deduplicate_entries(merged.get("behavior_observations", []))
            return {"merged_skills": merged}

        return {
                "merged_skills": {
                "candidate_id": candidate_id or result.get("candidate_id", ""),
                "skills": self._deduplicate_entries(result.get("skills", [])),
                "behavior_observations": self._deduplicate_entries(result.get("behavior_observations", [])),
            }
        }

    def _run_pipeline(self, input_text: str, target_role: str = "auto", candidate_id: str = "") -> Dict[str, Any]:
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

    def analyze(
        self,
        resume_text: str = None,
        resume_history: List[Dict[str, str]] = None,
        target_role: str = "auto",
        candidate_id: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze resume content and extract skills based on target role.
        
        Args:
            resume_text: Full resume text to analyze
            resume_history: List of Q&A dictionaries with 'question' and 'answer' keys
            target_role: Target role for analysis. Can be ANY role string:
                - "auto": Auto-detect role from content (default)
                - Any role name like "software_engineer", "data_scientist", 
                  "product_manager", "devops_engineer", "ux_designer", etc.
                - The LLM will intelligently extract relevant skills
        
        Returns:
            Dictionary containing:
                - detected_role: The detected or specified role
                - technical_tools: List of tools/software skills
                - methodologies: List of methodology skills
                - domain_knowledge: List of domain knowledge skills
                - soft_skills: List of soft skills
        """
        if resume_text:
            return self._run_pipeline(resume_text, target_role, candidate_id)
        if resume_history:
            return self._run_pipeline(self._format_history(resume_history), target_role, candidate_id)
        return self._empty_skills_result(candidate_id)
