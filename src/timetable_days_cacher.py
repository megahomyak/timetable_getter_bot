from abc import ABC, abstractmethod
from typing import Set


class AbstractTimetableDaysCacher(ABC):

    @abstractmethod
    def set_days(self, days: Set[int]):
        pass

    @abstractmethod
    def get_days(self) -> Set[int]:
        pass


class TimetableDaysCacher(AbstractTimetableDaysCacher):

    def __init__(
            self, initial_timetable_days: Set[int], save_file_path: str):
        self._timetable_days = initial_timetable_days
        self._save_file_path = save_file_path

    @classmethod
    def from_file(cls, save_file_path: str):
        try:
            with open(save_file_path) as f:
                days = set(int(day) for day in f.read().split())
        except FileNotFoundError:
            days = set()
        return cls(initial_timetable_days=days, save_file_path=save_file_path)

    def set_days(self, days: Set[int]):
        if self._timetable_days != days:
            with open(self._save_file_path, "w") as f:
                f.write(" ".join(str(day) for day in days))
        self._timetable_days = days

    def get_days(self) -> Set[int]:
        return self._timetable_days
