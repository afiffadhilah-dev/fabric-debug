from agents.summarization.conversation.skill_agent import ConversationSkillAgent


def extract_skills_from_conversation(answers, candidate_id: str):
    """Extract skills section from conversation using the dedicated ConversationSkillAgent."""
    agent = ConversationSkillAgent()
    return agent.analyze(answers=answers, candidate_id=candidate_id)
