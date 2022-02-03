import asyncio
import sys

import loguru
import vkbottle
from netschoolapi import NetSchoolAPI

from src.bot import Bot
from src.config import Config
from src.timetable_days_cacher import TimetableDaysCacher


async def main():
    config = Config.make_from_file("data/config.json")
    loguru.logger.remove()
    loguru.logger.add(sys.stdout, level="WARNING")
    netschoolapi_client = NetSchoolAPI(url="https://sgo.edu-74.ru/")
    await netschoolapi_client.login(
        user_name=config.sgo_username, password=config.sgo_password,
        school=config.school_name
    )
    bot = await Bot.new(
        config=config,
        vk_group_client=vkbottle.Bot(token=config.vk_group_token),
        vk_user_client=vkbottle.User(token=config.vk_user_token),
        netschoolapi_client=netschoolapi_client,
        timetable_days_cacher=TimetableDaysCacher.from_file(
            "data/timetable_days.txt"
        ),
        do_logging=True
    )
    await bot.run()


asyncio.get_event_loop().run_until_complete(main())
