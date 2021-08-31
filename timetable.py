from dataclasses import dataclass
from typing import List

from netschoolapi.data import Lesson


@dataclass
class Timetable:
    lessons: List[Lesson]

    def get_homework_as_string(self) -> str:
        return "\n".join(
            f"{lesson.subject}: {lesson.homework}"
            for lesson in self.lessons
            if lesson.homework
        )

    def get_timetable_as_string(self) -> str:
        return "\n".join(
            f"{lesson.number}. {lesson.subject}, {lesson.room} "
            f"({lesson.starts_at} - {lesson.ends_at})"
            for lesson in self.lessons
        )
