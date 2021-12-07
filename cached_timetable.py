import asyncio
import datetime
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import netschoolapi
import pytz
import vkbottle
from PIL import Image as PILImageModule

from image_cropper import ImageCropper

YEKATERINBURG_TIMEZONE = pytz.timezone("Asia/Yekaterinburg")

SATURDAY = 5


class TimetableNotFound(Exception):
    pass


def now():
    return datetime.datetime.now(tz=YEKATERINBURG_TIMEZONE)


def today():
    return now().date()


def get_next_school_day_date():
    today_ = today()
    return today_ + datetime.timedelta(
        # Skipping the sunday
        days=2 if today_.weekday() == SATURDAY else 1
    )


TIMETABLE_ANNOUNCEMENT_TITLE_REGEX = re.compile(
    r"расписание для 5-11 классов на (\d+).+", flags=re.IGNORECASE
)


@dataclass
class Timetable:
    attachment_string: str
    date: datetime.date


class TimetableCacher:

    def __init__(
            self, netschoolapi_client: netschoolapi.NetSchoolAPI,
            vk_client: vkbottle.Bot):
        self._netschoolapi_client = netschoolapi_client
        self._vk_client = vk_client
        self._timetable_getting_lock = asyncio.Lock()
        self._cached_timetable: Optional[Timetable] = None

    async def get_from_cache_or_download(
            self, date: datetime.date = None):
        if date is None:
            date = today()
        if self._cache_is_valid(date):
            return self._cached_timetable
        try:
            return await self._download_and_cache_timetable(date)
        except TimetableNotFound:
            if self._cached_timetable is None:
                raise TimetableNotFound
            return self._cached_timetable

    async def download(self, date: datetime.date = None):
        return await self._download_and_cache_timetable(
            date or get_next_school_day_date()
        )

    def _cache_is_valid(self, expected_date: datetime.date):
        return (
            self._cached_timetable is not None
            and self._cached_timetable.date == expected_date
        )

    async def _download_and_cache_timetable(self, date: datetime.date):
        async with self._timetable_getting_lock:
            timetable = await self._download_timetable(date)
            attachment_string = (
                await vkbottle.PhotoMessageUploader(
                    api=self._vk_client.api
                ).upload(timetable)
            )
            timetable = Timetable(
                attachment_string=attachment_string,
                date=date
            )
            self._cached_timetable = timetable
            return timetable

    async def _download_timetable(self, date: datetime.date) -> BytesIO:
        next_day_number = date.day
        for announcement in (
            await self._netschoolapi_client.announcements()
        ):
            for attachment in announcement.attachments:
                match = TIMETABLE_ANNOUNCEMENT_TITLE_REGEX.fullmatch(
                    attachment.name
                )
                if match:
                    if int(match.group(1)) == next_day_number:
                        file_buffer = await (
                            self._netschoolapi_client
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
                            format="jpeg" if format_ == "jpg" else format_
                        )
                        return file_buffer
                    raise TimetableNotFound
        raise TimetableNotFound
