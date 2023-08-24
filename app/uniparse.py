import requests
from bs4 import BeautifulSoup

from enum import Enum
from dataclasses import dataclass


class SubjWeek(Enum):
    EVEN = 0
    ODD = 1
    EVERY = 2


str_to_subjweek = {"чис.": SubjWeek.EVEN, "знам.": SubjWeek.ODD, "": SubjWeek.EVERY}
week_to_str = {SubjWeek.EVEN: "числитель", SubjWeek.ODD: "знаменатель"}


class SubjType(Enum):
    LECTURE = 0
    PRACTICE = 1


str_to_subjtype = {"лек.": SubjType.LECTURE, "пр.": SubjType.PRACTICE, "": None}
type_to_str = {SubjType.LECTURE: "лекция", SubjType.PRACTICE: "практика"}


@dataclass
class Subject:
    name: str
    teacher: str
    place: str
    other: str
    type: SubjType
    week: SubjWeek

    def __str__(self):
        week_str = (
            "каждую неделю"
            if self.week == SubjWeek.EVERY
            else "по числителю"
            if self.week == SubjWeek.EVEN
            else "по знаменателю"
        )
        return f"""
        Пара: {type_to_str[self.type]} 
        Предмет: {self.name}
        Проходит: {self.place}, {week_str}, {self.other}
        Преподаватель: {self.teacher}."""


DAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]


def get_subjects(url: str) -> dict[str, list[list[Subject]]]:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    juicy_table = soup.find("table", {"id": "schedule"})
    rows = juicy_table.find_all("tr")
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


def pretty_subjects(subjs):
    lines = []
    for i in range(6):
        for j, subj in enumerate(subjs[i]):
            if subj != []:
                lines.append(f"День {i}, предмет {j}: {subj}")
    return "\n".join(lines)


if __name__ == "__main__":
    weekdays = get_subjects("https://www.sgu.ru/schedule/knt/do/341")
    print(pretty_subjects(weekdays))
