# GitHub Mirror

GitHub API mirror that caches the responses and implements
[conditional requests](https://developer.github.com/v3/#conditional-requests),
serving the client with the cached responses when the GitHub API replies with a
304 HTTP code, reducing the number of API calls, making a more efficient use of
the GitHub API rate limit.

The mirror acts only on GET requests, by-passing the other requests methods.

The cache is currently in-memory only, shared among all the threads, but not
shared between processes. Every time the server is started, the cache is
initialized empty.

## Use

Build the Docker image:

```
$ docker build -t github-mirror .
```

Run the Docker container:

```
$ docker run --rm -p 8080:8080 github-mirror
[2020-02-16 21:06:04 +0000] [1] [INFO] Starting gunicorn 20.0.4
[2020-02-16 21:06:04 +0000] [1] [INFO] Listening at: http://0.0.0.0:8080 (1)
[2020-02-16 21:06:04 +0000] [1] [INFO] Using worker: threads
[2020-02-16 21:06:04 +0000] [8] [INFO] Booting worker with pid: 8
```

Use it as Github API url:

```
$ python
Python 3.6.10 (default, Dec 20 2019, 00:00:00)
[GCC 9.2.1 20190827 (Red Hat 9.2.1-1)] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
>>> import requests
>>> requests.get('http://localhost:8080/repos/app-sre/github-mirror')
<Response [200]>
>>>
>>> requests.get('http://localhost:8080/repos/app-sre/github-mirror')
<Response [200]>
>>>
```

After those two requests, the server log will show:

```
$ docker run --rm -p 8080:8080 github-mirror
[2020-02-16 21:06:04 +0000] [1] [INFO] Starting gunicorn 20.0.4
[2020-02-16 21:06:04 +0000] [1] [INFO] Listening at: http://0.0.0.0:8080 (1)
[2020-02-16 21:06:04 +0000] [1] [INFO] Using worker: threads
[2020-02-16 21:06:04 +0000] [8] [INFO] Booting worker with pid: 8
2020-02-16 21:08:07,948 [GET] CACHE_MISS https://api.github.com/repos/app-sre/github-mirror
2020-02-16 21:08:13,585 [GET] CACHE_HIT https://api.github.com/repos/app-sre/github-mirror
```

If you're using PyGithub, you have to pass the `base_url` when creating
the client instance:

```
>>> from github import Github
>>> gh_cli = Github(base_url='http://localhost:8080')
```

## Metrics

The service has a `/metrics` endpoint, exposing metrics in the Prometheus
format:

```
>>> response = requests.get('http://localhost:8080/metrics')
>>> print(response.content.decode())
...
http_request_total 2.0
...
request_latency_seconds_count{cache="MISS",method="GET",status="200"} 1.0
...
request_latency_seconds_count{cache="HIT",method="GET",status="200"} 1.0
...
```

## Develop

Install the development requirements:

```
$  make develop
```

Run the code checks and tests:

```
$  make check
```

Run the development server:

```
$  make run
```

## User Validation

To enable the user validation, the `GITHUB_USERS` environment variable
should be available to the server. The `GITHUB_USERS` is a colon-separated
list of authorized users to have their requests to the Github Mirror served.

The user validation, when enabled, will not allow unauthenticated requests
to the Github Mirror.

Please notice that, in order to validate the user, one additional get request
is made to the Github API, to the `/user` endpoint, using the provided
authorization token. That call will also go through the caching mechanism, so
the rate limit will be preserved when possible.
