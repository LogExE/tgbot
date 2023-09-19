import requests

from myshared import UniDownException, UNI_PAGE


def teachers_search(name: str) -> list[dict[str, str]]:
    try:
        resp = requests.post(
            UNI_PAGE + "/schedule/teacher/search", data={"js": 1, "search": name}
        )
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise UniDownException()


if __name__ == "__main__":
    print(teachers_search("Галаев"))
