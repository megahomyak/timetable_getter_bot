import json
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    site_url: str
    vk_group_token: str
    vk_user_token: str
    sgo_username: str
    sgo_password: str
    school_name: str
    timetable_checking_delay_in_seconds: int
    minimum_timetable_sending_hour: int
    maximum_timetable_sending_hour: int
    timetable_weekdays: List[int]
    do_logging: bool
    print_incoming_messages: int
    broadcast_peer_ids: List[int]

    @classmethod
    def make_from_file(cls, filename: str, encoding="utf-8"):
        instance = cls(**json.load(open(filename, encoding=encoding)))
        return instance
