import pytest

import time_related_things


@pytest.mark.parametrize(
    ("initial_weekday", "future_weekday", "days_between_them"),
    [(0, 6, 6), (6, 1, 2), (6, 0, 1), (3, 5, 2)]
)
def test_time_calculations(initial_weekday, future_weekday, days_between_them):
    assert time_related_things.get_amount_of_days_to_a_weekday(
        initial_weekday, future_weekday
    ) == days_between_them
