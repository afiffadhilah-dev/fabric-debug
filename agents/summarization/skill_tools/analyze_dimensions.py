import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from utils.data_loader import DataLoader


class AnalyzeAgent:
    """
    Agent for analyzing skills dimensions from extracted skills data.
    
    Takes output from conversation/resume extraction and adds 6 dimensions
    to each skill: duration, depth, autonomy, scale, constraint, production.
    """
    
    def __init__(
        self,
        llm_service: LLMService = None,
        prompt_loader: PromptLoader = None,
        data_loader: DataLoader = None
    ):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.data_loader = data_loader or DataLoader()
        self.llm_deep = llm_service or LLMService.deep()
        self.data_dir = Path(__file__).parent.parent.parent.parent / "data" / "analyze"

    def _format_evidence(self, evidence: List[Dict[str, Any]]) -> str:
        """Format evidence list into readable text"""
        formatted = []
        for ev in evidence:
            quote = ev.get("quote", "")
            timestamp = ev.get("timestamp", "")
            if quote:
                if timestamp:
                    formatted.append(f"[{timestamp}] {quote}")
                else:
                    formatted.append(quote)
        return "\n".join(formatted)

    def _get_dimensions_schema(self) -> Dict[str, Any]:
        """Schema for dimensions analysis"""
        return {
            "duration": "string",
            "depth": "string",
            "autonomy": "string",
            "scale": "string",
            "constraint": "string",
            "production": "string"
        }

    def _analyze_skill_dimensions(
        self,
        skill_name: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Analyze a single skill to extract 6 dimensions using LLM.
        
        Args:
            skill_name: Name of the skill
            evidence: List of evidence objects with quote and timestamp
            
        Returns:
            Dictionary with 6 dimensions
        """
        if not evidence:
            return {
                "duration": "N/A",
                "depth": "N/A",
                "autonomy": "N/A",
                "scale": "N/A",
                "constraint": "N/A",
                "production": "N/A"
            }

        evidence_text = self._format_evidence(evidence)
        
        human_prompt = self.prompt_loader.load(
            "analyze_dimensions",
            mode="summarization",
            skill_name=skill_name,
            evidence_text=evidence_text
        )

        result = self.llm_deep.generate_json(
            system_prompt="You are an expert at analyzing technical skills and experience from evidence. Provide short, concise keywords or phrases (2-5 words max) for each dimension based only on the provided evidence.",
            human_prompt=human_prompt,
            schema=self._get_dimensions_schema()
        )

        if result is None:
            return {
                "duration": "N/A",
                "depth": "N/A",
                "autonomy": "N/A",
                "scale": "N/A",
                "constraint": "N/A",
                "production": "N/A"
            }

        return {
            "duration": result.get("duration", "N/A"),
            "depth": result.get("depth", "N/A"),
            "autonomy": result.get("autonomy", "N/A"),
            "scale": result.get("scale", "N/A"),
            "constraint": result.get("constraint", "N/A"),
            "production": result.get("production", "N/A")
        }

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze skills dimensions from extracted skills data.
        
        Args:
            input_data: Dictionary with structure:
                {
                    "candidate_id": "...",
                    "skills": [
                        {
                            "name": "...",
                            "evidence": [...]
                        }
                    ],
                    "behavior_observations": [...]
                }
                
        Returns:
            Same structure with dimensions added to each skill
        """
        result = {
            "candidate_id": input_data.get("candidate_id", ""),
            "skills": [],
            "behavior_observations": input_data.get("behavior_observations", [])
        }

        skills = input_data.get("skills", [])
        
        for skill in skills:
            skill_name = skill.get("name", "")
            evidence = skill.get("evidence", [])
            
            # Analyze dimensions for this skill
            dimensions = self._analyze_skill_dimensions(skill_name, evidence)
            
            # Add dimensions to skill
            analyzed_skill = skill.copy()
            analyzed_skill["dimensions"] = dimensions
            
            result["skills"].append(analyzed_skill)

        return result

    def analyze_from_file(
        self,
        input_filename: str = "input.json",
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load data from file, analyze, and optionally save results.
        
        Args:
            input_filename: Input JSON file name
            output_filename: Optional output file name (if None, adds '_analyzed' suffix)
            
        Returns:
            Analyzed data dictionary
        """
        # Load input data
        input_path = self.data_dir / input_filename
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        with open(input_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)
        
        # Analyze
        analyzed_data = self.analyze(input_data)
        
        # Save if output filename provided
        if output_filename:
            output_path = self.data_dir / output_filename
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(analyzed_data, f, indent=2, ensure_ascii=False)
        
        return analyzed_data

