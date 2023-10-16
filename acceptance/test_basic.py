import os
import requests



GITHUB_MIRROR_URL = os.environ['GITHUB_MIRROR_URL']
CLIENT_TOKEN = os.environ['CLIENT_TOKEN']


def test_get_repo(path, code, cache):
    url = f'{GITHUB_MIRROR_URL}{path}'
    headers = {'Authorization': f'token {CLIENT_TOKEN}'}

    response = requests.get(url, headers=headers)

    assert response.status_code == code
    if cache is not None:
        assert response.headers['X-Cache'] == cache


test_get_repo('/repos/app-sre/github-mirror', 200, None)
test_get_repo('/repos/app-sre/github-mirror', 200, 'ONLINE_HIT')
