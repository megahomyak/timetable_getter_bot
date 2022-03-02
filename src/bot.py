import asyncio
import os
import random
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Sequence, List

import PIL.Image
import httpx
import netschoolapi.schemas
import vkbottle
from netschoolapi import NetSchoolAPI
from vkbottle.bot import Message
from vkbottle_types.objects import MessagesSendUserIdsResponseItem

from src import image_cropper
from src import time_related_things
from src.config import Config
from src.looped_two_ways_iterator import LoopedTwoWaysIterator
from src.timetable_days_cacher import AbstractTimetableDaysCacher, DaysType

TIMETABLE_ANNOUNCEMENT_TITLE_REGEX = re.compile(
    r"расписание для 5-11 классов на (?P<month_day_number>\d+)",
    flags=re.IGNORECASE
)
HTML_TAGS_REGEX = re.compile(r"</?\w+>")

# TODO:
# check for a new timetable EVERY MINUTE until `maximum_timetable_sending_hour`,
# and if some of the timetables was updated, send it with the "[ИЗМЕНЕНИЕ]\n\n"
# sign before it.
# (Now it is implemented that way: if new timetables were found, bot goes
# to a long sleep (this is not a separate abstraction, see line 153))
# Reopen a session for every request


@dataclass
class Timetable:
    announcement_text: str
    attachment: netschoolapi.schemas.Attachment
    is_updated: bool


