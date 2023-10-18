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
Module containing all the abstractions around an HTTP response.
"""


class MirrorResponse:
    """
    Wrapper around the requests.Response, implementing properties
    that replace the strings containing the GutHub API url by the
    mirror url where needed.

    :param original_response: the return from the original request
                              to the GitHub API
    :param gh_api_url: the GitHub API url (with the scheme)
    :param gh_mirror_url: the GitHub Mirror url (with the scheme)

    :type original_response: requests.Response
    :type gh_api_url: str
    :type gh_mirror_url: str
    """
    def __init__(self, original_response, gh_api_url, gh_mirror_url):
        self._original_response = original_response
        self._gh_api_url = gh_api_url.rstrip('/')
        self._gh_mirror_url = gh_mirror_url.rstrip('/')

    @property
    def headers(self):
        """
        Retrieves the headers we are interested in from the original
        response and sanitizes them so we can impersonate the GitHub
        API.

        :return: the sanitized headers
        :rtype: dict
        """
        sanitized_headers = {}

        x_cache = self._original_response.headers.get('X-Cache')
        if x_cache is not None:
            sanitized_headers['X-Cache'] = x_cache

        link = self._original_response.headers.get('Link')
        if link is not None:
            sanitized_headers['Link'] = link.replace(
                self._gh_api_url,
                self._gh_mirror_url
            )

        content_type = self._original_response.headers.get('Content-Type')
        if content_type is not None:
            sanitized_headers['Content-Type'] = content_type

        last_modified = self._original_response.headers.get('Last-Modified')
        if last_modified is not None:
            sanitized_headers['Last-Modified'] = last_modified

        etag = self._original_response.headers.get('ETag')
        if etag is not None:
            sanitized_headers['ETag'] = etag

        return sanitized_headers

    @property
    def content(self):
        """
        Retrieves the content from the original response and sanitizes
        them so we can impersonate the GitHub API.

        :return: the sanitized content
        :rtype: bytes
        """
        if self._original_response.content is None:
            return None

        sanitized_content = self._original_response.content.replace(
            self._gh_api_url.encode(),
            self._gh_mirror_url.encode()
        )

        return sanitized_content

    @property
    def status_code(self):
        """
        Convenience method to expose the original response HTTP
        status code.

        :return: the response status code
        """
        return self._original_response.status_code
