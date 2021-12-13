import asyncio
import datetime

import pytz

YEKATERINBURG_TIMEZONE = pytz.timezone("Asia/Yekaterinburg")

SATURDAY = 5


def now():
    return datetime.datetime.now(tz=YEKATERINBURG_TIMEZONE)


def today():
    return now().date()


async def wait_until(time: datetime.datetime):
    await asyncio.sleep((time - now()).total_seconds())


def get_next_school_day_date():
    date = today()
    return date + datetime.timedelta(
        # Skipping the sunday because we don't have classes on sunday
        days=2 if date.weekday() == SATURDAY else 1
    )


MINIMUM_TIMETABLE_SENDING_HOUR = 10


async def _wait_until_minimum_timetable_sending_hour_on_some_day(
        date: datetime.date):
    date = datetime.datetime.combine(
        date=date, time=datetime.time(hour=MINIMUM_TIMETABLE_SENDING_HOUR),
        tzinfo=YEKATERINBURG_TIMEZONE
    )
    await wait_until(date)


async def wait_until_minimum_timetable_sending_hour():
    await _wait_until_minimum_timetable_sending_hour_on_some_day(
        date=today() + datetime.timedelta(days=1)
    )


async def wait_until_next_school_day():
    await _wait_until_minimum_timetable_sending_hour_on_some_day(
        # Sleeping through the sunday
        date=get_next_school_day_date()
    )
