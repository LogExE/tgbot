import requests
from bs4 import BeautifulSoup

from enum import Enum
from dataclasses import dataclass


class SubjWeek(Enum):
    EVEN = 0
    ODD = 1
    EVERY = 2

    def __str__(self):
        if self == SubjWeek.EVERY:
            return "каждую неделю"
        elif self == SubjWeek.EVEN:
            return "по числителю"
        else:
            return "по знаменателю"


class SubjType(Enum):
    LECTURE = 0
    PRACTICE = 1

    def __str__(self):
        if self == SubjType.LECTURE:
            return "лекция"
        else:
            return "практика"


@dataclass
class Subject:
    name: str
    teacher: str
    place: str
    other: str
    type: SubjType
    week: SubjWeek

    def __str__(self):
        return (
            f"Пара: {self.type}\n"
            f"Предмет: {self.name}\n"
            f"Проходит: {self.place}, {self.week}, {self.other}\n"
            f"Преподаватель: {self.teacher}."
        )


DAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]

TIMES = [
    "8:20-9:50",
    "10:00-11:30",
    "12:05-13:40",
    "13:50-15:25",
    "15:35-17:10",
    "17:20-18:40",
    "18:45-20:05",
    "20:10-21:30",
]

str_to_subjweek = {"чис.": SubjWeek.EVEN, "знам.": SubjWeek.ODD, "": SubjWeek.EVERY}
str_to_subjtype = {"лек.": SubjType.LECTURE, "пр.": SubjType.PRACTICE, "": None}


def get_group_schedule(url: str) -> dict[str, list[list[Subject]]]:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    juicy_table = soup.find("table", {"id": "schedule"})
    rows = juicy_table.find_all("tr")
    if rows is None:
        return {}
    rows = rows[1:]
    weekdays = {day: [] for day in DAYS}
    for row in rows:
        data = row.find_all("td")
        for day, d in zip(DAYS, data):
            subjects = []
            entries = d.findChildren("div", recursive=False)
            for e in entries:
                week = e.find("div", {"class": "l-pr-r"})
                type = e.find("div", {"class": "l-pr-t"})
                other = e.find("div", {"class": "l-pr-g"})
                name = e.find("div", {"class": "l-dn"})
                teacher = e.find("div", {"class": "l-tn"})
                place = e.find("div", {"class": "l-p"})
                subjects.append(
                    Subject(
                        name=name.text,
                        teacher=teacher.text,
                        place=place.text,
                        type=str_to_subjtype[type.text],
                        other=other.text,
                        week=str_to_subjweek[week.text],
                    )
                )
            weekdays[day].append(subjects)

    return weekdays


def pretty_day(day: list[list[Subject]]) -> str:
    lines = []
    for time, lesson in zip(TIMES, day):
        lines.append(f"{time}:")
        if len(lesson) > 0:
            for i, subj in enumerate(lesson, 1):
                lines.append(f"{i}) {subj}\n")
        else:
            lines.append("Нет данных.\n")
    return "\n".join(lines)


if __name__ == "__main__":
    gs = get_group_schedule("https://www.sgu.ru/schedule/mm/do/341")
    for day in DAYS:
        print(day)
        print(pretty_day(gs[day]))
