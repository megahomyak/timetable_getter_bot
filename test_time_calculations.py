import datetime

import pytest

import time_related_things
from looped_two_ways_iterator import LoopedTwoWaysIterator


@pytest.mark.parametrize(
    ("initial_weekday", "future_weekday", "days_between_them"),
    [(0, 6, 6), (6, 1, 2), (6, 0, 1), (3, 5, 2)]
)
def test_weekdays_skip(initial_weekday, future_weekday, days_between_them):
    assert time_related_things.get_amount_of_days_to_a_weekday(
        initial_weekday, future_weekday
    ) == days_between_them


@pytest.mark.parametrize(
    (
        "weekdays", "initial_weekday", "expected_next_weekday",
        "amount_of_days_to_wait"
    ),
    [
        [(0, 1, 2, 3, 4, 5), 6, 0, 1],
        [(0, 1, 2, 3, 4, 5), 0, 1, 1],
        [(0, 1, 2, 3, 4, 5), 5, 0, 2],
        [(0, 5, 6), 2, 5, 3],
        [(0, 1), 0, 1, 1]
    ]
)
def test_weekdays_iterator_roll(
        weekdays, initial_weekday: int, expected_next_weekday,
        amount_of_days_to_wait):
    weekdays_iterator = LoopedTwoWaysIterator(weekdays)
    time_related_things.roll_weekdays_iterator(
        weekdays_iterator, initial_weekday
    )
    next_weekday = next(weekdays_iterator)
    assert next_weekday == expected_next_weekday
    assert time_related_things.get_amount_of_days_to_a_weekday(
        initial_weekday, next_weekday
    ) == amount_of_days_to_wait


FUNNY_DATE = datetime.datetime(day=14, month=11, year=1987, hour=12)
# FUNNY_DATE.weekday() == 5 (saturday)


@pytest.mark.parametrize(
    ("initial_date", "next_timetable_weekday", "expected_future_date"),
    [
        [
            FUNNY_DATE, 6,
            (FUNNY_DATE + datetime.timedelta(days=1)).replace(hour=10)
        ],
        [
            FUNNY_DATE.replace(hour=22), 0,
            (FUNNY_DATE + datetime.timedelta(days=2)).replace(hour=10)
        ],
        [
            FUNNY_DATE.replace(hour=22), 5,
            FUNNY_DATE.replace(hour=10)
        ],
        [
            FUNNY_DATE.replace(hour=22), 2,
            (FUNNY_DATE + datetime.timedelta(days=4)).replace(hour=10)
        ]
    ]
)
def test_next_timetable_search_beginning_date(
        initial_date, next_timetable_weekday, expected_future_date):
    assert time_related_things.get_next_timetable_search_beginning_date(
        next_timetable_weekday=next_timetable_weekday,
        sleep_end_hour=10,
        initial_date=initial_date
    ) == expected_future_date
