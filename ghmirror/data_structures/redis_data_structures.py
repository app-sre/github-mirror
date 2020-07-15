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


PRIMARY_ENDPOINT = os.environ.get('PRIMARY_ENDPOINT', 'localhost')
READER_ENDPOINT = os.environ.get('READER_ENDPOINT', PRIMARY_ENDPOINT)
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
REDIS_TOKEN = os.environ.get('REDIS_TOKEN')
REDIS_SSL = os.environ.get('REDIS_SSL')


class RedisCache:
    """
    Dictionary-like implementation for caching requests in Redis.
    """
    def __init__(self):
        self.wr_cache = self._get_connection(PRIMARY_ENDPOINT)
        self.ro_cache = self._get_connection(READER_ENDPOINT)

    def __contains__(self, item):
        sr_key = self._serialize(item)
        return self.ro_cache.exists(sr_key)

    def __getitem__(self, item):
        sr_key = self._serialize(item)
        sr_value = self.ro_cache.get(sr_key)
        if sr_value is None:
            raise KeyError(item)
        return self._deserialize(sr_value)

    def __setitem__(self, key, value):
        sr_key = self._serialize(key)
        sr_value = self._serialize(value)
        self.wr_cache.set(sr_key, sr_value)

    def __iter__(self):
        return self._scan_iter()

    def __len__(self):
        return self.ro_cache.dbsize()

    def __sizeof__(self):
        return self.ro_cache.info()['used_memory']

    def _scan_iter(self):
        """
        Make an iterator so that the client doesn't need to remember
        the cursor position.
        """
        cursor = '0'
        while cursor != 0:
            cursor, data = self.wr_cache.scan(cursor)
            for item in data:
                yield self._deserialize(item)

    @staticmethod
    def _get_connection(host):
        parameters = {'host': host, 'port': REDIS_PORT}
        if REDIS_TOKEN is not None:
            parameters['password'] = REDIS_TOKEN
        if REDIS_SSL == 'True':
            parameters['ssl'] = True
        return redis.Redis(**parameters)

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
