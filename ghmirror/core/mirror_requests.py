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
Implements conditional requests
"""

import hashlib
import logging

import requests

from ghmirror.core.constants import REQUESTS_TIMEOUT
from ghmirror.data_structures.monostate import RequestsCache
from ghmirror.decorators.metrics import requests_metrics


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s')
LOG = logging.getLogger(__name__)


@requests_metrics
def conditional_request(method, url, auth, data=None):
    """
    Implements conditional requests
    """
    cache = RequestsCache()
    headers = {}
    if auth is None:
        auth_sha = None
    else:
        auth_sha = hashlib.sha1(auth.encode()).hexdigest()
        headers['Authorization'] = auth

    # Special case for non-GET requests
    if method != 'GET':
        # Just forward the request with the auth header
        resp = requests.request(method=method,
                                url=url,
                                headers=headers,
                                data=data,
                                timeout=REQUESTS_TIMEOUT)

        LOG.info('[%s] CACHE_MISS %s', method, url)
        # And just forward the response (with the
        # cache-miss header, for metrics)
        resp.headers['X-Cache'] = 'MISS'
        return resp

    cache_key = (url, auth_sha)

    cached_response = None
    if cache_key in cache:
        cached_response = cache[cache_key]
        etag = cached_response.headers.get('ETag')
        if etag is not None:
            headers['If-None-Match'] = etag
        last_mod = cached_response.headers.get('Last-Modified')
        if last_mod is not None:
            headers['If-Modified-Since'] = last_mod

    resp = requests.request(method=method, url=url, headers=headers,
                            timeout=REQUESTS_TIMEOUT)

    if resp.status_code == 304:
        LOG.info('[GET] CACHE_HIT %s', url)
        cached_response.headers['X-Cache'] = 'HIT'
        return cached_response

    LOG.info('[GET] CACHE_MISS %s', url)
    resp.headers['X-Cache'] = 'MISS'
    # Caching only makes sense when at least one
    # of those headers is present
    if any(['ETag' in resp.headers,
            'Last-Modified' in resp.headers]):
        cache[cache_key] = resp
    return resp
