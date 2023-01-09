import asyncio
import sys
import traceback

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
    netschoolapi_client = NetSchoolAPI(
        url=config.site_url,
        default_requests_timeout=0,  # Infinite re-requests
    )
    await netschoolapi_client.login(
        user_name=config.sgo_username, password=config.sgo_password,
        school_name_or_id=config.school_name
    )
    bot = await Bot.new(
        config=config,
        vk_group_client=vkbottle.Bot(token=config.vk_group_token),
        vk_user_client=vkbottle.User(token=config.vk_user_token),
        netschoolapi_client=netschoolapi_client,
        timetable_days_cacher=TimetableDaysCacher.from_file(
            "data/timetable_days.txt"
        )
    )
    while True:
        # noinspection PyBroadException
        try:
            await bot.run()
        except Exception as exception:
            # "Сетевой город" likes to throw sudden errors at me, and I'm tired
            # to get rid of them individually, so for now this approach is
            # acceptable
            traceback.print_exc()
            await asyncio.sleep(5)  # Just in case


asyncio.run(main())
