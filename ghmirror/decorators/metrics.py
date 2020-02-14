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
Metrics decorators.
"""

import time

from functools import wraps

import flask

from ghmirror.data_structures.monostate import StatsCache


STATS_CACHE = StatsCache()


def requests_metrics(function):
    """
    Decorator to collect metrics from the request and populate the
    StatsCache object.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        start = time.time()
        response = function(*args, **kwargs)

        # This is the total time spent to process the request
        elapsed_time = (time.time() - start)

        # Incrementing the total requests couter
        STATS_CACHE.count()

        # The X-Cache header is added by the flask APP
        # and it contains either HIT or MISS
        cache = response.headers['X-Cache']

        # Adding the request metrics to the histogram
        STATS_CACHE.observe(cache=cache,
                            status=response.status_code,
                            value=elapsed_time,
                            method=flask.request.method)

        return response
    return wrapper
