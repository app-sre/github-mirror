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

"""Implements conditional requests"""

# ruff: noqa: PLR2004
import hashlib
import logging

import requests

from ghmirror.core.constants import (
    PER_PAGE_ELEMENTS,
    REQUESTS_TIMEOUT,
)
from ghmirror.data_structures.monostate import GithubStatus
from ghmirror.data_structures.requests_cache import RequestsCache
from ghmirror.decorators.metrics import requests_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
LOG = logging.getLogger(__name__)


def _get_elements_per_page(url_params):
    """Get 'per_page' parameter if present in URL or return None if not present"""
    if url_params is not None:
        per_page = url_params.get("per_page")
        if per_page is not None:
            return int(per_page)

    return None


def _cache_response(resp, cache, cache_key):
    """Cache response if it makes sense

    Implements the logic to decide whether or not whe should cache a request acording
    to the headers and content
    """
    # Caching only makes sense when at least one
    # of those headers is present
    if resp.status_code == 200 and any([
        "ETag" in resp.headers,
        "Last-Modified" in resp.headers,
    ]):
        cache[cache_key] = resp


def _online_request(
    session, method, url, cached_response, headers=None, parameters=None
):
    """Handle API errors on conditional requests and try to serve contents from cache"""
    try:
        resp = session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=REQUESTS_TIMEOUT,
            params=parameters,
        )

        # When we hit the API limit, or there is a problem with the API
        # let's try to serve from cache
        error_resp_header = _should_error_response_be_served_from_cache(resp)

        # If we didn't find any error in the API request, we return the
        # response directly to the next layer
        if error_resp_header is None:
            return resp

        if cached_response is None:
            LOG.info("%s GET CACHE_MISS %s", error_resp_header, url)
            resp.headers["X-Cache"] = error_resp_header + "_MISS"
            return resp

        LOG.info("%s GET CACHE_HIT %s", error_resp_header, url)
        cached_response.headers["X-Cache"] = error_resp_header + "_HIT"
        return cached_response

    except requests.exceptions.Timeout:
        if cached_response is None:
            raise

        LOG.info("API_TIMEOUT GET CACHE_HIT %s", url)
        cached_response.headers["X-Cache"] = "API_TIMEOUT_HIT"
        return cached_response

    except requests.exceptions.ConnectionError:
        if cached_response is None:
            raise

        LOG.info("API_CONNECTION_ERROR GET CACHE_HIT %s", url)
        cached_response.headers["X-Cache"] = "API_CONNECTION_ERROR_HIT"
        return cached_response


def _is_last_full_page(cached_response, per_page_elements) -> bool:
    """
    Check if the cached response is the last full page of a paginated response.

    The last full page is determined by checking if the number of elements in the cached response
    is same as the 'per_page' parameter and if there is no 'next' link in the response headers.
    If the endpoint does not support pagination, or if all results fit on a single page, the link header will be omitted.

    docs:
    * https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api?apiVersion=2022-11-28
    * https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api?apiVersion=2022-11-28#using-link-headers
    """
    if len(cached_response.json()) != per_page_elements:
        return False
    if (links := cached_response.links) and links.get("next"):  # noqa: SIM103
        return False
    return True


def _handle_not_changed(
    session,
    cached_response,
    per_page_elements,
    headers,
    method,
    url,
    parameters,
    cache,
    cache_key,
):
    """
    Handle 304 Not Modified responses from the API.

    If the cached response is the last full page of a paginated response,
    we need to revalidate the cache by making a new request without
    conditional headers. Otherwise, we can return the cached response.
    This is to ensure that we are not serving stale data due to weak etag,
    response links header can change even if the content did not change.
    """
    if _is_last_full_page(cached_response, per_page_elements):
        headers.pop("If-None-Match", None)
        headers.pop("If-Modified-Since", None)
        resp = session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=REQUESTS_TIMEOUT,
            params=parameters,
        )

        LOG.info("ONLINE GET CACHE_MISS %s", url)
        resp.headers["X-Cache"] = "ONLINE_MISS"
        _cache_response(resp, cache, cache_key)
        return resp

    LOG.info("ONLINE GET CACHE_HIT %s", url)
    cached_response.headers["X-Cache"] = "ONLINE_HIT"
    return cached_response


@requests_metrics
def conditional_request(session, method, url, auth, data=None, url_params=None):
    """Implements conditional requests.

    Checking first whether the upstream API is online of offline to decide which
    request routine to call.
    """
    if GithubStatus().online:
        return online_request(session, method, url, auth, data, url_params)
    return offline_request(method, url, auth)


