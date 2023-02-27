import asyncio
from dataclasses import dataclass
from io import BytesIO
import json
import random
from typing import Dict, List, Set
import lxml.html
import html
from netschoolapi import netschoolapi
import vkbottle
import loguru
import vkbottle.bot
import sys
import re
import datetime
from logging import Logger
import os
from margincropper import crop_margins, ContentNotFound
import PIL.Image
from vkbottle_types.objects import MessagesSendUserIdsResponseItem

@dataclass
class Config:
    vk_group_token: str
    vk_group_id: int
    vk_user_token: str
    sgo_url: str
    sgo_username: str
    sgo_password: str
    sgo_school_name: str
    timetable_checking_delay_in_seconds: int
    log_level: str

@dataclass
class Timetable:
    announcement_text: str
    attachment: netschoolapi.schemas.Attachment
    is_updated: bool

with open("data/config.json") as f:
    config = Config(**json.load(f))

logger = Logger("TGB")
logger.setLevel(config.log_level)

def open_or(path, alternative):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return alternative

Day = int
Time = float
TimetableTimes = Dict[Day, Time]

BROADCAST_PEER_IDS_PATH = "data/broadcast_peer_ids.txt"
TIMETABLE_TIMES_PATH = "data/timetable_days.txt"

broadcast_peer_ids: Set[int] = set(
    int(i) for i in
    open_or(BROADCAST_PEER_IDS_PATH, "").strip().split()
)

TIMETABLE_NAME_REGEX = re.compile(r"Распис\w+ (?!звон).*кла\D*(?P<day>\d+)", re.IGNORECASE)

def remove_html_tags(string):
    if string:
        string = str(lxml.html.fromstring(string).text_content())
        string = html.unescape(string)
    return string

def save_broadcast_peer_ids():
    with open(BROADCAST_PEER_IDS_PATH, "w") as f:
        f.write("\n".join(str(i) for i in broadcast_peer_ids))

async def handle_new_message(message: vkbottle.bot.Message):
    if message.text == "/подключить":
        broadcast_peer_ids.add(message.peer_id)
        await message.reply("Рассылка подключена!")
        save_broadcast_peer_ids()
    elif message.text == "/отключить":
        broadcast_peer_ids.remove(message.peer_id)
        await message.reply("Рассылка отключена!")
        save_broadcast_peer_ids()

netschoolapi_client = netschoolapi.NetSchoolAPI(config.sgo_url)
vk_group_client = vkbottle.Bot(token=config.vk_group_token)
vk_user_client = vkbottle.User(token=config.vk_user_token)

async def run():
    await netschoolapi_client.login(
        config.sgo_username, config.sgo_password, config.sgo_school_name
    )
    old_timetable_times: TimetableTimes = {}
    for line in open_or(TIMETABLE_TIMES_PATH, "").strip().split():
        day, time_ = line.split(":")
        old_timetable_times[int(day)] = float(time_)
    logger.info("Starting!")
    while True:
        logger.debug(f"Timetables times before receiving new timetables (at {datetime.datetime.now()}): {old_timetable_times}")
        new_timetable_times: TimetableTimes = {}
        new_timetables: List[Timetable] = []
        for announcement in await netschoolapi_client.announcements():
            for attachment in announcement.attachments:
                match_ = TIMETABLE_NAME_REGEX.match(attachment.name)
                if match_ is not None:
                    day = int(match_.group("day"))
                    new_timetable_times[day] = announcement.post_date.timestamp()
                    old_time = old_timetable_times.get(day)
                    if old_time != announcement.post_date:
                        new_timetables.append(Timetable(
                            announcement_text=remove_html_tags(announcement.content),
                            attachment=attachment,
                            is_updated=bool(old_time)
                        ))
        old_timetable_times = new_timetable_times
        with open(TIMETABLE_TIMES_PATH, "w") as f:
            f.write("\n".join(
                ":".join((str(day), str(time)))
                for day, time in new_timetable_times.items()
            ))
        logger.debug(f"Timetables times after receiving new timetables (at {datetime.datetime.now()}): {new_timetable_times}")
        if new_timetables:
            logger.debug(f"Sending the following timetables (at {datetime.datetime.now()}): {new_timetables}")
        else:
            logger.debug(f"No new timetables found (at {datetime.datetime.now()})")
        for timetable in new_timetables:
            post_title, image_format = os.path.splitext(timetable.attachment.name)
            if image_format == "jpg":
                image_format = "jpeg"
            image = BytesIO()
            await netschoolapi_client.download_attachment(
                attachment_id=timetable.attachment.id,
                buffer=image,
            )
            try:
                crop_margins(
                    PIL.Image.open(image).convert("RGB"),
                    margin_color=(0, 0, 0),
                    max_margin_color_difference=20,
                ).save(image, format=image_format)
            except ContentNotFound:
                pass
            vk_attachment_string: str = await vkbottle.PhotoWallUploader(
                api=vk_user_client.api,
            ).upload(image)
            message = post_title
            if timetable.announcement_text:
                message += f"\n\nТекст объявления: {timetable.announcement_text}"
            if timetable.is_updated:
                message = "[ОБНОВЛЕНО]\n\n" + message
            post = await vk_user_client.api.wall.post(
                owned_id=config.vk_group_id,
                from_group=True,
                message=message,
                attachments=[vk_attachment_string],
            )
            for peer_id in broadcast_peer_ids:
                messages: List[MessagesSendUserIdsResponseItem] = (
                    await vk_group_client.api.messages.send(
                        attachment=vk_attachment_string,
                        message=message,
                        random_id=random.randint(-1_000_000, 1_000_000),
                        peer_ids=list(broadcast_peer_ids),
                    )
                )
                chats = await (
                    vk_group_client.api.messages.get_conversations_by_id(
                        peer_ids=list(broadcast_peer_ids)
                    )
                )
                allowed_peers = set()
                for chat in chats.items:
                    if (
                        chat.chat_settings and (
                            chat.chat_settings.pinned_message is None
                            or (
                                chat.chat_settings.pinned_message.from_id
                                == config.vk_group_id
                            )
                        )
                    ):
                        allowed_peers.add(chat.peer.id)
                for message in messages:
                    if message.peer_id in allowed_peers:
                        try:
                            await vk_group_client.api.messages.pin(
                                peer_id=message.peer_id,
                                conversation_message_id=(
                                    message.conversation_message_id
                                )
                            )
                        except Exception:  # I do not bother about this either
                            pass


async def main():
    asyncio.create_task(run())
    vk_group_client.on.message()(handle_new_message)
    await vk_group_client.run_polling()


loguru.logger.remove()
loguru.logger.add(sys.stdout, level="WARNING")
