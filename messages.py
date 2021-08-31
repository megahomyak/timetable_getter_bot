import random
from typing import AsyncGenerator, Set

from simple_avk import SimpleAVK

from abstract_messages import AbstractMessage, AbstractMessageListener


class Message(AbstractMessage):

    def __init__(self, text: str, peer_id: int, vk: SimpleAVK):
        self._text = text
        self.vk = vk
        self.peer_id = peer_id

    @property
    def text(self) -> str:
        return self._text

    async def reply(self, text: str) -> None:
        await self.vk.call_method(
            "messages.send", {
                "message": text,
                "random_id": random.randint(-1_000_000, 1_000_000),
                "peer_id": self.peer_id
            }
        )


class MessageListenerForWhitelistedChats(AbstractMessageListener):

    def __init__(
            self, vk: SimpleAVK, whitelisted_chat_peer_ids: Set[int],
            debug=False):
        self.vk = vk
        self.whitelisted_chat_peer_ids = whitelisted_chat_peer_ids
        self.debug = debug

    async def listen(self) -> AsyncGenerator[AbstractMessage, None]:
        async for event in self.vk.listen():
            if event["type"] == "message_new":
                message = event["object"]["message"]
                text = message["text"]
                peer_id = message["peer_id"]
                if self.debug:
                    print(f"{peer_id=}, {text=}")
                if peer_id in self.whitelisted_chat_peer_ids:
                    yield Message(text, peer_id, self.vk)
