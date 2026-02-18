import json
from pathlib import Path
from typing import Dict, List, Any
import re


# -----------------------
# Normalization helpers
# -----------------------

def _normalize(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r"\(.*?\)", "", name)
    s = s.replace("/", ",")
    s = s.replace("-", " ")
    s = s.lower()
    s = " ".join(s.split())
    s = re.sub(r"[^a-z0-9.+ ]", "", s)
    return s.strip()


# -----------------------
# Parent skill mapping
# -----------------------

PARENT_MAP = {
    "java": ["spring", "spring boot", "hibernate", "jpa", "java"],
    "python": ["flask", "fastapi", "django", "pyspark", "python"],
    "node.js": ["express", "nestjs", "node.js", "nodejs", "node js", "node"],
    "go": ["golang", "go lang", "go"],
    "rust": ["rust"],
    "react.js": ["react", "redux", "context api", "zustand", "rtk query", "react native"],
    "angular": ["angular", "rxjs"],
    "vue.js": ["vue"],
    "docker": ["docker compose", "docker-compose", "docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["ec2", "s3", "lambda", "rds", "aws"],
    "gcp": ["compute engine", "cloud run", "gcp", "bigquery"],
    "azure": ["azure"],
    "postgresql": ["postgresql", "postgres", "postgres db"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "kafka": ["kafka"],
    "spark": ["spark", "pyspark"],
    "graphql": ["graphql"],
    "rest api": ["rest", "restful"],
    "ci/cd": ["github actions", "gitlab ci", "jenkins", "ci/cd"],
    "testing": ["jest", "junit", "cypress", "testing", "tdd"],
    "monitoring": ["prometheus", "grafana", "otel", "observability"],
}


def find_parent(name_lc: str) -> str:
    tokens = [t.strip() for t in name_lc.split() if t.strip()]
    for parent, subs in PARENT_MAP.items():
        for sub in subs:
            if sub in name_lc:
                return parent
            for tok in tokens:
                if tok == sub:
                    return parent
    return ""


# =======================
# SKILLS (unchanged)
# =======================

def merge_skills(resume: Dict[str, Any], convo: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Dict[str, Any]] = {}

    def add_entry(src: str, entry: Dict[str, Any]):
        name = entry.get("name", "")
        normalized = _normalize(name)
        parent = find_parent(normalized)

        if not parent:
            for p in normalized.split(","):
                parent = find_parent(p.strip())
                if parent:
                    break

        key = parent or normalized or name.lower()
        if key not in merged:
            merged[key] = {"name": parent or name, "evidence": []}

        for ev in entry.get("evidence", []):
            ev2 = {"quote": ev.get("quote", ""), "timestamp": ev.get("timestamp", ""), "source": src}
            quotes = {e["quote"] for e in merged[key]["evidence"]}
            if ev2["quote"] and ev2["quote"] not in quotes:
                merged[key]["evidence"].append(ev2)

    for e in resume.get("skills", []):
        add_entry("resume", e)
    for e in convo.get("skills", []):
        add_entry("conversation", e)

    out = []
    for v in merged.values():
        out.append({"name": v["name"], "evidence": v["evidence"][:3]})

    return {
        "candidate_id": resume.get("candidate_id") or convo.get("candidate_id"),
        "skills": out
    }


# =======================
# BEHAVIORS (unchanged)
# =======================

def merge_behaviors(resume: Dict[str, Any], convo: Dict[str, Any]) -> List[Dict[str, Any]]:
    merged = {}

    def add(src, item):
        name = item.get("name", "")
        k = _normalize(name)
        if k not in merged:
            merged[k] = {"name": name, "evidence": []}

        for ev in item.get("evidence", []):
            ev2 = {"quote": ev.get("quote", ""), "timestamp": ev.get("timestamp", ""), "source": src}
            quotes = {e["quote"] for e in merged[k]["evidence"]}
            if ev2["quote"] and ev2["quote"] not in quotes:
                merged[k]["evidence"].append(ev2)

    for i in resume.get("behavior_observations", []):
        add("resume", i)
    for i in convo.get("behavior_observations", []):
        add("conversation", i)

    return list(merged.values())


# =======================
# INFRA (structured)
# =======================

def merge_infra(resume: Dict[str, Any], convo: Dict[str, Any]) -> Dict[str, Any]:
    merged = {}

    def key_of(i):
        return (
            (i.get("environment_type") or "").lower().strip(),
            (i.get("scale") or "").lower().strip(),
            (i.get("reliability_expectation") or "").lower().strip(),
            (i.get("operational_constraints") or "").lower().strip(),
        )

    def normalize_evidence(raw):
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return [raw]
        if isinstance(raw, str):
            return [{"quote": raw, "timestamp": ""}]
        return []

    def add(src, item):
        k = key_of(item)
        if k not in merged:
            merged[k] = {
                "environment_type": item.get("environment_type", ""),
                "scale": item.get("scale", ""),
                "reliability_expectation": item.get("reliability_expectation", ""),
                "operational_constraints": item.get("operational_constraints", ""),
                "evidence": [],
                "confidence": item.get("confidence", 0),
            }

        merged[k]["confidence"] = max(merged[k]["confidence"], item.get("confidence", 0))

        for ev in normalize_evidence(item.get("evidence")):
            if isinstance(ev, str):
                quote, timestamp = ev, ""
            else:
                quote = ev.get("quote", "")
                timestamp = ev.get("timestamp", "")

            ev2 = {"quote": quote, "timestamp": timestamp, "source": src}
            quotes = {e["quote"] for e in merged[k]["evidence"]}
            if ev2["quote"] and ev2["quote"] not in quotes:
                merged[k]["evidence"].append(ev2)

    for i in resume.get("infra_contexts", []):
        add("resume", i)
    for i in convo.get("infra_contexts", []):
        add("conversation", i)

    return {
        "candidate_id": resume.get("candidate_id") or convo.get("candidate_id"),
        "infra_contexts": list(merged.values())
    }



# =======================
# DOMAIN (structured)
# =======================

def merge_domains(resume: Dict[str, Any], convo: Dict[str, Any]) -> Dict[str, Any]:
    merged = {}

    """
    Merge domain_contexts from resume and conversation while preserving
    structured fields such as industry, product_type, business_model, etc.

    The agents return items like:
      {"industry": ..., "product_type": ..., "evidence": [...], "confidence": ...}

    We merge by a normalization of industry+product_type to avoid duplicates,
    concatenate/pick the most common values for structured fields, and
    normalize evidence as in other merge helpers.
    """
    merged: Dict[str, Dict[str, Any]] = {}

    def key_for(item: Dict[str, Any]) -> str:
        # prefer industry + product_type, fallback to industry, fallback to product_type
        industry = (item.get("industry") or "").strip()
        product = (item.get("product_type") or "").strip()
        if industry and product:
            return _normalize(f"{industry} {product}")
        if industry:
            return _normalize(industry)
        if product:
            return _normalize(product)
        # last resort: try name or empty
        return _normalize(item.get("name", ""))

    def add_entry(src: str, item: Dict[str, Any]):
        k = key_for(item)
        if k not in merged:
            # initialize with empty structured fields
            merged[k] = {
                "industry": item.get("industry", ""),
                "product_type": item.get("product_type", ""),
                "business_model": item.get("business_model", ""),
                "customer_type": item.get("customer_type", ""),
                "regulatory_or_compliance_context": item.get("regulatory_or_compliance_context", ""),
                "business_criticality": item.get("business_criticality", ""),
                "evidence": [],
                "confidence": item.get("confidence", ""),
            }

        target = merged[k]

        # prefer non-empty structured fields from item if target lacks them
        for fld in ["industry", "product_type", "business_model", "customer_type", "regulatory_or_compliance_context", "business_criticality"]:
            if not target.get(fld) and item.get(fld):
                target[fld] = item.get(fld)

        # confidence: keep the highest-seeming (prefer non-empty)
        if item.get("confidence") and not target.get("confidence"):
            target["confidence"] = item.get("confidence")

        # Normalize evidence (reuse logic from _merge_generic)
        raw_evidence = item.get("evidence", [])
        if isinstance(raw_evidence, str):
            evidence_items = [{"quote": raw_evidence}]
        elif isinstance(raw_evidence, dict):
            evidence_items = [raw_evidence]
        elif isinstance(raw_evidence, list):
            evidence_items = raw_evidence
        else:
            evidence_items = []

        for ev in evidence_items:
            if isinstance(ev, str):
                quote = ev
                timestamp = ""
            elif isinstance(ev, dict):
                quote = ev.get("quote", ev.get("text", ""))
                timestamp = ev.get("timestamp", "")
            else:
                continue

            ev2 = {"quote": quote, "timestamp": timestamp, "source": src}
            quotes = {e.get("quote", "") for e in target["evidence"]}
            if ev2["quote"] and ev2["quote"] not in quotes:
                target["evidence"].append(ev2)

    for e in resume.get("domain_contexts", []):
        add_entry("resume", e)
    for e in convo.get("domain_contexts", []):
        add_entry("conversation", e)

    out = []
    for v in merged.values():
        v["evidence"] = v["evidence"][:3]
        out.append(v)

    return {"candidate_id": resume.get("candidate_id") or convo.get("candidate_id") or "", "domain_contexts": out}
