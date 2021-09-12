import asyncio
import datetime
import random
import re
import traceback
from dataclasses import dataclass
from io import BytesIO
from typing import Optional, Tuple

import pytz
import vkbottle
import vkbottle.bot
import vkbottle.dispatch.rules.bot
from PIL import Image as PILImageModule

from config import Config
from netschoolapi import NetSchoolAPI

HELP_MESSAGE = (
    "/помощь (или \"/команды\") - это сообщение\n"
    "/расписание - последнее расписание на сегодня из сетевого города"
)

TIMETABLE_ANNOUNCEMENT_TITLE_REGEX = re.compile(
    r"расписание для 5-11 классов на (\d+).+", flags=re.IGNORECASE
)


class RectangleCoordinates:

    def __init__(
            self, top_left_corner: Tuple[int, int],
            lower_right_corner: Tuple[int, int]):
        self.box = top_left_corner + lower_right_corner


TIMETABLE_CORNER_COORDINATES = RectangleCoordinates(
    top_left_corner=(0, 513),
    lower_right_corner=(186, 668)
)


@dataclass
class CachedTimetableInfo:
    month_day_number: int
    attachment_string: str


class TimetableForTodayIsntFound(Exception):
    pass


class PeerCheckerRule(vkbottle.dispatch.rules.bot.ABCMessageRule):

    def __init__(self, peer_id: int):
        self.peer_id = peer_id

    async def check(self, message: vkbottle.bot.Message) -> bool:
        return self.peer_id == message.peer_id


def _future_done_callback(future: asyncio.Future):
    exception = future.exception()
    if exception:
        # noinspection PyBroadException
        try:
            raise exception
        except Exception:
            traceback.print_exc()


MINIMUM_TIMETABLE_SENDING_HOUR_IN_UTC = 10
NIGHT_HOUR_IN_UTC = 18

YEKATERINBURG_TIMEZONE = pytz.timezone("Asia/Yekaterinburg")

SATURDAY = 6


def today():
    return datetime.datetime.now(YEKATERINBURG_TIMEZONE).date()


def get_timedelta_from_now_to(day, hour, today_=None, now=None):
    utcnow = now or datetime.datetime.now()
    return datetime.datetime.combine(
        (
            today_ or today() + datetime.timedelta(
                days=day if utcnow.hour < hour else day + 1
            )
        ),
        datetime.time(hour=hour)
    ) - utcnow


async def sleep_to_the_end_of_the_next_school_day():
    await asyncio.sleep(get_timedelta_from_now_to(
        # Skipping the next day if current day is saturday because
        # there are no classes on sunday
        day=1 if today().weekday() == SATURDAY else 0,
        hour=MINIMUM_TIMETABLE_SENDING_HOUR_IN_UTC
    ).total_seconds())


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
        self.cached_timetable_info: Optional[CachedTimetableInfo] = None
        self.timetable_getting_lock = asyncio.Lock()

    async def run(self):
        asyncio.create_task(
            self.check_timetable_periodically_and_send_it()
        ).add_done_callback(
            _future_done_callback
        )
        await self.vk_client.run_polling()

    async def get_timetable_attachment_string(self) -> str:
        async with self.timetable_getting_lock:
            next_day_number = (today() + datetime.timedelta(days=1)).day
            if (
                self.cached_timetable_info
                and (
                    self.cached_timetable_info.month_day_number
                    == next_day_number
                )
            ):
                return self.cached_timetable_info.attachment_string
            for announcement in await self.netschoolapi_client.announcements():
                for attachment in announcement.attachments:
                    match = TIMETABLE_ANNOUNCEMENT_TITLE_REGEX.fullmatch(
                        attachment.name
                    )
                    if match:
                        if int(match.group(1)) == next_day_number:
                            file_buffer = BytesIO()
                            await self.netschoolapi_client.download_attachment(
                                attachment, path_or_file=file_buffer
                            )
                            timetable = PILImageModule.open(
                                file_buffer
                            ).crop(TIMETABLE_CORNER_COORDINATES.box)
                            file_buffer = BytesIO()
                            timetable.save(
                                file_buffer,
                                format=attachment.name.split(".")[-1]
                            )
                            attachment_string = (
                                await vkbottle.PhotoMessageUploader(
                                    api=self.vk_client.api
                                ).upload(file_buffer)
                            )
                            self.cached_timetable_info = (
                                CachedTimetableInfo(
                                    month_day_number=next_day_number,
                                    attachment_string=attachment_string
                                )
                            )
                            return attachment_string
                        raise TimetableForTodayIsntFound
            raise TimetableForTodayIsntFound

    async def check_timetable_periodically_and_send_it(self):
        while True:
            try:
                await self.send_timetable_to_peer_id(
                    self.config.class_chat_peer_id
                )
            except TimetableForTodayIsntFound:
                if datetime.datetime.utcnow().hour > NIGHT_HOUR_IN_UTC:
                    await sleep_to_the_end_of_the_next_school_day()
                else:
                    await asyncio.sleep(
                        self.config.timetable_checking_delay_in_seconds
                    )
            else:
                await sleep_to_the_end_of_the_next_school_day()

    async def send_timetable_to_peer_id(self, peer_id: int):
        timetable_attachment_string = (
            await self.get_timetable_attachment_string()
        )
        await self.vk_client.api.messages.send(
            attachment=timetable_attachment_string,
            peer_id=peer_id,
            random_id=random.randint(-1_000_000, 1_000_000)
        )

    async def handle_message(self, message: vkbottle.bot.Message):
        if message.text.startswith("/"):
            text = message.text[1:].casefold()
            if text == "расписание":
                try:
                    await self.send_timetable_to_peer_id(message.peer_id)
                except TimetableForTodayIsntFound:
                    await message.answer("Расписания пока нет!")
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
