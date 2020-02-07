# GitHub Mirror

GitHub API mirror that caches the responses and implements
[conditional requests](https://developer.github.com/v3/#conditional-requests),
serving the client with the cached responses when the GitHub API replies with a
304 HTTP code, reducing the number of API calls, making a more efficient use of
the GitHub API rate limit.

The mirror acts only on GET requests, bypassing the other requests methods.

The cache is currently in-memory only, shared among all the threads, but not
shared between processes. Every time the server is started, the cache is
initialized empty.

Check the code:

```
$  make check
```

Run the development server:

```
$  make run-app
```

Using:

```
$ pipenv run python
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
>>> requests.get('http://localhost:8080/stats').json()
{'cache_hit': 1, 'cache_miss': 1}
```

Notice that requests to the `/stats` endpoint are not considered for cache
hit/miss statistics.

After those three requests, the server log will show:

```
2020-02-07 13:47:21,067 [GET] CACHE_MISS https://api.github.com/repos/app-sre/github-mirror
2020-02-07 13:47:21,069 127.0.0.1 - - [07/Feb/2020 13:47:21] "GET /repos/app-sre/github-mirror HTTP/1.1" 200 -
2020-02-07 13:47:30,938 [GET] CACHE_HIT https://api.github.com/repos/app-sre/github-mirror
2020-02-07 13:47:30,941 127.0.0.1 - - [07/Feb/2020 13:47:30] "GET /repos/app-sre/github-mirror HTTP/1.1" 200 -
2020-02-07 13:47:52,677 127.0.0.1 - - [07/Feb/2020 13:47:52] "GET /stats HTTP/1.1" 200 -
```

If you're using PyGithub, you just have to pass the `base_url` when creating
the client instance:

```
>>> from github import Github
>>> gh_cli = Github(base_url='http://localhost:8080')
```
