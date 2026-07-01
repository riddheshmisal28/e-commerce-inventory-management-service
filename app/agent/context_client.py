import requests


class EngineeringContextClient:

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 5,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def get_endpoints(self):
        response = self.session.get(
            f"{self.base_url}/engineering/endpoints",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_entities(self):
        response = self.session.get(
            f"{self.base_url}/engineering/entities",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_models(self):
        response = self.session.get(
            f"{self.base_url}/engineering/models",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def search_endpoints(
        self,
        keyword: str,
    ):
        response = self.session.get(
            f"{self.base_url}/engineering/endpoints/search",
            params={"keyword": keyword},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()