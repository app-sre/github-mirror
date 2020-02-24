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
Contains all the required verification
"""

import hashlib
import os

from functools import wraps

import flask

from ghmirror.core.constants import GH_API
from ghmirror.core.mirror_requests import conditional_request
from ghmirror.data_structures.monostate import UsersCache


AUTHORIZED_USERS = os.environ.get('GITHUB_USERS')


def check_user(function):
    """
    Checks whether the user is a member of one of the
    authorized organizations
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        # When the GITHUB_USERS is not set, we resume the normal
        # operation, where we do not check users
        if AUTHORIZED_USERS is None:
            return function(*args, **kwargs)

        authorized_users = AUTHORIZED_USERS.split(':')
        authorization = flask.request.headers.get('Authorization')
        # At this stage, Authorization header is mandatory
        if authorization is None:
            return flask.Response('Requires authentication', 401)

        users_cache = UsersCache()
        auth_sha = hashlib.sha1(authorization.encode()).hexdigest()
        # Users in cache were already checked and authorized,
        # so we just keep serving them
        if auth_sha in users_cache:
            return function(*args, **kwargs)

        # Using the Authorization header to get the user information
        user_url = f'{GH_API}/user'
        resp = conditional_request(method='GET', url=user_url,
                                   auth=authorization)

        # Fail early when Github API tells something is wrong
        if resp.status_code != 200:
            return flask.Response(resp.content, resp.status_code)

        user_login = resp.json()['login']
        # At this point we have the authorized_users list and the
        # user login from Github. If there's a match, we just
        # return the decorated function, but not before caching
        # the user for the next time
        if user_login in authorized_users:
            users_cache.add(auth_sha)
            return function(*args, **kwargs)

        # No match means user is forbidden
        doc_url = 'https://github.com/app-sre/github-mirror#user-validation'
        return flask.jsonify(message='User %s has no permission to use the '
                                     'github-mirror' % user_login,
                             documentation_url=doc_url), 403

    return wrapper
