class ChunkingService:
    def __init__(self):
        pass

    def split(self, content: str) -> list[str]:
        # Split text into paragraph chunks separated by blank lines, then slice long paragraphs with overlap
        normalized = content.replace("\r\n", "\n")
        chunks = []
        
        for line in normalized.split("\n"):
            paragraph = line.strip()
            if not paragraph:
                continue

            chunks.append(paragraph)
        
        return chunks
