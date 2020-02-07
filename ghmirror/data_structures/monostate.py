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

__all__ = ['RequestsCache', 'StatsCache']


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
        setattr(self, item, 0)
        return getattr(self, item)

    def hit(self):
        """
        Convenience method to increment the hits counter.
        """
        self.hits += 1

    def miss(self):
        """
        Convenience method to increment the misses counter.
        """
        self.misses += 1