class Bot:

    def __init__(
            self, config: Config, vk_group_client: vkbottle.Bot,
            vk_group_id: int, vk_user_client: vkbottle.User,
            netschoolapi_client: NetSchoolAPI,
            timetable_days_cacher: AbstractTimetableDaysCacher,
            do_logging: bool):
        self._vk_group_client = vk_group_client
        self._vk_group_id = vk_group_id
        self._vk_user_client = vk_user_client
        self._config = config
        self._netschoolapi_client = netschoolapi_client
        self._timetable_days_cacher = timetable_days_cacher
        self._timetable_downloading_and_days_caching_lock = asyncio.Lock()
        self._do_logging = do_logging

    @classmethod
    async def new(
            cls, config: Config, vk_group_client: vkbottle.Bot,
            vk_user_client: vkbottle.User,
            netschoolapi_client: NetSchoolAPI,
            timetable_days_cacher: AbstractTimetableDaysCacher):
        vk_group_id = -(await vk_group_client.api.groups.get_by_id())[0].id
        bot_instance = cls(
            config=config, vk_group_client=vk_group_client,
            vk_group_id=vk_group_id, vk_user_client=vk_user_client,
            netschoolapi_client=netschoolapi_client,
            timetable_days_cacher=timetable_days_cacher,
            do_logging=config.do_logging
        )
        if config.print_incoming_messages:
            vk_group_client.on.message()(bot_instance._handle_new_message)
            asyncio.create_task(vk_group_client.run_polling())
        return bot_instance

    # noinspection PyMethodMayBeStatic
    async def _handle_new_message(self, message: Message):
        print(f"{message.peer_id=}, {message.text=}")

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
                    if self._do_logging:
                        print(
                            f"Timetables before receiving new timetables: "
                            f"{self._timetable_days_cacher.get_days()}"
                        )
                    timetables = await self._download_new_timetables()
                except httpx.HTTPError:
                    pass
                else:
                    if self._do_logging:
                        print(
                            f"Timetables after receiving new timetables: "
                            f"{self._timetable_days_cacher.get_days()}"
                        )
                    if timetables:
                        await self._send_timetables(timetables)
                        if self._do_logging:
                            now = time_related_things.now()
                            print(f"Sent timetables: {timetables} at {now}")
                    else:
                        if self._do_logging:
                            print("=> no new timetables found")
                await self._netschoolapi_client.logout()
                now = time_related_things.now()
                if now.hour >= self._config.maximum_timetable_sending_hour:
                    break
                elif now.hour < self._config.minimum_timetable_sending_hour:
                    if self._do_logging:
                        print(
                            f"Sleeping to "
                            f"{self._config.minimum_timetable_sending_hour} "
                            f"hour (now is {now})"
                        )
                    future = now.replace(
                        hour=self._config.minimum_timetable_sending_hour,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                    await asyncio.sleep(
                        (future - now).total_seconds()
                    )
                else:
                    if self._do_logging:
                        print(f"Short sleep (now is {now})")
                    await asyncio.sleep(
                        self._config.timetable_checking_delay_in_seconds
                    )
            future = (
                time_related_things.get_next_timetable_search_beginning_date(
                    next_timetable_weekday=next_timetable_weekday,
                    sleep_end_hour=self._config.minimum_timetable_sending_hour,
                    initial_date=now
                )
            )
            if self._do_logging:
                print(f"Long sleep until {future} (now is {now})")
            await asyncio.sleep((future - now).total_seconds())

    async def _send_timetables(self, timetables: Sequence[Timetable]):
        for timetable_number, timetable in enumerate(timetables, start=1):
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
                    api=self._vk_user_client.api
                ).upload(cropped_timetable_image_buffer)
            )
            message = post_title
            if timetable.announcement_text:
                message += (
                    f"\n\nТекст объявления: {timetable.announcement_text}"
                )
            if timetable.is_updated:
                message = "[ОБНОВЛЕНО]\n\n" + message
            post = await self._vk_user_client.api.wall.post(
                owner_id=self._vk_group_id,
                from_group=True,
                message=message,
                attachments=[vk_attachment_string]
            )
            # noinspection PyTypeChecker
            messages: List[MessagesSendUserIdsResponseItem] = (
                await self._vk_group_client.api.messages.send(
                    attachment=f"wall{self._vk_group_id}_{post.post_id}",
                    random_id=random.randint(-1_000_000, 1_000_000),
                    peer_ids=self._config.broadcast_peer_ids
                )
            )
            if timetable_number == 1:
                chats = await (
                    self._vk_group_client.api
                    .messages.get_conversations_by_id(
                        peer_ids=self._config.broadcast_peer_ids
                    )
                )
                allowed_peers = set()
                for chat in chats.items:
                    if (
                        chat.chat_settings.pinned_message is None
                        or (
                            chat.chat_settings.pinned_message.from_id
                            == self._vk_group_id
                        )
                    ):
                        allowed_peers.add(chat.peer.id)
                for message in messages:
                    if message.peer_id in allowed_peers:
                        await self._vk_group_client.api.messages.pin(
                            peer_id=message.peer_id,
                            conversation_message_id=(
                                message.conversation_message_id
                            )
                        )

    async def _download_new_timetables(self) -> Sequence[Timetable]:
        """
        Get all the timetables. If some of them are not in self._timetable_days,
        it means that they are new and they should be added to the result. After
        processing all of the timetables, set self._timetable_days to
        new_timetable_days
        """
        async with self._timetable_downloading_and_days_caching_lock:
            timetables = []
            old_timetable_days = self._timetable_days_cacher.get_days()
            new_timetable_days: DaysType = {}
            for announcement in await self._netschoolapi_client.announcements():
                for attachment in announcement.attachments:
                    match = TIMETABLE_ANNOUNCEMENT_TITLE_REGEX.match(
                        attachment.name
                    )
                    if match:
                        # We got a timetable!
                        timetable_day = int(match.group("month_day_number"))
                        new_timetable_days[timetable_day] = (
                            announcement.post_date
                        )
                        known_announcement_post_date = (
                            old_timetable_days.get(timetable_day)
                        )
                        if (
                            known_announcement_post_date
                            != announcement.post_date
                        ):
                            timetables.append(Timetable(
                                announcement_text=HTML_TAGS_REGEX.sub(
                                    "", announcement.content
                                ),
                                attachment=attachment,
                                is_updated=bool(known_announcement_post_date)
                            ))
            self._timetable_days_cacher.set_days(new_timetable_days)
            return timetables
