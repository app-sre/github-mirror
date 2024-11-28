import os

import requests

GITHUB_MIRROR_URL = os.environ.get("GITHUB_MIRROR_URL")
CLIENT_TOKEN = os.environ.get("CLIENT_TOKEN")


def test_get_repo(path, code, cache):
    if not GITHUB_MIRROR_URL or not CLIENT_TOKEN:
        raise ValueError("GITHUB_MIRROR_URL and CLIENT_TOKEN must be set")
    url = f"{GITHUB_MIRROR_URL}{path}"
    headers = {"Authorization": f"token {CLIENT_TOKEN}"}

    response = requests.get(url, headers=headers, timeout=60)

    assert response.status_code == code
    if cache is not None:
        assert response.headers["X-Cache"] == cache


if __name__ == "__main__":
    test_get_repo("/repos/app-sre/github-mirror", 200, None)
    test_get_repo("/repos/app-sre/github-mirror", 200, "ONLINE_HIT")
