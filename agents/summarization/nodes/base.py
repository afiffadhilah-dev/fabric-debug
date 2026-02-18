from abc import ABC, abstractmethod
from agents.summarization.state import SummarizationState


class BaseNode(ABC):
    @abstractmethod
    def run(self, state: SummarizationState) -> None:
        """Mutates the shared summarization state"""
        pass
