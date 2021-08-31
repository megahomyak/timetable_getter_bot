import datetime


def get_time_as_short_string(time: datetime.time):
    return time.strftime("%H:%M")
