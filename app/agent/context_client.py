import requests


BASE_URL = "http://localhost:8000"


def get_endpoints():
    return requests.get(
        f"{BASE_URL}/engineering/endpoints"
    ).json()


def get_entities():
    return requests.get(
        f"{BASE_URL}/engineering/entities"
    ).json()


def search_endpoints(keyword: str):
    return requests.get(
        f"{BASE_URL}/engineering/endpoints/search",
        params={"keyword": keyword},
    ).json()