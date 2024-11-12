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

import os
from functools import wraps

import flask

from ghmirror.core.constants import GH_API
from ghmirror.core.mirror_requests import conditional_request
from ghmirror.data_structures.monostate import UsersCache
from ghmirror.utils.extensions import session

AUTHORIZED_USERS = os.environ.get("GITHUB_USERS")
DOC_URL = "https://github.com/app-sre/github-mirror#user-validation"


def check_user(function):
    """
    Checks whether the user is a member of one of the
    authorized organizations
    """

    @wraps(function)
    def wrapper(*args, **kwargs):
        # Need to check if the Authorization header is present
        # in the request to support anonymous user access
        authorization = flask.request.headers.get("Authorization")

        # When the GITHUB_USERS is not set and there's no Authorization header
        # we just return the decorated function to allow anonymous access
        if AUTHORIZED_USERS is None and authorization is None:
            return function(*args, **kwargs)

        # At this stage, Authorization header is mandatory
        if authorization is None:
            return (
                flask.jsonify(
                    message="Authorization header is required",
                    documentation_url=DOC_URL,
                ),
                401,
            )

        users_cache = UsersCache()
        # Users in cache were already checked and authorized,
        # so we just keep serving them
        if authorization in users_cache:
            return function(*args, **kwargs)

        # Using the Authorization header to get the user information
        user_url = f"{GH_API}/user"
        resp = conditional_request(
            session=session, method="GET", url=user_url, auth=authorization
        )

        # Fail early when Github API tells something is wrong
        if resp.status_code != 200:  # noqa: PLR2004
            return flask.Response(resp.content, resp.status_code)

        user_login = resp.json()["login"]

        # If the GITHUB_USERS is not set, we just cache the user
        # for the next time and return the decorated function
        if AUTHORIZED_USERS is None:
            users_cache.add(authorization, user_login)
            return function(*args, **kwargs)

        authorized_users = AUTHORIZED_USERS.split(":")

        # At this point we have the authorized_users list and the
        # user login from Github. If there's a match, we just
        # return the decorated function, but not before caching
        # the user for the next time
        if user_login in authorized_users:
            users_cache.add(authorization, user_login)
            return function(*args, **kwargs)

        # No match means user is forbidden
        return (
            flask.jsonify(
                message=f"User {user_login} has no permission to "
                "use the github-mirror",
                documentation_url=DOC_URL,
            ),
            403,
        )

    return wrapper
