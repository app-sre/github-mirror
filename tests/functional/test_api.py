import hashlib
from unittest import mock

import pytest
import requests

from ghmirror.app import APP
from ghmirror.data_structures.monostate import UsersCache
from ghmirror.data_structures.monostate import GithubStatus
from ghmirror.core.constants import REQUESTS_TIMEOUT
from ghmirror.utils.wait import wait_for


class MockResponse:
    def __init__(self, content, headers, status_code, user=None):
        self.content = content.encode()
        self.headers = headers
        self.status_code = status_code
        self.user = user

    def json(self):
        return {'login': self.user}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError


def mocked_requests_get_etag(*args, **kwargs):
    if 'If-Modified-Since' in kwargs['headers']:
        return MockResponse('', {}, 304)

    if 'If-None-Match' in kwargs['headers']:
        return MockResponse('', {}, 304)

    return MockResponse('', {'ETag': 'foo'}, 200)


def mocked_requests_get_last_modified(*args, **kwargs):
    if 'If-Modified-Since' in kwargs['headers']:
        return MockResponse('', {}, 304)

    if 'If-None-Match' in kwargs['headers']:
        return MockResponse('', {}, 304)

    return MockResponse('', {'Last-Modified': 'bar'}, 200)


def mocked_requests_get_user_orgs_auth(*args, **kwargs):
    return MockResponse('', {}, 200, 'app-sre-bot')


def mocked_requests_get_user_orgs_unauth(*args, **kwargs):
    return MockResponse('', {}, 200, 'other')


def mocked_requests_get_error(*args, **kwargs):
    return MockResponse('', {}, 500)


def mocked_requests_monitor_good(*args, **kwargs):
    return MockResponse('', {}, 200)


def mocked_requests_monitor_bad(*args, **kwargs):
    return MockResponse('', {}, 403)


@pytest.fixture
def client():
    APP.config['TESTING'] = True

    with APP.test_client() as client:
        yield client


def test_healthz(client):
    response = client.get('/healthz', follow_redirects=True)
    assert response.status_code == 200
    assert response.data == b'OK'


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
def test_mirror_etag(mock_get, client):
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_last_modified)
def test_mirror_last_modified(mock_get, client):
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_last_modified)
def test_mirror_upstream_call(mocked_request, client):
    client.get('/user/repos?page=2',
               headers={'Authorization': 'foo'})
    expected_url = 'https://api.github.com/user/repos?page=2'
    mocked_request.assert_called_with(method='GET',
                                      headers={'Authorization': 'foo'},
                                      url=expected_url,
                                      timeout=REQUESTS_TIMEOUT)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_last_modified)
def test_mirror_non_get(mocked_request, client):
    client.patch('/repos/foo/bar', data=b'foo')
    expected_url = 'https://api.github.com/repos/foo/bar'
    mocked_request.assert_called_with(method='PATCH', data=b'foo', headers={},
                                      url=expected_url,
                                      timeout=REQUESTS_TIMEOUT)


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_user_orgs_auth)
@mock.patch('ghmirror.core.mirror_requests.requests.request')
def test_mirror_authorized_user(mocked_request, mocked_cond_request, client):
    client.get('/repos/app-sre/github-mirror',
               headers={'Authorization': 'foo'})
    mocked_cond_request.assert_called_with(auth='foo', method='GET',
                                           url='https://api.github.com/user')
    mocked_request.assert_called_with(method='GET',
                                      headers={'Authorization': 'foo'},
                                      url='https://api.github.com/repos/'
                                          'app-sre/github-mirror',
                                      timeout=REQUESTS_TIMEOUT)


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_user_orgs_auth)
@mock.patch('ghmirror.core.mirror_requests.requests.request')
def test_mirror_authorized_user_cached(mocked_request, mocked_cond_request,
                                       client):
    users_cache = UsersCache()
    auth_sha = hashlib.sha1('foo'.encode()).hexdigest()
    users_cache.add(auth_sha)

    client.get('/repos/app-sre/github-mirror',
               headers={'Authorization': 'foo'})
    assert not mocked_cond_request.called
    mocked_request.assert_called_with(method='GET',
                                      headers={'Authorization': 'foo'},
                                      url='https://api.github.com/repos/'
                                          'app-sre/github-mirror',
                                      timeout=REQUESTS_TIMEOUT)


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_user_orgs_unauth)
def test_mirror_user_forbidden(mocked_cond_request, client):
    response = client.get('/repos/app-sre/github-mirror',
                          headers={'Authorization': 'foo'})
    assert response.status_code == 403


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
def test_mirror_no_auth(client):
    response = client.get('/repos/app-sre/github-mirror',
                          headers={})
    assert response.status_code == 401


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_error)
def test_mirror_auth_error(mocked_cond_request, client):
    response = client.get('/repos/app-sre/github-mirror',
                          headers={'Authorization': 'foo'})
    assert response.status_code == 500


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.get',
            side_effect=mocked_requests_monitor_good)
def test_offline_mode(mock_monitor_get, mock_request, client):
    # Let's wait the mirror consider itself online
    assert wait_for(lambda: GithubStatus().online, timeout=5)

    # First request will be a 200, intended to build up the cache and
    # is it is also an ONLINE_MISS
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)

    # Now make the mirror go offline for upstream timeout
    mock_monitor_get.side_effect = requests.exceptions.Timeout

    # Let's wait the mirror to consider itself offline
    assert wait_for(lambda: not GithubStatus().online, timeout=5)

    # Second request, mirror went offline already but response is in the
    # cache due to the first request
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="OFFLINE_HIT",'
            'method="GET",status="200"} 1.0') in str(response.data)

    # Additional request including auth header. Should MISS since the
    # cache key id built from resource + user
    response = client.get('/repos/app-sre/github-mirror',
                          headers={'Authorization': 'foo'})
    assert response.status_code == 504
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="OFFLINE_MISS",'
            'method="GET",status="504"} 1.0') in str(response.data)

    # POST, just to check if we are behaving.
    response = client.post('/repos/app-sre/github-mirror',
                           data=b'foo')
    assert response.status_code == 504
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="OFFLINE_MISS",'
            'method="POST",status="504"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.get',
            side_effect=mocked_requests_monitor_good)
def test_offline_mode_upstream_error(mock_monitor_get, mock_request, client):
    # Let's wait the mirror consider itself online
    assert wait_for(lambda: GithubStatus().online, timeout=5)

    # First request will be a 200, intended to build up the cache and
    # is it is also an ONLINE_MISS
    assert wait_for(lambda: GithubStatus().online, timeout=5)
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)

    # Now make the mirror go offline for upstream error
    mock_monitor_get.side_effect = mocked_requests_monitor_bad

    # Let's wait the mirror to consider itself offline
    assert wait_for(lambda: not GithubStatus().online, timeout=5)

    # For the second request, mirror went offline already but
    # response is in the cache due to the first request, so
    # we get a 200 and an OFFLINE_HIT
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="OFFLINE_HIT",'
            'method="GET",status="200"} 1.0') in str(response.data)
