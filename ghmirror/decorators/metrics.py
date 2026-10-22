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

"""Metrics decorators."""

import time
from functools import wraps

import flask

from ghmirror.data_structures.monostate import (
    StatsCache,
    UsersCache,
    request_github_rtt,
)

STATS_CACHE = StatsCache()


def requests_metrics(function):
    """Collect metrics from the request and populate the StatsCache object."""

    @wraps(function)
    def wrapper(*args, **kwargs):
        token = request_github_rtt.set(0.0)
        start = time.perf_counter()
        try:
            response = function(*args, **kwargs)
        finally:
            github_rtt = request_github_rtt.get()
            request_github_rtt.reset(token)

        # This is the total time spent to process the request
        elapsed_time = time.perf_counter() - start

        # Incrementing the total requests counter
        STATS_CACHE.count()

        # The X-Cache header is added by the flask APP
        # and it contains either HIT or MISS
        cache = response.headers["X-Cache"]

        users_cache = UsersCache()
        authorization = flask.request.headers.get("Authorization")
        if authorization:
            user = users_cache.get(authorization)
            if not user:
                # This may be the first call to get /user
                # so users_cache is not yet updated
                # with the user to match the auth sha.
                # Try to get the user from the response.
                user = response.json().get("login")
        else:
            user = None

        # Adding the request metrics to the histogram
        STATS_CACHE.observe(
            cache=cache,
            status=response.status_code,
            value=elapsed_time,
            method=flask.request.method,
            user=user,
        )

        # New unified phase histogram (additive — keeps request_latency_seconds above alive)
        # All three phases share the same cache label and fire exactly once per request.
        STATS_CACHE.observe_github_latency(cache=cache, value=github_rtt)
        STATS_CACHE.observe_total_latency(cache=cache, value=elapsed_time)
        STATS_CACHE.observe_app_latency(
            cache=cache,
            value=max(0.0, elapsed_time - github_rtt),
        )

        return response

    return wrapper
