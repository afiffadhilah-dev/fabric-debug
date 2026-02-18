class NormalizeService:
    def __init__(self):
        pass

    def normalize_text(self, text: str) -> str:
        cleaned_lines = self._clean_line(text)
        return self._merge_short_lines(cleaned_lines)

    def _clean_line(self, text: str) -> list[str]:
        import re

        normalized = text.replace("\r\n", "\n")
        cleaned_lines: list[str] = []

        for raw_line in normalized.split("\n"):
            stripped = self._clean_noise(raw_line)
            if stripped:
                cleaned_lines.append(stripped)

        return cleaned_lines

    def _clean_noise(self, text: str) -> list[str]:
        import re
        stripped = re.sub(r"[^A-Za-z0-9\s,\.\-:;!?()'\"/]", " ", text)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        return stripped

    def _merge_short_lines(self, cleaned_lines: list[str]) -> str:
        merged: list[str] = []

        for line in cleaned_lines:
            words = line.split()
            if merged and 2 <= len(words) <= 5:
                # Lowercase the first word when merging if the previous part is mid-sentence
                if merged[-1] and merged[-1][-1] not in ".!?":
                    words[0] = words[0].lower()
                merged[-1] = f"{merged[-1]} {' '.join(words)}".strip()
            else:
                merged.append(line)

        return "\n".join(merged)