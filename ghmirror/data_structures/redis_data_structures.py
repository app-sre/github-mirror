# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2020
# Author: Maha Ashour <mashour@redhat.com>

"""Caching data in Redis."""

import base64
import json
import os
from random import randint

import redis
from requests.models import Response
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers

PRIMARY_ENDPOINT = os.environ.get("PRIMARY_ENDPOINT", "localhost")
READER_ENDPOINT = os.environ.get("READER_ENDPOINT", PRIMARY_ENDPOINT)
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_TOKEN = os.environ.get("REDIS_TOKEN")
REDIS_SSL = os.environ.get("REDIS_SSL")


class RedisCache:
    """Dictionary-like implementation for caching requests in Redis."""

    def __init__(self):
        self.wr_cache = self._get_connection(PRIMARY_ENDPOINT)
        self.ro_cache = self._get_connection(READER_ENDPOINT)

    def __contains__(self, item):
        sr_key = self._serialize_key(item)
        return self.ro_cache.exists(sr_key)

    def __getitem__(self, item):
        sr_key = self._serialize_key(item)
        sr_value = self.ro_cache.get(sr_key)
        if sr_value is None:
            raise KeyError(item)
        return self._deserialize_response(sr_value)

    def __setitem__(self, key, value):
        sr_key = self._serialize_key(key)
        sr_value = self._serialize_response(value)
        # randomize cache expiration time (1 hr increments) from 1 hr to 6 mon
        rand_val = randint(1, 4320)
        self.wr_cache.set(sr_key, sr_value, ex=3600 * rand_val)

    def __iter__(self):
        return self._scan_iter()

    def __len__(self):
        return self.ro_cache.dbsize()

    def __sizeof__(self):
        return self.ro_cache.info()["used_memory"]

    def _scan_iter(self):
        """Make an iterator so that the client doesn't need to remember the cursor position."""
        cursor = "0"
        while cursor != 0:
            cursor, data = self.wr_cache.scan(cursor)
            for item in data:
                try:
                    yield self._deserialize_key(item)
                except json.JSONDecodeError:
                    # Entry written by a previous, pickle-based version of the
                    # cache. It will expire on its own; skip it.
                    continue

    @staticmethod
    def _get_connection(host):
        parameters = {"host": host, "port": REDIS_PORT}
        if REDIS_TOKEN is not None:
            parameters["password"] = REDIS_TOKEN
        if REDIS_SSL is not None and REDIS_SSL.lower() == "true":
            parameters["ssl"] = True
        return redis.Redis(**parameters)

    @staticmethod
    def _serialize_key(key):
        """Serialize a cache key for storage in Redis"""
        return json.dumps(key).encode()

    @staticmethod
    def _deserialize_key(key):
        """Deserialize a cache key stored in Redis"""
        return json.loads(key)

    @staticmethod
    def _serialize_response(response):
        """Serialize a requests.Response-like object for storage in Redis.

        Only the fields needed to rebuild the response are stored (as JSON),
        rather than pickling the object, so reading the cache can never
        trigger arbitrary code execution.
        """
        payload = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": base64.b64encode(response.content or b"").decode("ascii"),
        }
        return json.dumps(payload).encode()

    @staticmethod
    def _deserialize_response(item):
        """Rebuild a requests.Response from its JSON representation"""
        payload = json.loads(item)
        response = Response()
        response.status_code = payload["status_code"]
        response.headers = CaseInsensitiveDict(payload["headers"])
        response.encoding = get_encoding_from_headers(response.headers)
        response._content = base64.b64decode(payload["content"])  # noqa: SLF001
        return response
