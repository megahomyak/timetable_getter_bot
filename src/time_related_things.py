import asyncio
import datetime

import pytz

from src.looped_two_ways_iterator import LoopedTwoWaysIterator

YEKATERINBURG_TIMEZONE = pytz.timezone("Asia/Yekaterinburg")


def now():
    return datetime.datetime.now(tz=YEKATERINBURG_TIMEZONE)


WEEKDAYS_AMOUNT = 7


def get_amount_of_days_to_a_weekday(
        initial_weekday: int, future_weekday: int):
    return (future_weekday - initial_weekday) % WEEKDAYS_AMOUNT


def get_next_timetable_search_beginning_date(
        next_timetable_weekday: int, sleep_end_hour: int,
        initial_date: datetime.datetime):
    future = initial_date + datetime.timedelta(
        days=get_amount_of_days_to_a_weekday(
            initial_weekday=initial_date.weekday(),
            future_weekday=next_timetable_weekday
        )
    )
    future = future.replace(
        hour=sleep_end_hour,
        minute=0,
        second=0,
        microsecond=0
    )
    return future


async def sleep_to_next_timetable_day(
        next_timetable_weekday: int, sleep_end_hour: int,
        initial_datetime: datetime.datetime):
    future = get_next_timetable_search_beginning_date(
        next_timetable_weekday, sleep_end_hour, initial_datetime
    )
    await asyncio.sleep((future - initial_datetime).total_seconds())


def roll_weekdays_iterator(
        timetable_weekdays_iterator: LoopedTwoWaysIterator,
        current_weekday: int):
    try:
        while timetable_weekdays_iterator.step_forward() <= current_weekday:
            # Skipping all the days that go before current day (and the
            # current day, if present)
            pass
    except StopIteration:
        pass
    else:
        timetable_weekdays_iterator.step_back()
    # Now this iterator will yield the day that goes after current (maybe
    # even from the next week, if StopIteration was raised)
