from random import randint
from unittest import (
    TestCase,
    mock,
)

import pytest

from ghmirror.core.mirror_requests import (
    _get_elements_per_page,  # noqa: PLC2701
    _is_rate_limit_error,  # noqa: PLC2701
    _should_error_response_be_served_from_cache,  # noqa: PLC2701
)
from ghmirror.data_structures.monostate import StatsCache
from ghmirror.data_structures.requests_cache import RequestsCache

RAND_CACHE_SIZE = randint(100, 1000)


class TestStatsCache(TestCase):
    # pylint: disable=W0212
    def test_shared_state(self):
        stats_cache_01 = StatsCache()
        with pytest.raises(AttributeError) as e_info:
            stats_cache_01.foo
            self.assertIn("object has no attribute", e_info.message)
        self.assertEqual(stats_cache_01.counter._value._value, 0)

        stats_cache_01.count()
        stats_cache_01.count()

        self.assertEqual(stats_cache_01.counter._value._value, 2)

        stats_cache_02 = StatsCache()
        self.assertEqual(stats_cache_02.counter._value._value, 2)

        stats_cache_02.count()
        stats_cache_02.count()

        self.assertEqual(stats_cache_01.counter._value._value, 4)
        self.assertEqual(stats_cache_02.counter._value._value, 4)


class MockResponse:
    def __init__(self, content, headers, status_code, text):
        self.content = content.encode()
        self.headers = headers
        self.status_code = status_code
        self.text = text


class MockRedis:
    cache = {}

    def __init__(self, size=0):
        self.size = size

    def exists(self, item):
        return item in self.cache

    def get(self, item):
        if item in self.cache:
            return self.cache[item]
        return None

    def set(self, key, value, **_):
        self.cache[key] = value

    def _scan_iter(self):
        return iter(self.cache)

    def scan(self, *_args):
        return 0, iter(self.cache)

    def dbsize(self):
        return len(self.cache)

    def info(self):
        return {"used_memory": self.size}


def mocked_redis_cache(*_args, **_kwargs):
    return MockRedis(size=RAND_CACHE_SIZE)


class TestRequestsCache(TestCase):
    @mock.patch("ghmirror.data_structures.requests_cache.CACHE_TYPE", "redis")
    @mock.patch(
        "ghmirror.data_structures.redis_data_structures.REDIS_TOKEN", "mysecret"
    )
    @mock.patch("ghmirror.data_structures.redis_data_structures.REDIS_SSL", "True")
    @mock.patch(
        "ghmirror.data_structures.redis_data_structures.redis.Redis",
        side_effect=mocked_redis_cache,
    )
    def test_interface_redis(self, _mock_cache):
        requests_cache_01 = RequestsCache()
        requests_cache_01["foo"] = MockResponse(
            content="bar", headers={}, status_code=200, text=""
        )
        self.assertTrue(list(requests_cache_01))
        self.assertIn("foo", requests_cache_01)

        self.assertEqual(requests_cache_01["foo"].content, b"bar")
        self.assertEqual(requests_cache_01["foo"].status_code, 200)

        self.assertEqual(requests_cache_01.__sizeof__(), RAND_CACHE_SIZE)

        self.assertRaises(KeyError, lambda: requests_cache_01["bar"])

    @mock.patch("ghmirror.data_structures.requests_cache.CACHE_TYPE", "in-memory")
    def test_interface_in_memory(self):
        requests_cache_01 = RequestsCache()
        requests_cache_01["foo"] = MockResponse(
            content="bar", headers={}, status_code=200, text=""
        )
        self.assertTrue(list(requests_cache_01))
        self.assertIn("foo", requests_cache_01)

    @mock.patch("ghmirror.data_structures.requests_cache.CACHE_TYPE", "in-memory")
    def test_shared_state(self):
        requests_cache_01 = RequestsCache()
        requests_cache_01["foo"] = MockResponse(
            content="bar", headers={}, status_code=200, text=""
        )
        requests_cache_02 = RequestsCache()

        self.assertEqual(requests_cache_02["foo"].content, b"bar")
        self.assertEqual(requests_cache_02["foo"].status_code, 200)


class TestParseUrlParameters(TestCase):
    def test_url_params_empty(self):
        url_params = None
        self.assertIsNone(_get_elements_per_page(url_params))

    def test_url_params_no_per_page(self):
        url_params = {}
        self.assertIsNone(_get_elements_per_page(url_params))

    def test_url_params_per_page(self):
        url_params = {"per_page": 2}
        self.assertEqual(_get_elements_per_page(url_params), 2)


class TestIsRateLimitCondition(TestCase):
    def test_is_rate_limit_error_true(self):
        text = "You have triggered an abuse detection mechanism."
        resp = MockResponse(content="bar", headers={}, status_code=403, text=text)
        self.assertTrue(_is_rate_limit_error(resp))

    def test_is_rate_limit_error_false(self):
        text = "it's fine."
        resp = MockResponse(content="bar", headers={}, status_code=403, text=text)
        self.assertFalse(_is_rate_limit_error(resp))


class TestServeFromCacheCondition(TestCase):
    def test_should_serve_from_cache_rate_limit(self):
        text = "You have triggered an abuse detection mechanism."
        resp = MockResponse(content="bar", headers={}, status_code=403, text=text)
        header = _should_error_response_be_served_from_cache(resp)
        self.assertEqual(header, "RATE_LIMITED")

    def test_should_serve_from_cache_api_error(self):
        text = "it's fine."
        resp = MockResponse(content="bar", headers={}, status_code=500, text=text)
        header = _should_error_response_be_served_from_cache(resp)
        self.assertEqual(header, "API_ERROR")

    def test_should_serve_from_cache_ok(self):
        text = "it's fine."
        resp = MockResponse(content="bar", headers={}, status_code=200, text=text)
        header = _should_error_response_be_served_from_cache(resp)
        self.assertIsNone(header)
