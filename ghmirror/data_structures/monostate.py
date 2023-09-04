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

import os
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

from ghmirror.core.constants import GH_STATUS_API
from ghmirror.core.constants import STATUS_TIMEOUT


__all__ = ['GithubStatus', 'InMemoryCache', 'StatsCache', 'UsersCache']


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s')

LOG = logging.getLogger(__name__)


class _GithubStatus:

    def __init__(self, sleep_time, session):
        self.sleep_time = sleep_time
        self.online = True
        self.session = session
        self._start_check()

    def _start_check(self):
        """
        Starting a daemon thread to check the GitHub API status.
        daemon is required so the thread is killed when the main
        thread completes. This is also useful for the tests.
        """
        thread = threading.Thread(target=self.check, daemon=True)
        thread.start()

    @staticmethod
    def _is_github_online(response):
        """
        Check if the Github API is online based on the response.
        If API Requests component status is major_outage, then it's offline.
        If API Requests component status is one of operational,
        degraded_performance, or partial_outage, then it's online.
        """
        components = response.json()['components']
        return any(c['name'] == 'API Requests'
                   and c['status'] != 'major_outage'
                   for c in components)

    @classmethod
    def create(cls):
        """
        Class method to create a new instance of _GithubStatus.
        """
        sleep_time = int(os.environ.get("GITHUB_STATUS_SLEEP_TIME", 1))
        return cls(sleep_time, requests.Session())

    def check(self):
        """
        Method to be called in a thread. It will check the
        Github API status every self.sleep_time seconds and set
        the self.online accordingly.
        """
        while True:
            try:
                response = self.session.get(GH_STATUS_API,
                                            timeout=STATUS_TIMEOUT)
                response.raise_for_status()
                self.online = self._is_github_online(response)
                if not self.online:
                    LOG.warning('Github API is offline, response: %s',
                                response.text)
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.HTTPError) as error:
                LOG.warning('Github API is offline, reason: %s', error)
                self.online = False
            time.sleep(self.sleep_time)


class GithubStatus:
    """
    Monostate class for sharing the Github API Status.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def __new__(cls, *args, **kwargs):  # pylint: disable=unused-argument
        with cls._lock:
            if cls._instance is None:
                cls._instance = _GithubStatus.create()
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

    def get(self, key):
        """
        Getting the value from the backing dict
        """
        return self._data.get(self._sha(key))


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
                              labelnames=('cache', 'status', 'method', 'user'),
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

    def observe(self, cache, status, value, method, user):
        """
        Convenience method to populate the histogram.
        """
        self.histogram.labels(cache=cache, status=status,
                              method=method, user=user).observe(value)

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
