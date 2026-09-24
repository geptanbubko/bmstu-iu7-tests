"""Абстракция ввода-вывода: UI не зависит от print/input (DIP)."""
from abc import ABC, abstractmethod


class IUserIO(ABC):
    @abstractmethod
    def write(self, text: str) -> None:
        pass

    @abstractmethod
    def read(self, prompt: str) -> str:
        pass


class ConsoleIO(IUserIO):
    def write(self, text: str) -> None:
        print(text)

    def read(self, prompt: str) -> str:
        return input(prompt)
