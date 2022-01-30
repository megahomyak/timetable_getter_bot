import asyncio
import datetime

import pytz

YEKATERINBURG_TIMEZONE = pytz.timezone("Asia/Yekaterinburg")


def now():
    return datetime.datetime.now(tz=YEKATERINBURG_TIMEZONE)


WEEKDAYS_AMOUNT = 7


def get_amount_of_days_to_a_weekday(
        initial_weekday: int, future_weekday: int):
    return (future_weekday - initial_weekday) % WEEKDAYS_AMOUNT


async def sleep_to_next_timetable_day(
        next_timetable_weekday: int, end_hour: int,
        beginning_datetime: datetime.datetime):
    future = beginning_datetime + datetime.timedelta(
        days=get_amount_of_days_to_a_weekday(
            initial_weekday=beginning_datetime.weekday(),
            future_weekday=next_timetable_weekday
        )
    )
    future = future.replace(
        hour=end_hour,
        minute=0,
        second=0,
        microsecond=0
    )
    await asyncio.sleep((future - beginning_datetime).total_seconds())
