import requests
from bs4 import BeautifulSoup

UNI_PAGE = "https://www.sgu.ru/schedule/"


def get_faculties() -> dict[str, str]:
    page = requests.get(UNI_PAGE)
    soup = BeautifulSoup(page.content, "html.parser")

    div = soup.find("div", {"class": "panes_item__type_group"})

    ret = {}
    items = div.find_all("li")
    for item in items:
        a = item.find("a")
        ret[a.text] = a["href"]

    return ret


if __name__ == "__main__":
    print(get_faculties())
