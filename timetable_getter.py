import asyncio
import datetime

from netschoolapi import NetSchoolAPI

from abstract_timetable_getter import AbstractTimetableGetter
from timetable import Timetable


class TimetableGetter(AbstractTimetableGetter):

    def __init__(self, netschoolapi: NetSchoolAPI):
        self.netschoolapi = netschoolapi
        self.timetable_getting_lock = asyncio.Lock()

    async def get_timetable(self, day_bias: int = 0) -> Timetable:
        day = datetime.date.today() - datetime.timedelta(days=day_bias)
        async with self.timetable_getting_lock:
            async with self.netschoolapi:
                lessons = (
                    await self.netschoolapi.get_diary(
                        week_start=day, week_end=day
                    )
                ).schedule[0].lessons
        return Timetable(lessons)
