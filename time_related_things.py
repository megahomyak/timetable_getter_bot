import asyncio
import datetime

import pytz

YEKATERINBURG_TIMEZONE = pytz.timezone("Asia/Yekaterinburg")

FRIDAY = 4
SATURDAY = 5


def now():
    return datetime.datetime.now(tz=YEKATERINBURG_TIMEZONE)


def today():
    return now().date()


def get_next_school_day_date():
    today_ = today()
    return today_ + datetime.timedelta(
        # Skipping the sunday
        days=2 if today_.weekday() == SATURDAY else 1
    )


async def wait_until(time: datetime.datetime):
    await asyncio.sleep((time - now()).total_seconds())


MINIMUM_TIMETABLE_SENDING_HOUR = 12


async def wait_until_minimum_timetable_sending_hour():
    date = today()
    date += datetime.timedelta(
        # Skipping the saturday because there will be no timetable for sunday on
        # saturday (because we don't have lessons on sunday)
        days=2 if date.weekday() == FRIDAY else 1
    )
    await wait_until(datetime.datetime.combine(
        date, datetime.time(hour=MINIMUM_TIMETABLE_SENDING_HOUR),
        tzinfo=YEKATERINBURG_TIMEZONE
    ))
