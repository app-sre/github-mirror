from unittest import mock

import pytest
import requests

from ghmirror.app import APP
from ghmirror.data_structures.monostate import UsersCache
from ghmirror.data_structures.monostate import GithubStatus
from ghmirror.core.constants import REQUESTS_TIMEOUT, PER_PAGE_ELEMENTS
from ghmirror.utils.wait import wait_for


class MockResponse:
    def __init__(self, content, headers, status_code, user=None, links=None, json_content=None):
        self.content = content.encode()
        self.text = content
        self.headers = headers
        self.status_code = status_code
        self.user = user
        self.links = links
        self.json_content = json_content

    def json(self):
        if self.json_content is not None:
            return self.json_content
        return {'login': self.user}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError


def mocked_requests_get_etag(*_args, **kwargs):
    if 'If-Modified-Since' in kwargs['headers']:
        return MockResponse('', {}, 304)

    if 'If-None-Match' in kwargs['headers']:
        return MockResponse('', {}, 304)

    return MockResponse('', {'ETag': 'foo'}, 200)


def mocked_requests_get_last_modified(*_args, **kwargs):
    if 'If-Modified-Since' in kwargs['headers']:
        return MockResponse('', {}, 304)

    if 'If-None-Match' in kwargs['headers']:
        return MockResponse('', {}, 304)

    return MockResponse('', {'Last-Modified': 'bar'}, 200)


def mocked_requests_get_user_orgs_auth(*_args, **_kwargs):
    return MockResponse('', {}, 200, 'app-sre-bot')


def mocked_requests_get_user_orgs_unauth(*_args, **_kwargs):
    return MockResponse('', {}, 200, 'other')


def mocked_requests_get_error(*_args, **_kwargs):
    return MockResponse('', {}, 500)


def mocked_requests_monitor_good(*_args, **_kwargs):
    return MockResponse('', {}, 200)


def mocked_requests_monitor_bad(*_args, **_kwargs):
    return MockResponse('', {}, 403)


def setup_mocked_requests_session_get(mocked_session, side_effect):
    mocked_session.return_value.get.side_effect = side_effect


def mocked_requests_rate_limited(*_args, **_kwargs):
    return MockResponse('API rate limit exceeded', {}, 403)


def mocked_requests_api_corner_case(*_args, **kwargs):
    if 'If-None-Match' in kwargs['headers']:
        return MockResponse('', {}, 304, json_content=[{'a': 'b'}, {'c', 'd'}])

    return MockResponse('', {'ETag': 'foo'}, 200, json_content=[{'a': 'b'}, {'c', 'd'}])


@pytest.fixture(name="client")
def fixture_client():
    APP.config['TESTING'] = True

    with APP.test_client() as client:
        yield client


