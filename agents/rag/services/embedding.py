from config import settings
import requests


class EmbeddingService:
    def __init__(self):
        self.model = settings.EMBEDDING_MODEL
        self.api_key = settings.OPENROUTER_API_KEY

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        return self._call_openrouter_embedding_api(chunks)

    def embed_query(self, query: str) -> list[float]:
        result = self._call_openrouter_embedding_api(query)
        return result[0] if result else []

    def _call_openrouter_embedding_api(self, inputs) -> list[list[float]]:
        model = self.model or "openai/text-embedding-3-small"

        response = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": inputs
            }
        )

        data = response.json()
        return [item["embedding"] for item in data["data"]]
