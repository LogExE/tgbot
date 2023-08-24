import requests
from bs4 import BeautifulSoup


def get_groups(url: str) -> dict[str, str]:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    ret = {}
    links = soup.find_all("a", href=True)
    for link in links:
        if "/schedule/" in link["href"] and len(link["href"].split("/")) == 5:
            ret[link.text] = link["href"]
    return ret


if __name__ == "__main__":
    print(get_groups("https://www.sgu.ru/schedule/knt/"))
