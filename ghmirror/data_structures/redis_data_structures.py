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

"""
Caching data in Redis.
"""

import os
import pickle
import redis


class RedisCache:
    """
    Dictionary-like implementation for caching requests in Redis.
    """
    def __init__(self):
        endpoint = os.environ.get('REDIS_ENDPOINT')
        port = os.environ.get('REDIS_PORT', 6379)
        password = os.environ.get('REDIS_TOKEN')
        self.cache = redis.Redis(
            host=endpoint,
            port=port,
            password=password,
            ssl=True)

    def __contains__(self, item):
        sr_key = self._serialize(item)
        return self.cache.exists(sr_key)

    def __getitem__(self, item):
        sr_key = self._serialize(item)
        sr_value = self.cache.get(sr_key)
        if sr_value is None:
            raise KeyError(item)
        return self._deserialize(sr_value)

    def __setitem__(self, key, value):
        sr_key = self._serialize(key)
        sr_value = self._serialize(value)
        self.cache.set(sr_key, sr_value)

    def __iter__(self):
        return self._scan_iter()

    def __len__(self):
        return self.cache.dbsize()

    def __sizeof__(self):
        return self.cache.info()['used_memory']

    def _scan_iter(self):
        """
        Make an iterator so that the client doesn't need to remember
        the cursor position.
        """
        cursor = '0'
        while cursor != 0:
            cursor, data = self.cache.scan(cursor)
            for item in data:
                yield self._deserialize(item)

    @staticmethod
    def _serialize(item):
        """ Serialize items for storage in Redis
        """
        return pickle.dumps(item)

    @staticmethod
    def _deserialize(item):
        """ Deserialize items stored in Redis
        """
        return pickle.loads(item)
