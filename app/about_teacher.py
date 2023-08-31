import requests

from myshared import UniDownException

TEACHERS_ADDR = "https://www.sgu.ru/schedule/teacher/search"


def teachers_search(name: str) -> list[dict[str, str]]:
    try:
        resp = requests.post(TEACHERS_ADDR, data={"js": 1, "search": name})
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise UniDownException()


if __name__ == "__main__":
    print(teachers_search("Галаев"))
