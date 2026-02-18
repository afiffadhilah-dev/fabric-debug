from repositories.candidate_profile_data_repository import CandidateProfileDataRepository


class LoadCandidateNode:
    def __init__(self, db_session):
        self.db = db_session

    def run(self, state):
        interview = state["interview_session"]
        candidate_id = interview.candidate_id

        repo = CandidateProfileDataRepository(self.db)
        profile = repo.get_candidate_profile(candidate_id)
        state["candidate_profile"] = profile

        return state
