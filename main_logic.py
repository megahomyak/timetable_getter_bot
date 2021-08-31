import asyncio

import aiohttp

from bot import make_bot


async def main():
    async with aiohttp.ClientSession() as aiohttp_session:
        bot = await make_bot(
            aiohttp_session, config_filename="config.json", debug=False
        )
        print("Starting!")
        await bot.run()

asyncio.get_event_loop().run_until_complete(main())
