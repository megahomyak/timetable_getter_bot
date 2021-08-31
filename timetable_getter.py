import asyncio
import datetime

from abstract_timetable_getter import AbstractTimetableGetter
from netschoolapi import NetSchoolAPI
from timetable import Timetable


class TimetableGetter(AbstractTimetableGetter):

    def __init__(self, netschoolapi: NetSchoolAPI):
        self.netschoolapi = netschoolapi
        self.timetable_getting_lock = asyncio.Lock()

    async def get_timetable(self, day_bias: int = 0) -> Timetable:
        day = datetime.date.today() + datetime.timedelta(days=day_bias)
        async with self.timetable_getting_lock:
            diary = await self.netschoolapi.diary(start=day, end=day)
            if diary.schedule:
                return Timetable(diary.schedule[0].lessons)
            else:
                return Timetable(lessons=[])
