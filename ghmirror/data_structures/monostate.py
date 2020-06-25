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

import sys

from prometheus_client import CollectorRegistry
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import ProcessCollector


__all__ = ['RequestsCache', 'StatsCache', 'UsersCache']


class RequestsCacheBorg:
    """
    Monostate class for sharing the requests cache.
    """
    _state = {}

    def __init__(self):
        self.__dict__ = self._state


class RequestsCache(RequestsCacheBorg):
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
        return self._data[item]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __iter__(self):
        return iter(self._data)

    def __sizeof__(self):
        return sys.getsizeof(self._data)


class UsersCacheBorg:
    """
    Monostate class for sharing the users cache.
    """
    _state = {}

    def __init__(self):
        self.__dict__ = self._state


class UsersCache(UsersCacheBorg):
    """
    Set-like implementation for caching users information.
    """
    def __getattr__(self, item):
        """
        Safe class argument initialization. We do it here
        (instead of in the __init__()) so we don't overwrite
        them when a new instance is created.
        """
        setattr(self, item, set())
        return getattr(self, item)

    def __contains__(self, item):
        return item in self._data

    def add(self, value):
        """
        Adding the value to the backing set
        """
        self._data.add(value)


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
