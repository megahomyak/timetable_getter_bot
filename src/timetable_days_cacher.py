import datetime
from abc import ABC, abstractmethod
from typing import Dict


DayNumber = int
LastChangeDatetime = datetime.datetime

DaysType = Dict[DayNumber, LastChangeDatetime]


class AbstractTimetableDaysCacher(ABC):

    @abstractmethod
    def set_days(self, days: DaysType):
        pass

    @abstractmethod
    def get_days(self) -> DaysType:
        pass


class TimetableDaysCacher(AbstractTimetableDaysCacher):

    def __init__(
            self, initial_timetable_days: DaysType, save_file_path: str):
        self._timetable_days = initial_timetable_days
        self._save_file_path = save_file_path

    @classmethod
    def from_file(cls, save_file_path: str):
        try:
            days = {}
            with open(save_file_path) as f:
                for day_number, last_change_timestamp in (
                    day.split() for day in f.read().split()
                ):
                    days[int(day_number)] = last_change_timestamp
        except FileNotFoundError:
            days = set()
        return cls(initial_timetable_days=days, save_file_path=save_file_path)

    def set_days(self, days: DaysType):
        if self._timetable_days != days:
            with open(self._save_file_path, "w") as f:
                f.write(" ".join(str(day) for day in days))
        self._timetable_days = days

    def get_days(self) -> DaysType:
        return self._timetable_days
