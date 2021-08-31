import json
from dataclasses import dataclass
from typing import Set


@dataclass
class Config:
    vk_bot_token: str
    vk_bot_group_id: int
    sgo_username: str
    sgo_password: str
    school_name: str
    whitelisted_chat_peer_ids: Set[int]

    @classmethod
    def make_from_file(cls, filename: str, encoding="utf-8"):
        instance = cls(**json.load(open(filename, encoding=encoding)))
        instance.whitelisted_chat_peer_ids = set(
            instance.whitelisted_chat_peer_ids
        )
        return instance
