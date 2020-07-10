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
from ghmirror.data_structures.monostate import GithubStatus
from ghmirror.data_structures.requests_cache import RequestsCache
from ghmirror.decorators.metrics import requests_metrics


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s')
LOG = logging.getLogger(__name__)


@requests_metrics
def conditional_request(method, url, auth, data=None):
    """
    Implements conditional requests, checking first whether
    the upstream API is online of offline to decide which
    request routine to call.
    """
    if GithubStatus().online:
        return online_request(method, url, auth, data)
    return offline_request(method, url, auth)


def online_request(method, url, auth, data=None):
    """
    Implements conditional requests.
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

        LOG.info('ONLINE %s CACHE_MISS %s', method, url)
        # And just forward the response (with the
        # cache-miss header, for metrics)
        resp.headers['X-Cache'] = 'ONLINE_MISS'
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
        LOG.info('ONLINE GET CACHE_HIT %s', url)
        cached_response.headers['X-Cache'] = 'ONLINE_HIT'
        return cached_response

    # When wen hit the API limit, let's try to serve from cache
    if resp.status_code == 403 and 'API rate limit exceeded' in resp.text:
        return offline_request(method=method, url=url, auth=auth,
                               error_code=resp.status_code,
                               error_message=resp.content)

    LOG.info('ONLINE GET CACHE_MISS %s', url)
    resp.headers['X-Cache'] = 'ONLINE_MISS'
    # Caching only makes sense when at least one
    # of those headers is present
    if any(['ETag' in resp.headers,
            'Last-Modified' in resp.headers]):
        cache[cache_key] = resp
    return resp


def offline_request(method, url, auth, error_code=504,
                    error_message=b'{"message": "gateway timeout"}\n'):
    """
    Implements offline requests (serves content from cache, when possible).
    """
    headers = {}
    if auth is None:
        auth_sha = None
    else:
        auth_sha = hashlib.sha1(auth.encode()).hexdigest()
        headers['Authorization'] = auth

    # Special case for non-GET requests
    if method != 'GET':
        LOG.info('OFFLINE %s CACHE_MISS %s', method, url)
        # Not much to do here. We just build up a response
        # with a reasonable status code so users know that our
        # upstream is offline
        response = requests.models.Response()
        response.status_code = error_code
        response.headers['X-Cache'] = 'OFFLINE_MISS'
        # pylint: disable=protected-access
        response._content = error_message
        return response

    cache = RequestsCache()
    cache_key = (url, auth_sha)
    if cache_key in cache:
        LOG.info('OFFLINE GET CACHE_HIT %s', url)
        # This is the best case: upstream is offline
        # but we have the resource in cache for a given
        # user. We then serve from cache.
        cached_response = cache[cache_key]
        cached_response.headers['X-Cache'] = 'OFFLINE_HIT'
        return cached_response

    LOG.info('OFFLINE GET CACHE_MISS %s', url)
    # GETs without cached content will receive an error
    # code so they know our upstream is offline.
    response = requests.models.Response()
    response.status_code = error_code
    response.headers['X-Cache'] = 'OFFLINE_MISS'
    # pylint: disable=protected-access
    response._content = error_message
    return response
