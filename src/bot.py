import asyncio
import os
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

import PIL.Image
import httpx
import netschoolapi.schemas
import vkbottle
from netschoolapi import NetSchoolAPI

from src import image_cropper
from src import time_related_things
from src.config import Config
from src.looped_two_ways_iterator import LoopedTwoWaysIterator
from src.timetable_days_cacher import AbstractTimetableDaysCacher

TIMETABLE_ANNOUNCEMENT_TITLE_REGEX = re.compile(
    r"расписание для 5-11 классов на (?P<month_day_number>\d+)",
    flags=re.IGNORECASE
)


@dataclass
class Timetable:
    attachment: netschoolapi.schemas.Attachment


class Bot:

    def __init__(
            self, config: Config, vk_group_client: vkbottle.Bot,
            vk_group_id: int, vk_user_client: vkbottle.User,
            netschoolapi_client: NetSchoolAPI,
            timetable_days_cacher: AbstractTimetableDaysCacher):
        self._vk_group_client = vk_group_client
        self._vk_group_id = vk_group_id
        self._vk_group_client = vk_user_client
        self._config = config
        self._netschoolapi_client = netschoolapi_client
        self._timetable_days_cacher = timetable_days_cacher
        self._timetable_downloading_and_days_caching_lock = asyncio.Lock()

    @classmethod
    async def new(
            cls, config: Config, vk_group_client: vkbottle.Bot,
            vk_user_client: vkbottle.User,
            netschoolapi_client: NetSchoolAPI,
            timetable_days_cacher: AbstractTimetableDaysCacher):
        vk_group_id = -(await vk_group_client.api.groups.get_by_id())[0].id
        return cls(
            config=config, vk_group_client=vk_group_client,
            vk_group_id=vk_group_id, vk_user_client=vk_user_client,
            netschoolapi_client=netschoolapi_client,
            timetable_days_cacher=timetable_days_cacher
        )

    async def run(self):
        print("Starting!")
        timetable_weekdays_iterator = LoopedTwoWaysIterator(
            self._config.timetable_weekdays
        )
        time_related_things.roll_weekdays_iterator(
            timetable_weekdays_iterator,
            current_weekday=time_related_things.now().weekday()
        )
        for next_timetable_weekday in timetable_weekdays_iterator:
            while True:
                # SLEEP SCHEDULE:
                # Sleep until the next timetable day if it is late.
                # Sleep until the next timetable day if timetables were fetched.
                # Sleep for timetable checking delay otherwise.
                try:
                    timetables = await self._download_new_timetables()
                except httpx.HTTPError:
                    pass
                else:
                    await self._send_timetables(timetables)
                    now = time_related_things.now()
                    break
                now = time_related_things.now()
                if now.hour >= self._config.maximum_timetable_sending_hour:
                    break
                else:
                    await asyncio.sleep(
                        self._config.timetable_checking_delay_in_seconds
                    )
            await time_related_things.sleep_to_next_timetable_day(
                next_timetable_weekday=next_timetable_weekday,
                sleep_end_hour=(
                    self._config.minimum_timetable_sending_hour
                ),
                initial_datetime=now
            )

    async def _send_timetables(self, timetables: Iterable[Timetable]):
        for timetable in timetables:
            post_title, file_extension = (
                os.path.splitext(timetable.attachment.name)
            )
            image_format = (
                file_extension[1:]  # Removing the dot at the beginning
            )
            if image_format == "jpg":
                image_format = "jpeg"
            timetable_image_as_bytes = await (
                self._netschoolapi_client.download_attachment_as_bytes(
                    attachment=timetable.attachment
                )
            )
            cropped_timetable_image_buffer = BytesIO()
            image_cropper.crop_white_margins(
                PIL.Image.open(timetable_image_as_bytes).convert("RGB")
            ).save(cropped_timetable_image_buffer, format=image_format)
            vk_attachment_string: str = (
                await vkbottle.PhotoWallUploader(
                    api=self._vk_group_client.api
                ).upload(cropped_timetable_image_buffer)
            )
            await self._vk_group_client.api.wall.post(
                owner_id=self._vk_group_id,
                from_group=True,
                message=post_title,
                attachments=[vk_attachment_string]
            )

    async def _download_new_timetables(self) -> Iterable[Timetable]:
        """
        Get all the timetables. If some of them are not in self._timetable_days,
        it means that they are new and they should be added to the result. After
        processing all of the timetables, set self._timetable_days to
        new_timetable_days
        """
        async with self._timetable_downloading_and_days_caching_lock:
            timetables = []
            old_timetable_days = self._timetable_days_cacher.get_days()
            new_timetable_days = set()
            for announcement in await self._netschoolapi_client.announcements():
                for attachment in announcement.attachments:
                    match = TIMETABLE_ANNOUNCEMENT_TITLE_REGEX.match(
                        attachment.name
                    )
                    if match:
                        # We got a timetable!
                        timetable_day = int(match.group("month_day_number"))
                        new_timetable_days.add(timetable_day)
                        if timetable_day not in old_timetable_days:
                            timetables.append(Timetable(attachment))
            self._timetable_days_cacher.set_days(new_timetable_days)
            return timetables
