import json
from dataclasses import dataclass


@dataclass
class Config:
    vk_bot_token: str
    sgo_username: str
    sgo_password: str
    school_name: str
    class_chat_peer_id: int
    timetable_checking_delay_in_seconds: int

    @classmethod
    def make_from_file(cls, filename: str, encoding="utf-8"):
        instance = cls(**json.load(open(filename, encoding=encoding)))
        return instance
