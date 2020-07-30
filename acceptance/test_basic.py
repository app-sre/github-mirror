import os
import requests

import pytest


GITHUB_MIRROR_URL = os.environ['GITHUB_MIRROR_URL']
CLIENT_TOKEN = os.environ['CLIENT_TOKEN']


class TestsBasic:

    @pytest.mark.parametrize(
        'path, code, cache',
        (
                ['/repos/app-sre/github-mirror', 200, None],
                ['/repos/app-sre/github-mirror', 200, 'ONLINE_HIT'],
        )
    )
    def test_get_repo(self, path, code, cache):
        url = f'{GITHUB_MIRROR_URL}{path}'
        headers = {'Authorization': f'token {CLIENT_TOKEN}'}

        response = requests.get(url, headers=headers)

        assert response.status_code == code
        if cache is not None:
            assert response.headers['X-Cache'] == cache