def test_healthz(client):
    response = client.get('/healthz', follow_redirects=True)
    assert response.status_code == 200
    assert response.data == b'OK'


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_etag(mock_monitor_session, _mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_last_modified)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_last_modified(mock_monitor_session, _mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_last_modified)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_upstream_call(mock_monitor_session, mocked_request, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    client.get('/user/repos?page=2',
               headers={'Authorization': 'foo'})
    expected_url = 'https://api.github.com/user/repos?page=2'
    mocked_request.assert_called_with(method='GET',
                                      headers={'Authorization': 'foo'},
                                      url=expected_url,
                                      timeout=REQUESTS_TIMEOUT,
                                      params={'page': '2', 'per_page': PER_PAGE_ELEMENTS})


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_last_modified)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_non_get(mock_monitor_session, mocked_request, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    client.patch('/repos/foo/bar', data=b'foo')
    expected_url = 'https://api.github.com/repos/foo/bar'
    mocked_request.assert_called_with(method='PATCH', data=b'foo', headers={},
                                      url=expected_url,
                                      timeout=REQUESTS_TIMEOUT,
                                      params={'per_page': PER_PAGE_ELEMENTS})


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_user_orgs_auth)
@mock.patch('ghmirror.core.mirror_requests.requests.request')
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_authorized_user(mock_monitor_session, mocked_request, mocked_cond_request, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    client.get('/repos/app-sre/github-mirror',
               headers={'Authorization': 'foo'})
    mocked_cond_request.assert_called_with(auth='foo', method='GET',
                                           url='https://api.github.com/user')
    mocked_request.assert_called_with(method='GET',
                                      headers={'Authorization': 'foo'},
                                      url='https://api.github.com/repos/'
                                          'app-sre/github-mirror',
                                      timeout=REQUESTS_TIMEOUT,
                                      params={'per_page': PER_PAGE_ELEMENTS})


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_user_orgs_auth)
@mock.patch('ghmirror.core.mirror_requests.requests.request')
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_authorized_user_cached(mock_monitor_session,
                                       mocked_request,
                                       mocked_cond_request,
                                       client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    users_cache = UsersCache()
    auth = 'foo'
    users_cache.add(auth)

    client.get('/repos/app-sre/github-mirror',
               headers={'Authorization': auth})
    assert not mocked_cond_request.called
    mocked_request.assert_called_with(method='GET',
                                      headers={'Authorization': auth},
                                      url='https://api.github.com/repos/'
                                          'app-sre/github-mirror',
                                      timeout=REQUESTS_TIMEOUT,
                                      params={'per_page': PER_PAGE_ELEMENTS})


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_user_orgs_unauth)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_user_forbidden(mock_monitor_session, _mocked_cond_request, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    response = client.get('/repos/app-sre/github-mirror',
                          headers={'Authorization': 'foo'})
    assert response.status_code == 403


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_no_auth(mock_monitor_session, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    response = client.get('/repos/app-sre/github-mirror',
                          headers={})
    assert response.status_code == 401


@mock.patch('ghmirror.decorators.checks.AUTHORIZED_USERS', 'app-sre-bot')
@mock.patch('ghmirror.decorators.checks.conditional_request',
            side_effect=mocked_requests_get_error)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_auth_error(mock_monitor_session, _mocked_cond_request, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    response = client.get('/repos/app-sre/github-mirror',
                          headers={'Authorization': 'foo'})
    assert response.status_code == 500


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_offline_mode(mock_monitor_session, _mock_request, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Let's wait the mirror consider itself online
    assert wait_for(lambda: GithubStatus().online, timeout=5)

    # First request will be a 200, intended to build up the cache and
    # is it is also an ONLINE_MISS
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    # Now make the mirror go offline for upstream timeout
    setup_mocked_requests_session_get(mock_monitor_session, requests.exceptions.Timeout)

    # Let's wait the mirror to consider itself offline
    assert wait_for(lambda: not GithubStatus().online, timeout=5)

    # Second request, mirror went offline already but response is in the
    # cache due to the first request
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="OFFLINE_HIT",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    # Additional request including auth header. Should MISS since the
    # cache key id built from resource + user
    response = client.get('/repos/app-sre/github-mirror',
                          headers={'Authorization': 'foo'})
    assert response.status_code == 504
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="OFFLINE_MISS",'
            'method="GET",status="504",user="None"} 1.0') in str(response.data)

    # POST, just to check if we are behaving.
    response = client.post('/repos/app-sre/github-mirror',
                           data=b'foo')
    assert response.status_code == 504
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="OFFLINE_MISS",'
            'method="POST",status="504",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_offline_mode_upstream_error(mock_monitor_session, _mock_request, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
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
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    # Now make the mirror go offline for upstream error
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_get_error)

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
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_rate_limited)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_rate_limited(_mock_monitor_session, mock_request, client):
    setup_mocked_requests_session_get(_mock_monitor_session, mocked_requests_monitor_good)
    # First request will get a 403/rate-limited. Because it's not cached
    # yet, we receive the same 403
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 403
    response = client.get('/metrics')
    # In the metrics, we see a RATE_LIMITED_MISS
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="RATE_LIMITED_MISS",'
            'method="GET",status="403",user="None"} 1.0') in str(response.data)

    # Second request will be a 200, intended to build up the cache, so
    # it is an ONLINE_MISS
    mock_request.side_effect = mocked_requests_get_etag
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    # For the third request, the response is a 403/rate-limited,
    # but because the resource was cached we want to see a 200
    # with RATE_LIMITED_HIT
    mock_request.side_effect = mocked_requests_rate_limited
    response = client.get('/repos/app-sre/github-mirror')
    assert response.status_code == 200
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="RATE_LIMITED_HIT",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_api_corner_case)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_pagination_corner_case_custom_page_elements(mock_monitor_session, _mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror?per_page=2',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror?per_page=2',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_miss as the request content has the same
    # number of elements as the PER_PAGE_ELEMENTS and links content
    # is empty
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 2.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.PER_PAGE_ELEMENTS', 2)
@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_api_corner_case)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_pagination_corner_case(mock_monitor_session, _mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_miss as the request content has the same
    # number of elements as the PER_PAGE_ELEMENTS and links content
    # is empty
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 2.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=requests.exceptions.Timeout)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_request_timeout(mock_monitor_session, _mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 502
    assert "Timeout" in response.data.decode("utf-8")


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_request_timeout_hit(mock_monitor_session, mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    mock_get.side_effect = requests.exceptions.Timeout
    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="API_TIMEOUT_HIT",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_request_5xx(mock_monitor_session, mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


    mock_get.side_effect = mocked_requests_get_error
    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="API_ERROR_HIT",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_request_5xx_miss(mock_monitor_session, mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


    mock_get.side_effect = mocked_requests_get_error
    response = client.get('/repos/app-sre/github-mirror/2',
                          follow_redirects=True)
    assert response.status_code == 500

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="API_ERROR_MISS",'
            'method="GET",status="500",user="None"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_request_connection_error_hit(mock_monitor_session, mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="ONLINE_HIT",'
            'method="GET",status="200",user="None"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)

    mock_get.side_effect = requests.exceptions.ConnectionError
    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="API_CONNECTION_ERROR_HIT",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="ONLINE_MISS",'
            'method="GET",status="200",user="None"} 1.0') in str(response.data)


@mock.patch('ghmirror.core.mirror_requests.requests.request',
            side_effect=mocked_requests_get_etag)
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
def test_mirror_request_connection_error_miss(mock_monitor_session, mock_get, client):
    setup_mocked_requests_session_get(mock_monitor_session, mocked_requests_monitor_good)
    mock_get.side_effect = requests.exceptions.ConnectionError
    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 502
