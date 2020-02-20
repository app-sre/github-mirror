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

import logging

import flask

from prometheus_client import generate_latest

from ghmirror.core.constants import GH_API
from ghmirror.core.mirror_response import MirrorResponse
from ghmirror.core.mirror_requests import conditional_request
from ghmirror.data_structures.monostate import StatsCache
from ghmirror.decorators.checks import check_user


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s')

LOG = logging.getLogger(__name__)

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
@check_user
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

    resp = conditional_request(method=flask.request.method,
                               url=url,
                               auth=flask.request.headers.get('Authorization'),
                               data=flask.request.data)

    mirror_response = MirrorResponse(original_response=resp,
                                     gh_api_url=GH_API,
                                     gh_mirror_url=flask.request.host_url)

    return flask.Response(mirror_response.content,
                          mirror_response.status_code,
                          mirror_response.headers)


if __name__ == '__main__':  # pragma: no cover
    APP.run(host='127.0.0.1', debug=True, port='8080')
