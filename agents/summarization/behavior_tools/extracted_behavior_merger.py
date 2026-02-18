from agents.summarization.merger.merge_extracted import merge_behaviors


def merge_extracted_behaviors(resume_result: dict, convo_result: dict):
    """Merge behavior observations extracted from resume and conversation.

    Returns a list of merged behavior items.
    """
    return merge_behaviors(resume_result, convo_result)
