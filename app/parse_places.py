import requests
from bs4 import BeautifulSoup

from myshared import UniDownException, UNI_PAGE


def get_places() -> dict[str, str]:
    """returns in format: place_name -> url"""
    try:
        page = requests.get(UNI_PAGE + "/schedule")
    except requests.exceptions.ConnectionError:
        raise UniDownException()

    soup = BeautifulSoup(page.content, "html.parser")

    div = soup.find("div", {"class": "panes_item__type_group"})

    ret = {}
    items = div.find_all("li")
    for item in items:
        a = item.find("a")
        ret[a.text] = a["href"]

    return ret


if __name__ == "__main__":
    print(get_places())
