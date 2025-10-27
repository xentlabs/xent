from abc import ABC, abstractmethod


class TextGenerator(ABC):
    @abstractmethod
    def generate_text(self, max_length: int | None = None) -> str:
        pass

    @abstractmethod
    def generate_list(sef, prompt: str, length: int) -> list[str]:
        pass
