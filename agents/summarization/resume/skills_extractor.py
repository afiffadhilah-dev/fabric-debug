from agents.summarization.resume.skill_agent import ResumeSkillAgent


def extract_skills_from_resume(resume_text: str, candidate_id: str):
    """Extract skills section from resume using the dedicated ResumeSkillAgent."""
    agent = ResumeSkillAgent()
    return agent.analyze(resume_text=resume_text, candidate_id=candidate_id)
