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
Implements caching backend
"""

import os

from ghmirror.data_structures.monostate import InMemoryCache
from ghmirror.data_structures.redis_data_structures import RedisCache

CACHE_TYPE = os.environ.get("CACHE_TYPE", "in-memory")


class RequestsCache:
    """
    Instantiates either a InMemoryCache or a Redis Cache object
    """

    def __new__(cls, *args, **kwargs):
        if CACHE_TYPE == "redis":
            return RedisCache(*args, **kwargs)
        return InMemoryCache(*args, **kwargs)

    def __init__(self):  # pragma: no cover
        pass

    def __contains__(self, item):  # pragma: no cover
        pass

    def __getitem__(self, item):  # pragma: no cover
        pass

    def __setitem__(self, key, value):  # pragma: no cover
        pass

    def __iter__(self):  # pragma: no cover
        pass

    def __len__(self):  # pragma: no cover
        pass

    def __sizeof__(self):  # pragma: no cover
        pass
