from agents.summarization.resume.behavior_agent import ResumeBehaviorAgent


def extract_behaviors_from_resume(resume_text: str, candidate_id: str):
    """Extract behavior observations from resume using the dedicated ResumeBehaviorAgent."""
    agent = ResumeBehaviorAgent()
    return agent.analyze(resume_text=resume_text, candidate_id=candidate_id)
