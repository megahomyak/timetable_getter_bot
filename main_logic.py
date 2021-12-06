import asyncio
import datetime
import random

import vkbottle
import vkbottle.bot
import vkbottle.dispatch.rules.bot
from netschoolapi import NetSchoolAPI

from cached_timetable import (
    TimetableCacher, TimetableNotFound, now, today, Timetable
)
from config import Config

HELP_MESSAGE = (
    "/помощь (или \"/команды\") - это сообщение\n"
    "/расписание - последнее расписание на сегодня из сетевого города"
)


async def wait_until(time: datetime.datetime):
    await asyncio.sleep((time - now()).total_seconds())


class PeerCheckerRule(vkbottle.dispatch.rules.bot.ABCMessageRule):

    def __init__(self, peer_id: int):
        self.peer_id = peer_id

    async def check(self, message: vkbottle.bot.Message) -> bool:
        return self.peer_id == message.peer_id


MINIMUM_TIMETABLE_SENDING_HOUR = 12
NIGHT_HOUR = 22


FRIDAY = 4


async def wait_until_minimum_timetable_sending_hour():
    date = today()
    date += datetime.timedelta(
        # Skipping the saturday because there will be no timetable for sunday on
        # saturday (because we don't have lessons on sunday)
        days=2 if date.weekday() == FRIDAY else 1
    )
    await wait_until(datetime.datetime.combine(
        date, datetime.time(hour=MINIMUM_TIMETABLE_SENDING_HOUR)
    ))


class Bot:

    def __init__(
            self, config: Config, vk_client: vkbottle.Bot,
            netschoolapi_client: NetSchoolAPI):
        # noinspection PyTypeChecker
        # because Set[int] is also applicable for FromPeerRule
        vk_client.on.message(PeerCheckerRule(config.class_chat_peer_id))(
            self.handle_message
        )
        self.vk_client = vk_client
        self.config = config
        self.netschoolapi_client = netschoolapi_client
        self.timetable_cacher = TimetableCacher(netschoolapi_client, vk_client)

    async def run(self):
        asyncio.create_task(self.check_timetable_periodically_and_send_it())
        print("Starting!")
        await self.vk_client.run_polling()

    async def check_timetable_periodically_and_send_it(self):
        while True:
            try:
                timetable = await self.timetable_cacher.download()
            except TimetableNotFound:
                if now().hour > NIGHT_HOUR:
                    await wait_until_minimum_timetable_sending_hour()
                else:
                    await asyncio.sleep(
                        self.config.timetable_checking_delay_in_seconds
                    )
            else:
                await self.send_timetable_to_peer_id(
                    timetable, self.config.class_chat_peer_id
                )
                await wait_until_minimum_timetable_sending_hour()

    async def send_timetable_to_peer_id(
            self, timetable: Timetable, peer_id: int):
        await self.vk_client.api.messages.send(
            attachment=timetable.attachment_string,
            message="Расписание на " + timetable.date.strftime("%d.%m.%Y"),
            peer_id=peer_id,
            random_id=random.randint(-1_000_000, 1_000_000)
        )

    async def handle_message(self, message: vkbottle.bot.Message):
        if message.text.startswith("/"):
            text = message.text[1:].casefold()
            if text == "расписание":
                try:
                    timetable = (
                        await self.timetable_cacher.get_from_cache_or_download()
                    )
                except TimetableNotFound:
                    await message.answer("Расписания пока нет!")
                else:
                    await self.send_timetable_to_peer_id(
                        timetable=timetable,
                        peer_id=message.peer_id
                    )
            elif text in ("помощь", "команды"):
                await message.answer(HELP_MESSAGE)


async def main():
    config = Config.make_from_file("config.json")
    netschoolapi_client = NetSchoolAPI(url="https://sgo.edu-74.ru/")
    await netschoolapi_client.login(
        user_name=config.sgo_username, password=config.sgo_password,
        school=config.school_name
    )
    bot = Bot(
        config=config,
        vk_client=vkbottle.Bot(token=config.vk_bot_token),
        netschoolapi_client=netschoolapi_client
    )
    await bot.run()


asyncio.get_event_loop().run_until_complete(main())
