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
The GitHub Mirror endpoints
"""

import hashlib
import logging

import flask
import requests

from prometheus_client import generate_latest

from ghmirror.app.response import MirrorResponse
from ghmirror.data_structures.monostate import RequestsCache
from ghmirror.data_structures.monostate import StatsCache
from ghmirror.decorators.metrics import requests_metrics


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s')

LOG = logging.getLogger(__name__)
GH_API = 'https://api.github.com'

APP = flask.Flask(__name__)


@APP.route('/healthz', methods=["GET"])
def healthz():
    """
    Health check endpoint for Kubernetes.
    """
    return flask.Response('OK')


@APP.route('/metrics', methods=["GET"])
def metrics():
    """
    Prometheus metrics endpoint.
    """
    headers = {'Content-type': 'text/plain'}
    return flask.Response(generate_latest(registry=StatsCache().registry),
                          200, headers)


@APP.route('/', defaults={'path': ''})
@APP.route('/<path:path>', methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@requests_metrics
def ghmirror(path):
    """
    Default endpoint, matching any url without a specific endpoint.
    """
    url = f'{GH_API}/{path}'

    if flask.request.args:
        url += '?'
        for key, value in flask.request.args.items():
            url += f'{key}={value}&'
        url = url.rstrip('&')

    headers = {}
    authorization = flask.request.headers.get('Authorization')
    auth_sha = None
    if authorization is not None:
        headers['Authorization'] = authorization
        # The authorization token will be used as cache key,
        # so let's hash it for additional security.
        auth_sha = hashlib.sha1(authorization.encode()).hexdigest()

    if flask.request.method != 'GET':
        LOG.info('[%s] BYPASS %s', flask.request.method, url)

        resp = requests.request(flask.request.method,
                                url=url,
                                headers=headers,
                                data=flask.request.data)

        return flask.Response(resp.content,
                              resp.status_code,
                              headers={'X-Cache': 'MISS'})

    cache = RequestsCache()

    cache_key = (url, auth_sha)
    if cache_key in cache:
        etag = cache[cache_key].headers.get('ETag')
        if etag is not None:
            headers['If-None-Match'] = etag
        last_mod = cache[cache_key].headers.get('Last-Modified')
        if last_mod is not None:
            headers['If-Modified-Since'] = last_mod

    resp = requests.request(flask.request.method,
                            url=url,
                            headers=headers)

    if resp.status_code != 304:
        LOG.info('[GET] CACHE_MISS %s', url)
        stats_cache.miss()
        # Caching only makes sense when at least one
        # of those headers is present
        if any(['ETag' in resp.headers,
                'Last-Modified' in resp.headers]):
            cache[cache_key] = resp
        mirror_response = MirrorResponse(original_response=resp,
                                         headers={'X-Cache': 'MISS'},
                                         gh_api_url=GH_API,
                                         gh_mirror_url=flask.request.host_url)
    else:
        LOG.info('[GET] CACHE_HIT %s', url)
        mirror_response = MirrorResponse(original_response=cache[cache_key],
                                         headers={'X-Cache': 'HIT'},
                                         gh_api_url=GH_API,
                                         gh_mirror_url=flask.request.host_url)

    return flask.Response(mirror_response.content,
                          mirror_response.status_code,
                          mirror_response.headers)


if __name__ == '__main__':  # pragma: no cover
    APP.run(host='127.0.0.1', debug=True, port='8080')