def online_request(session, method, url, auth, data=None, url_params=None):
    """Implements conditional requests."""
    cache = RequestsCache()
    headers = {}
    parameters = url_params.to_dict() if url_params is not None else {}

    per_page_elements = _get_elements_per_page(url_params)

    if per_page_elements is None:
        per_page_elements = PER_PAGE_ELEMENTS
        parameters["per_page"] = PER_PAGE_ELEMENTS

    if auth is None:
        auth_sha = None
    else:
        auth_sha = hashlib.sha1(auth.encode()).hexdigest()
        headers["Authorization"] = auth

    # Special case for non-GET requests
    if method != "GET":
        # Just forward the request with the auth header
        resp = session.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            timeout=REQUESTS_TIMEOUT,
            params=parameters,
        )

        LOG.info("ONLINE %s CACHE_MISS %s", method, url)
        # And just forward the response (with the
        # cache-miss header, for metrics)
        resp.headers["X-Cache"] = "ONLINE_MISS"
        return resp

    cache_key = (url, auth_sha)

    cached_response = None
    if cache_key in cache:
        cached_response = cache[cache_key]
        etag = cached_response.headers.get("ETag")
        if etag is not None:
            headers["If-None-Match"] = etag
        last_mod = cached_response.headers.get("Last-Modified")
        if last_mod is not None:
            headers["If-Modified-Since"] = last_mod

    resp = _online_request(
        session=session,
        method=method,
        url=url,
        headers=headers,
        parameters=parameters,
        cached_response=cached_response,
    )

    if resp.status_code == 304:
        return _handle_not_changed(
            session,
            cached_response,
            per_page_elements,
            headers,
            method,
            url,
            parameters,
            cache,
            cache_key,
        )

    # This section covers the log and the headers logic when we don't have
    # any error on the _online_request method, and the response from the
    # Github API is returned.
    if "X-Cache" not in resp.headers:
        LOG.info("ONLINE GET CACHE_MISS %s", url)
        resp.headers["X-Cache"] = "ONLINE_MISS"
        _cache_response(resp, cache, cache_key)

    return resp


def _should_error_response_be_served_from_cache(response):
    """Parse a response to check if we should serve contents from cache

    :param response: requests module response
    :type response: requests.Response

    :return: The headers that we should return on the request if served
        from cache
    :rtype: str, optional
    """
    if _is_rate_limit_error(response):
        return "RATE_LIMITED"

    if response.status_code >= 500 and response.status_code < 600:
        return "API_ERROR"

    return None


def _is_rate_limit_error(response):
    """Try to serve response from the cache when we hit API limit

    :param response: requests module response
    :type response: requests.Response
    """
    rate_limit_messages = {
        "API rate limit exceeded",
        "secondary rate limit",
        "abuse detection mechanism",
    }
    return response.status_code == 403 and any(
        m in response.text for m in rate_limit_messages
    )


def offline_request(
    method, url, auth, error_code=504, error_message=b'{"message": "gateway timeout"}\n'
):
    """Implements offline requests (serves content from cache, when possible)."""
    headers = {}
    if auth is None:
        auth_sha = None
    else:
        auth_sha = hashlib.sha1(auth.encode()).hexdigest()
        headers["Authorization"] = auth

    # Special case for non-GET requests
    if method != "GET":
        LOG.info("OFFLINE %s CACHE_MISS %s", method, url)
        # Not much to do here. We just build up a response
        # with a reasonable status code so users know that our
        # upstream is offline
        response = requests.models.Response()
        response.status_code = error_code
        response.headers["X-Cache"] = "OFFLINE_MISS"
        response._content = error_message  # noqa: SLF001
        return response

    cache = RequestsCache()
    cache_key = (url, auth_sha)
    if cache_key in cache:
        LOG.info("OFFLINE GET CACHE_HIT %s", url)
        # This is the best case: upstream is offline
        # but we have the resource in cache for a given
        # user. We then serve from cache.
        cached_response = cache[cache_key]
        cached_response.headers["X-Cache"] = "OFFLINE_HIT"
        return cached_response

    LOG.info("OFFLINE GET CACHE_MISS %s", url)
    # GETs without cached content will receive an error
    # code so they know our upstream is offline.
    response = requests.models.Response()
    response.status_code = error_code
    response.headers["X-Cache"] = "OFFLINE_MISS"
    response._content = error_message  # noqa: SLF001
    return response
