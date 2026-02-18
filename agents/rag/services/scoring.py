class ScoringService:
    def __init__(self):
        pass

    def rerank(self, results: list[dict]) -> list[dict]:
        """
        Rerank results by grouping candidates and calculating average similarity.
        This eliminates duplicates and returns unique candidates sorted by relevance.
        """
        # Group by candidate_id and collect all similarities
        candidates_map = {}

        for result in results:
            candidate_id = result.get("candidate_id")

            if candidate_id not in candidates_map:
                candidates_map[candidate_id] = {
                    "name": result.get("name"),
                    "chunk_matches": [result.get("chunk_match")],
                    "similarities": [result.get("similarity")],
                    "chunks": result.get("chunks"),
                }
            else:
                candidates_map[candidate_id]["chunk_matches"].append(
                    result.get("chunk_match"))
                candidates_map[candidate_id]["similarities"].append(
                    result.get("similarity"))

        # Calculate average similarity and rank candidates by average similarity
        reranked = []
        for candidate_id, data in candidates_map.items():
            reranked.append({
                "candidate_id": candidate_id,
                "name": data["name"],
                "chunk_matches": data["chunk_matches"],
                "average_similarity": sum(data["similarities"]) / len(data["similarities"]),
                "chunks": data["chunks"]
            })

        # Sort by average similarity (descending)
        reranked.sort(key=lambda x: x["average_similarity"], reverse=True)

        return reranked
