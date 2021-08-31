import asyncio
import re
from typing import NoReturn

import aiohttp
from simple_avk import SimpleAVK

import command_regexes
from abstract_messages import AbstractMessageListener, AbstractMessage
from abstract_timetable_getter import AbstractTimetableGetter
from config import Config
from messages import MessageListenerForWhitelistedChats
from netschoolapi import NetSchoolAPI
from timetable import Timetable
from timetable_getter import TimetableGetter


class Bot:

    def __init__(
            self, message_listener: AbstractMessageListener,
            timetable_getter: AbstractTimetableGetter):
        self.message_listener = message_listener
        self.timetable_getter = timetable_getter
        self.handlers = (
            (command_regexes.GET_HOMEWORK_REGEX, self.send_homework),
            (command_regexes.GET_TIMETABLE_REGEX, self.send_timetable)
        )

    async def send_homework(self, message: AbstractMessage, match: re.Match):
        await message.reply(
            (
                await self.get_timetable(
                    day_bias=int(match.group(1) or 0)
                )
            ).get_homework_as_string()
        )

    async def send_timetable(self, message: AbstractMessage, match: re.Match):
        await message.reply(
            (
                await self.get_timetable(
                    day_bias=int(match.group(1) or 0)
                )
            ).get_timetable_as_string()
        )

    async def process_message(self, message: AbstractMessage):
        if message.text in ("/помощь", "/команды"):
            await message.reply(command_regexes.HELP_MESSAGE)
        for regex, handler in self.handlers:
            match = regex.fullmatch(message.text)
            if match:
                await handler(message, match)

    async def run(self) -> NoReturn:
        async for message in self.message_listener.listen():
            asyncio.create_task(self.process_message(message))

    async def get_timetable(self, day_bias: int = 0) -> Timetable:
        return await self.timetable_getter.get_timetable(day_bias)


async def make_bot(
        aiohttp_session: aiohttp.ClientSession, config_filename: str,
        debug=False) -> Bot:
    config = Config.make_from_file(config_filename)
    netschoolapi = NetSchoolAPI(url="https://sgo.edu-74.ru/")
    await netschoolapi.login(
        user_name=config.sgo_username,
        password=config.sgo_password,
        school=config.school_name
    )
    vk = SimpleAVK(
        aiohttp_session=aiohttp_session,
        token=config.vk_bot_token,
        group_id=config.vk_bot_group_id
    )
    return Bot(
        MessageListenerForWhitelistedChats(
            vk, config.whitelisted_chat_peer_ids, debug=debug
        ),
        TimetableGetter(netschoolapi)
    )
