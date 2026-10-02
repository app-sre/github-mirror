"""Module to create a requests session that will be used to make all the requests to the GitHub API."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_retry = Retry(connect=1, read=False, redirect=0, status=0, raise_on_status=False)
session = requests.Session()
_adapter = HTTPAdapter(pool_connections=1, pool_maxsize=20, max_retries=_retry)
session.mount("https://", _adapter)
