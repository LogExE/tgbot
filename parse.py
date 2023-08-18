import requests
from bs4 import BeautifulSoup

from enum import Enum
from dataclasses import dataclass


class SubjWeek(Enum):
    EVEN = 0
    ODD = 1
    EVERY = 2


str_to_subjweek = {"чис.": SubjWeek.EVEN, "знам.": SubjWeek.ODD, "": SubjWeek.EVERY}


class SubjType(Enum):
    LECTURE = 0
    PRACTICE = 1


str_to_subjtype = {"лек.": SubjType.LECTURE, "пр.": SubjType.PRACTICE, "": None}


@dataclass
class Subject:
    name: str
    teacher: str
    place: str
    other: str
    type: SubjType
    week: SubjWeek


def get_subjects(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    juicy_table = soup.find("table", {"id": "schedule"})
    rows = juicy_table.find_all("tr")
    rows = rows[1:]
    weekdays = [[] for i in range(6)]
    for row in rows:
        data = row.find_all("td")
        for j, d in enumerate(data):
            weekday = []
            entries = d.findChildren("div", recursive=False)
            for e in entries:
                week = e.find("div", {"class": "l-pr-r"})
                type = e.find("div", {"class": "l-pr-t"})
                other = e.find("div", {"class": "l-pr-g"})
                name = e.find("div", {"class": "l-dn"})
                teacher = e.find("div", {"class": "l-tn"})
                place = e.find("div", {"class": "l-p"})
                weekday.append(
                    Subject(
                        name=name.text,
                        teacher=teacher.text,
                        place=place.text,
                        type=str_to_subjtype[type.text],
                        other=other.text,
                        week=str_to_subjweek[week.text],
                    )
                )
            weekdays[j].append(weekday)

    return weekdays


if __name__ == "__main__":
    weekdays = get_subjects("https://www.sgu.ru/schedule/knt/do/341")
    for i in range(6):
        for j, subj in enumerate(weekdays[i]):
            print(f"День {i}, предмет {j}: {subj}")
