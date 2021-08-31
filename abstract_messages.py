from abc import ABC, abstractmethod
from typing import AsyncGenerator


class AbstractMessage(ABC):

    @property
    @abstractmethod
    def text(self) -> str:
        pass

    @abstractmethod
    async def reply(self, text: str) -> None:
        pass


class AbstractMessageListener(ABC):

    @abstractmethod
    async def listen(self) -> AsyncGenerator[AbstractMessage, None]:
        yield
