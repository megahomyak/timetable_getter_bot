from abc import ABC, abstractmethod

from timetable import Timetable


class AbstractTimetableGetter(ABC):

    @abstractmethod
    async def get_timetable(self, day_bias: int = 0) -> Timetable:
        pass
