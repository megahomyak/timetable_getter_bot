import asyncio
import datetime
import random
import re
import traceback
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import pytz
import vkbottle
import vkbottle.bot
import vkbottle.dispatch.rules.bot
from PIL import Image as PILImageModule
from netschoolapi import NetSchoolAPI

from config import Config
from image_cropper import ImageCropper

HELP_MESSAGE = (
    "/помощь (или \"/команды\") - это сообщение\n"
    "/расписание - последнее расписание на сегодня из сетевого города"
)

TIMETABLE_ANNOUNCEMENT_TITLE_REGEX = re.compile(
    r"расписание для 5-11 классов на (\d+).+", flags=re.IGNORECASE
)


@dataclass
class CachedTimetableInfo:
    month_day_number: int
    attachment_string: str
    date: datetime.date


class TimetableForTomorrowIsntFound(Exception):
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


MINIMUM_TIMETABLE_SENDING_HOUR = 12
NIGHT_HOUR = 22

YEKATERINBURG_TIMEZONE = pytz.timezone("Asia/Yekaterinburg")

SATURDAY = 5


def now():
    return datetime.datetime.now(tz=YEKATERINBURG_TIMEZONE)


def today():
    return now().date()


def get_timedelta_from_now_to(additional_days_amount, hour, now_=None):
    now_ = now_ or now()
    return datetime.datetime.combine(
        (
            now_.date() + datetime.timedelta(
                days=(
                    additional_days_amount
                    if now_.hour < hour else
                    additional_days_amount + 1
                )
            )
        ),
        datetime.time(hour=hour, tzinfo=YEKATERINBURG_TIMEZONE),
        tzinfo=YEKATERINBURG_TIMEZONE
    ) - now_


async def sleep_to_the_end_of_the_next_school_day(additional_days_amount):
    await asyncio.sleep(get_timedelta_from_now_to(
        additional_days_amount=additional_days_amount,
        hour=MINIMUM_TIMETABLE_SENDING_HOUR
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

    async def update_timetable(self, ignore_cached: bool):
        async with self.timetable_getting_lock:
            today_ = today()
            timetable_date = today_ + datetime.timedelta(
                # Skipping the sunday
                days=2 if today_.weekday() == SATURDAY else 1
            )
            next_day_number = timetable_date.day
            if (
                ignore_cached
                or not self.cached_timetable_info
                or (
                    self.cached_timetable_info.month_day_number
                    != next_day_number
                )
            ):
                for announcement in (
                    await self.netschoolapi_client.announcements()
                ):
                    for attachment in announcement.attachments:
                        match = TIMETABLE_ANNOUNCEMENT_TITLE_REGEX.fullmatch(
                            attachment.name
                        )
                        if match:
                            if int(match.group(1)) == next_day_number:
                                file_buffer = (
                                    await self.netschoolapi_client
                                    .download_attachment_as_bytes(
                                        attachment
                                    )
                                )
                                image_cropper = ImageCropper(
                                    PILImageModule.open(file_buffer)
                                )
                                file_buffer = BytesIO()
                                format_ = attachment.name.split(".")[-1]
                                image_cropper.crop().save(
                                    file_buffer,
                                    format=(
                                        "jpeg" if format_ == "jpg" else format_
                                    )
                                )
                                attachment_string = (
                                    await vkbottle.PhotoMessageUploader(
                                        api=self.vk_client.api
                                    ).upload(file_buffer)
                                )
                                self.cached_timetable_info = (
                                    CachedTimetableInfo(
                                        month_day_number=next_day_number,
                                        attachment_string=attachment_string,
                                        date=timetable_date
                                    )
                                )
                                return
                            elif ignore_cached:
                                raise TimetableForTomorrowIsntFound

    async def check_timetable_periodically_and_send_it(self):
        while True:
            try:
                await self.update_timetable_and_send_it_to_peer_id(
                    self.config.class_chat_peer_id, ignore_cached=True
                )
            except TimetableForTomorrowIsntFound:
                if now().hour > NIGHT_HOUR:
                    await sleep_to_the_end_of_the_next_school_day(
                        additional_days_amount=0
                    )
                else:
                    await asyncio.sleep(
                        self.config.timetable_checking_delay_in_seconds
                    )
            else:
                await sleep_to_the_end_of_the_next_school_day(
                    additional_days_amount=(
                        1 if today().weekday() == SATURDAY else 0
                    )
                )

    async def update_timetable_and_send_it_to_peer_id(
            self, peer_id: int, ignore_cached: bool):
        await self.update_timetable(ignore_cached)
        await self.send_timetable_to_peer_id(peer_id)

    async def send_timetable_to_peer_id(self, peer_id: int):
        await self.vk_client.api.messages.send(
            attachment=self.cached_timetable_info.attachment_string,
            message=(
                "Расписание на "
                + self.cached_timetable_info.date.strftime("%d.%m.%Y")
            ),
            peer_id=peer_id,
            random_id=random.randint(-1_000_000, 1_000_000)
        )

    async def handle_message(self, message: vkbottle.bot.Message):
        if message.text.startswith("/"):
            text = message.text[1:].casefold()
            if text == "расписание":
                try:
                    await self.update_timetable_and_send_it_to_peer_id(
                        message.peer_id, ignore_cached=False
                    )
                except TimetableForTomorrowIsntFound:
                    if self.cached_timetable_info:
                        await self.send_timetable_to_peer_id(message.peer_id)
                    else:
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
