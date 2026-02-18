from agents.summarization.resume.skill_agent import ResumeSkillAgent
from agents.summarization.conversation.skill_agent import ConversationSkillAgent
from agents.summarization.merger import merge_extracted
from agents.summarization.skill_tools.analyze_dimensions import AnalyzeAgent
from agents.summarization.skill_tools import score_skills
from utils.llm_service import LLMService


def skill_node(state):
    interview = state["interview_session"]
    candidate_id = interview.candidate_id

    answers = state["answers"]

    resume_agent = ResumeSkillAgent()
    convo_agent = ConversationSkillAgent()
    analyzer = AnalyzeAgent()

    resume_result = resume_agent.analyze(resume_text=state.get("resume_text", ""), candidate_id=candidate_id)
    convo_result = convo_agent.analyze(answers=answers, candidate_id=candidate_id)

    merged = merge_extracted.merge_skills(resume_result, convo_result)
    analyzed = analyzer.analyze(merged)

    llm = LLMService.fast()
    scored_skills = []

    for s in analyzed.get("skills", []):
        scores = score_skills._score_with_llm(
            llm,
            s["name"],
            s.get("evidence", []),
        )
        scored_skills.append({**s, **scores})

    return {
        **state,
        "skills": scored_skills,
        "behavior_observations": analyzed.get("behavior_observations", []),
    }
