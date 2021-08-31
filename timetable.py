from dataclasses import dataclass
from typing import List

import utils
from netschoolapi.data import Lesson

NO_LESSONS_IN_THE_SPECIFIED_DAY_TEXT = "В указанный день уроков нет"


@dataclass
class Timetable:
    lessons: List[Lesson]

    def get_homework_as_string(self) -> str:
        if self.lessons:
            subject_to_homework = {}
            for lesson in self.lessons:
                for assignment in lesson.assignments:
                    if assignment.type == "Домашнее задание":
                        try:
                            homework = subject_to_homework[lesson.subject]
                        except KeyError:
                            subject_to_homework[lesson.subject] = [
                                assignment.content
                            ]
                        else:
                            if assignment.content not in homework:
                                homework.append(assignment.content)
                        break
            return "\n\n".join(
                f"{subject_name}:\n" + "\n".join(homework_list)
                for subject_name, homework_list in subject_to_homework.items()
            )
        else:
            return NO_LESSONS_IN_THE_SPECIFIED_DAY_TEXT

    def get_timetable_as_string(self) -> str:
        if self.lessons:
            lessons_as_strings = []
            lesson_number = 1
            for lesson in self.lessons:
                while lesson_number != lesson.number:
                    lessons_as_strings.append(f"{lesson_number}. <пусто>")
                    lesson_number += 1
                lesson_start_string = (
                    utils.get_time_as_short_string(lesson.start)
                )
                lesson_end_string = (
                    utils.get_time_as_short_string(lesson.end)
                )
                lessons_as_strings.append(
                    f"{lesson_number}. {lesson.subject}, {lesson.room} "
                    f"({lesson_start_string} - {lesson_end_string})"
                )
                lesson_number += 1
            return "\n".join(lessons_as_strings)
        else:
            return NO_LESSONS_IN_THE_SPECIFIED_DAY_TEXT
