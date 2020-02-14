from unittest import mock

import pytest

from ghmirror.app import APP


def mocked_requests_get_etag(*args, **kwargs):
    class MockResponse:
        def __init__(self, content, headers, status_code):
            self.content = content.encode()
            self.headers = headers
            self.status_code = status_code

    if 'If-Modified-Since' in kwargs['headers']:
        return MockResponse('', {}, 304)

    if 'If-None-Match' in kwargs['headers']:
        return MockResponse('', {}, 304)

    return MockResponse('', {'ETag': 'foo'}, 200)


def mocked_requests_get_last_modified(*args, **kwargs):
    class MockResponse:
        def __init__(self, content, headers, status_code):
            self.content = content.encode()
            self.headers = headers
            self.status_code = status_code

    if 'If-Modified-Since' in kwargs['headers']:
        return MockResponse('', {}, 304)

    if 'If-None-Match' in kwargs['headers']:
        return MockResponse('', {}, 304)

    return MockResponse('', {'Last-Modified': 'bar'}, 200)


@pytest.fixture
def client():
    APP.config['TESTING'] = True

    with APP.test_client() as client:
        yield client


def test_healthz(client):
    response = client.get('/healthz', follow_redirects=True)
    assert response.status_code == 200
    assert response.data == b'OK'


@mock.patch('ghmirror.app.requests.request',
            side_effect=mocked_requests_get_etag)
def test_mirror_etag(mock_get, client):
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="MISS",'
            'method="GET",status="200"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="HIT",'
            'method="GET",status="200"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)


@mock.patch('ghmirror.app.requests.request',
            side_effect=mocked_requests_get_last_modified)
def test_mirror_last_modified(mock_get, client):
    # Initially the stats are zeroed
    response = client.get('/metrics')
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="MISS",'
            'method="GET",status="200"}') not in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # First get is a cache_miss
    response = client.get('/metrics', follow_redirects=True)

    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="HIT",'
            'method="GET",status="200"}') not in str(response.data)
    assert ('request_latency_seconds_count{cache="MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)

    response = client.get('/repos/app-sre/github-mirror',
                          follow_redirects=True)
    assert response.status_code == 200

    # Second get is a cache_hit
    response = client.get('/metrics', follow_redirects=True)
    assert response.status_code == 200
    assert ('request_latency_seconds_count{cache="HIT",'
            'method="GET",status="200"} 1.0') in str(response.data)
    assert ('request_latency_seconds_count{cache="MISS",'
            'method="GET",status="200"} 1.0') in str(response.data)


@mock.patch('ghmirror.app.requests.request',
            side_effect=mocked_requests_get_last_modified)
def test_mirror_upstream_call(mock_get, client):
    client.get('/user/repos?page=2',
               headers={'Authorization': 'foo'})
    mock_get.assert_called_with('GET', headers={'Authorization': 'foo'},
                                url='https://api.github.com/user/repos?page=2')


@mock.patch('ghmirror.app.requests.request',
            side_effect=mocked_requests_get_last_modified)
def test_mirror_non_get(mock_get, client):
    client.patch('/repos/foo/bar',
                 data=b'foo')
    mock_get.assert_called_with('PATCH', data=b'foo', headers={},
                                url='https://api.github.com/repos/foo/bar')
