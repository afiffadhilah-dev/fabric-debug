from agents.summarization.conversation.behavior_agent import ConversationBehaviorAgent


def extract_behaviors_from_conversation(answers, candidate_id: str):
    """Extract behavior observations from conversation using the dedicated ConversationBehaviorAgent."""
    agent = ConversationBehaviorAgent()
    return agent.analyze(answers=answers, candidate_id=candidate_id)
