from unittest import mock, TestCase
from random import randint

import pytest
import redis

from ghmirror.data_structures.requests_cache import RequestsCache
from ghmirror.data_structures.monostate import StatsCache


RAND_CACHE_SIZE = randint(100, 1000)


class TestStatsCache:

    def test_shared_state(self):
        stats_cache_01 = StatsCache()
        with pytest.raises(AttributeError) as e_info:
            stats_cache_01.foo
            assert 'object has no attribute' in e_info.message
        assert stats_cache_01.counter._value._value == 0

        stats_cache_01.count()
        stats_cache_01.count()

        assert stats_cache_01.counter._value._value == 2

        stats_cache_02 = StatsCache()
        assert stats_cache_02.counter._value._value == 2

        stats_cache_02.count()
        stats_cache_02.count()

        assert stats_cache_01.counter._value._value == 4
        assert stats_cache_02.counter._value._value == 4


class MockResponse:
    def __init__(self, content, headers, status_code):
        self.content = content.encode()
        self.headers = headers
        self.status_code = status_code

    def content(self):
        return self.content

    def headers(self):
        return self.headers

    def status_code(self):
        return self.status_code


class MockRedis:
    def __init__(self, size=0, alive=True, timeout=False, connected=True):
        self.cache = {}
        self.size = size
        self.alive = alive
        self.timeout = timeout
        self.connected = connected

    def exists(self, item):
        if self.connected:
            return item in self.cache
        raise redis.exceptions.ConnectionError

    def get(self, item):
        if item in self.cache:
            return self.cache[item]
        return None

    def set(self, key, value):
        self.cache[key] = value

    def _scan_iter(self):
        return iter(self.cache)

    def scan(self, *args):
        return 0, iter(self.cache)

    def dbsize(self):
        return len(self.cache)

    def info(self):
        return {'used_memory': self.size}

    def ping(self):
        if not self.alive:
            raise redis.exceptions.ConnectionError
        if self.timeout:
            raise redis.exceptions.TimeoutError

def mocked_redis_cache(*args, **kwargs):
    return MockRedis(size=RAND_CACHE_SIZE)

def mocked_connection_error(*args, **kwargs):
    return MockRedis(alive=False)

def mocked_timeout_error(*args, **kwargs):
    return MockRedis(timeout=True)

def mocked_dropped_connection(*args, **kwargs):
    return MockRedis(connected=False)

class TestRequestsCache(TestCase):

    @mock.patch('ghmirror.data_structures.requests_cache.CACHE_TYPE', 'redis')
    @mock.patch(
        'ghmirror.data_structures.redis_data_structures.redis.Redis',
        side_effect=mocked_redis_cache)
    def test_interface_redis(self, mock_cache):
        requests_cache_01 = RequestsCache()
        requests_cache_01['foo'] = MockResponse(content='bar',
                                                headers={},
                                                status_code=200)
        assert list(requests_cache_01)
        assert 'foo' in requests_cache_01

        assert requests_cache_01['foo'].content == 'bar'.encode()
        assert requests_cache_01['foo'].status_code == 200

        assert requests_cache_01.__sizeof__() == RAND_CACHE_SIZE
        
        self.assertRaises(KeyError, lambda: requests_cache_01['bar'])

    @mock.patch('ghmirror.data_structures.requests_cache.CACHE_TYPE', 'redis')
    @mock.patch(
        'ghmirror.data_structures.redis_data_structures.redis.Redis',
        side_effect=mocked_connection_error)
    def test_redis_connection(self, mock_cache):
        requests_cache_01 = RequestsCache()
        requests_cache_01['foo'] = MockResponse(content='bar',
                                                headers={},
                                                status_code=200)
        assert list(requests_cache_01)
        assert 'foo' in requests_cache_01

    @mock.patch('ghmirror.data_structures.requests_cache.CACHE_TYPE', 'redis')
    @mock.patch(
        'ghmirror.data_structures.redis_data_structures.redis.Redis',
        side_effect=mocked_timeout_error)
    def test_redis_timeout(self, mock_cache):
        requests_cache_01 = RequestsCache()
        requests_cache_01['foo'] = MockResponse(content='bar',
                                                headers={},
                                                status_code=200)
        assert list(requests_cache_01)
        assert 'foo' in requests_cache_01

    @mock.patch('ghmirror.data_structures.requests_cache.CACHE_TYPE', 'redis')
    @mock.patch(
        'ghmirror.data_structures.redis_data_structures.redis.Redis',
        side_effect=mocked_dropped_connection)
    def test_redis_dropped_connection(self, mock_cache):
        requests_cache_01 = RequestsCache()
        requests_cache_01['foo'] = MockResponse(content='bar',
                                                headers={},
                                                status_code=200)
        with self.assertRaises(redis.exceptions.ConnectionError):
            assert 'foo' in requests_cache_01

    @mock.patch('ghmirror.data_structures.requests_cache.CACHE_TYPE', 'in-memory')
    def test_interface_in_memory(self):
        requests_cache_01 = RequestsCache()
        requests_cache_01['foo'] = MockResponse(content='bar',
                                                headers={},
                                                status_code=200)
        assert list(requests_cache_01)
        assert 'foo' in requests_cache_01

    @mock.patch('ghmirror.data_structures.requests_cache.CACHE_TYPE', 'in-memory')
    def test_shared_state(self):
        requests_cache_01 = RequestsCache()
        requests_cache_01['foo'] = MockResponse(content='bar',
                                                headers={},
                                                status_code=200)        
        requests_cache_02 = RequestsCache()

        assert requests_cache_02['foo'].content == 'bar'.encode()
        assert requests_cache_02['foo'].status_code == 200
