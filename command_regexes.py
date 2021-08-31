import re

_help_message_parts = ["/помощь (или \"/команды\") - это сообщение"]


def make_regex(pattern: str, help_message: str):
    _help_message_parts.append(help_message)
    return re.compile(pattern)


GET_HOMEWORK_REGEX = make_regex(
    r"/дз(?: (-?\d+))?",
    "/дз [сдвиг в днях от сегодня (опционально)] - показать дз в указанный день"
)
GET_TIMETABLE_REGEX = make_regex(
    r"/расписание(?: (-?\d+))?",
    "/расписание [сдвиг в днях от сегодня (опционально)] - показать расписание "
    "в указанный день"
)


HELP_MESSAGE = "\n".join(_help_message_parts)
