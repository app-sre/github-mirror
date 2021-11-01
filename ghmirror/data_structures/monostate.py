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
# Author: Amador Pahim <apahim@redhat.com>

"""
Caching data structures.
"""

import threading
import time
import logging
import pickle
import sys
import hashlib

import requests

from prometheus_client import CollectorRegistry
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import ProcessCollector

from ghmirror.core.constants import GH_API
from ghmirror.core.constants import STATUS_TIMEOUT


__all__ = ['GithubStatus', 'InMemoryCache', 'StatsCache', 'UsersCache']


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s')

LOG = logging.getLogger(__name__)


class _GithubStatus:

    SLEEP_TIME = 1

    def __init__(self):
        self.online = True
        theard = threading.Thread(target=self.check)
        theard.start()

    def check(self):
        """
        Method to be called in a thread. It will check the
        Github API status every SLEEP_TIME seconds and set
        the self.online accordingly.
        """
        while True:
            try:
                response = requests.get(f'{GH_API}/status',
                                        timeout=STATUS_TIMEOUT)
                response.raise_for_status()
                self.online = True
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.HTTPError):
                self.online = False
            time.sleep(self.SLEEP_TIME)


class GithubStatus:
    """
    Monostate class for sharing the Github API Status.
    """

    _instance = None

    @classmethod
    def __new__(cls, *args, **kwargs):  # pylint: disable=unused-argument
        if cls._instance is None:
            cls._instance = _GithubStatus()
        return cls._instance


class InMemoryCacheBorg:
    """
    Monostate class for sharing the in-memory requests cache.
    """
    _state = {}

    def __init__(self):
        self.__dict__ = self._state


class InMemoryCache(InMemoryCacheBorg):
    """
    Dictionary-like implementation for caching requests.
    """
    def __getattr__(self, item):
        """
        Safe class argument initialization. We do it here
        (instead of in the __init__()) so we don't overwrite
        them on when a new instance is created.
        """
        setattr(self, item, dict())
        return getattr(self, item)

    def __contains__(self, item):
        return item in self._data

    def __getitem__(self, item):
        return self._data[item]['data']

    def __setitem__(self, key, value):
        """ Set the key-value pair as well as their total size
        """
        key_size = sys.getsizeof(pickle.dumps(key))
        value_size = sys.getsizeof(pickle.dumps(value))
        self._data[key] = {'data': value, 'size': key_size + value_size}

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __sizeof__(self):
        """ Calculate the size of the dictionary and all its contents
        """
        total_cache_size = sys.getsizeof(self._data)
        for value in self._data.values():
            total_cache_size += value['size']
        return total_cache_size


class UsersCacheBorg:
    """
    Monostate class for sharing the users cache.
    """
    _state = {}

    def __init__(self):
        self.__dict__ = self._state


class UsersCache(UsersCacheBorg):
    """
    Dict-like implementation for caching users information.
    """
    def __getattr__(self, item):
        """
        Safe class argument initialization. We do it here
        (instead of in the __init__()) so we don't overwrite
        them when a new instance is created.
        """
        setattr(self, item, dict())
        return getattr(self, item)

    @staticmethod
    def _sha(key):
        return hashlib.sha1(key.encode()).hexdigest()

    def __contains__(self, item):
        return self._sha(item) in self._data

    def add(self, key, value=None):
        """
        Adding the value to the backing dict
        """
        self._data[self._sha(key)] = value


class StatsCacheBorg:
    """
    Monostate class for sharing the Statistics.
    """
    _state = {}

    def __init__(self):
        self.__dict__ = self._state


class StatsCache(StatsCacheBorg):
    """
    Statistics cacher.
    """
    def __getattr__(self, item):
        """
        Safe class argument initialization. We do it here
        (instead of in the __init__()) so we don't overwrite
        them on when a new instance is created.
        """
        if item == 'registry':
            # This will create the self.registry attribute, which
            # contains an instance of the CollectorRegistry.
            setattr(self, item, CollectorRegistry())
            # Adding a ProcessCollector to the registry. The
            # ProcessCollector does not have to be an attribute,
            # since it's never manipulated  directly.
            ProcessCollector(registry=self.registry)

        elif item == 'histogram':
            # Adding a Histogram to the registry and also making
            # the Histogram available as an attribute so we can
            # call its observe()
            setattr(self, item,
                    Histogram(name='request_latency_seconds',
                              labelnames=('cache', 'status', 'method'),
                              documentation='request latency histogram',
                              registry=self.registry))
        elif item == 'counter':
            # Adding a Counter to the registry and also making
            # the Counter available as an attribute so we can
            # call its inc()
            setattr(self, item,
                    Counter(name='http_request',
                            documentation='total requests',
                            registry=self.registry))

        elif item == 'gauge_cache_size':
            setattr(self, item,
                    Gauge(name='github_mirror_cache_size',
                          documentation='cache size in bytes',
                          registry=self.registry))

        elif item == 'gauge_cached_objects':
            setattr(self, item,
                    Gauge(name='github_mirror_cached_objects',
                          documentation='number of cached objects',
                          registry=self.registry))

        else:
            raise AttributeError(f"object has no attribute {item}'")

        return getattr(self, item)

    def count(self):
        """
        Convenience method to increment the counter.
        """
        self.counter.inc(1)

    def observe(self, cache, status, value, method):
        """
        Convenience method to populate the histogram.
        """
        self.histogram.labels(cache=cache, status=status,
                              method=method).observe(value)

    def set_cache_size(self, value):
        """
        Convenience method to set the Gauge.
        """
        self.gauge_cache_size.set(value)

    def set_cached_objects(self, value):
        """
        Convenience method to set the Gauge.
        """
        self.gauge_cached_objects.set(value)
