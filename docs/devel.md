# Preparing

## Fork the repository

Go to https://github.com/app-sre/github-mirror, on the top-right corner,
click "Fork" and confirm the fork to your user.

That will give you a copy of the repository under your user. The resulting
repository url will be `https://github.com/<user>/github-mirror`.

## Clone from your fork

The git repository on your local machine has to be cloned from your fork.
That's because you can create branches on your fork and propose Pull Requests
from them, but you can't always create branches on the main repository. This is
known as [fork workflow](https://dev.to/mathieuks/introduction-to-github-fork-workflow-why-is-it-so-complex-3ac8).

Clone with:

```
user@localhost:~$ git clone git@github.com:<user>/github-mirror.git
```

## Setup your local repository

Your local repository will have a `remote` already in place:

```
user@localhost:~$ cd github-mirror
user@localhost:~/github-mirror$ git remote -v
origin  git@github.com:<user>/github-mirror.git (fetch)
origin  git@github.com:<user>/github-mirror.git (push)
```

`origin` points to your fork. Now you have to add the main repository as
another `remote`. That is useful to sync the changes from the main repository
into your local repository and into your fork.

Add it with:

```
user@localhost:~/github-mirror$ git remote add upstream git@github.com:app-sre/github-mirror.git
```

After that command, you will see two remotes:

```
user@localhost:~/github-mirror$ git remote -v
origin  git@github.com:<user>/github-mirror.git (fetch)
origin  git@github.com:<user>/github-mirror.git (push)
upstream  git@github.com:app-sre/github-mirror.git (fetch)
upstream  git@github.com:app-sre/github-mirror.git (push)
```

Now `upstream` points to the main repository.

## Create a Python virtual environment:

You need python - at least - v3.6. You can check the right version with:

```
user@localhost:~/github-mirror$ python --version
```

and

```
user@localhost:~/github-mirror$ python3 --version
```

Whatever is the right one, use it to create the virtual environment:

```
user@localhost:~/github-mirror$ python -m venv venv
```

That will use the python module `venv` to create a directory called `venv`
with your virtual environment.

Activate the virtual environment with:

```
user@localhost:~/github-mirror$ source venv/bin/activate
```

From now on, everything you install with `pip` will be installed in that
directory and will be only available when it's activated.

To exit the virtual environment, use:

```
(venv) user@localhost:~/github-mirror$ deactivate
```

## Install the python package in development mode

Activate the virtual environment:

```
user@localhost:~/github-mirror$ source venv/bin/activate
```

Install the package with:

```
(venv) user@localhost:~/github-mirror$ pip install --editable .
```

Install the check requirements with:

```
(venv) user@localhost:~/github-mirror$ pip install -r requirements-check.txt
```

##  Run the service

To start the service in development mode, use:

```
(venv) user@localhost:~/github-mirror$ python ghmirror/app/__init__.py
 * Serving Flask app "__init__" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
2020-06-08 15:08:58,704  * Running on http://127.0.0.1:8080/ (Press CTRL+C to quit)
2020-06-08 15:08:58,707  * Restarting with stat
2020-06-08 15:08:59,062  * Debugger is active!
2020-06-08 15:08:59,062  * Debugger PIN: 279-042-762
```

## Run your requests against the github-mirror

From a different terminal, just replace `https://api.github.com` by
`http://localhost:8080`:

```
user@localhost:~$ curl http://localhost:8080/repos/app-sre/sretoolbox
...
```

The service log will show:

```
2020-06-08 15:12:39,475 [GET] CACHE_MISS https://api.github.com/repos/app-sre/sretoolbox
2020-06-08 15:12:39,478 127.0.0.1 - - [08/Jun/2020 15:12:39] "GET /repos/app-sre/sretoolbox HTTP/1.1" 200 -
```

## Run github-mirror in Redis backed mode (optional)

When running in Redis mode, github-mirror will cache all requests in a Redis server instead of locally in-memory. This enables multiple instances of github-mirror to access and maintain a single shared cache.

First, you will need to tell github-mirror to run in Redis mode by setting the `CACHE_TYPE` environment variable. If the variable is not set, github mirror will run in the default in-memory cache mode.

```
user@localhost:~$ export CACHE_TYPE=redis
```

### Running Redis
If you already have Redis installed, use a different terminal to run the Redis server. By default Redis will run at address `locahost` and port `6379`:
```
user@localhost:~$ redis-server
```
Alternatively, you can run Redis in a Docker container (you may need to run docker as root):

```
user@localhost:~$ docker run --rm -it -p 6379:6379 redis
```

You can now test the Redis backed github mirror as [before](#run-your-requests-against-the-github-mirror).

### Additional configurations

You can optionally set the following environment variables, to configure the connection to the Redis server:
```
user@localhost:~$ export PRIMARY_ENDPOINT=<redis.primary.endpoint>
user@localhost:~$ export READER_ENDPOINT=<redis.reader.endpoint>
user@localhost:~$ export REDIS_PORT=<port>
user@localhost:~$ export REDIS_PASSWORD=<mysecret>
user@localhost:~$ export REDIS_SSL=True
```

# Coding

## Create a new local branch

You should never commit to your local master.

Before start coding, get the latest changes from upstream/master. First, make
sure your're on your local master:

```
(venv) user@localhost:~/github-mirror$ git branch
* master
```

Then get all new commits from upstream master:

```
(venv) user@localhost:~/github-mirror$ git pull upstream master
```

Then checkout to a new branch:

```
(venv) user@localhost:~/github-mirror$ git checkout -b new_feature_01
```

## Running the checks and tests

To run the code checks, use:

```
(venv) user@localhost:~/github-mirror$ flake8 ghmirror
```

and

```
(venv) user@localhost:~/github-mirror$ flake8 ghmirror
```

To run the tests, use:

```
(venv) user@localhost:~/github-mirror$ pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/
```

Those are all the checks and tests execute by the CI, so if they pass on your
local machine, they are expected to pass in the CI pipeline.

## Commit your changes

When the time comes, commit your changes:

```
(venv) user@localhost:~/github-mirror$ git commit -a -m "Adding feature 01"
```

Create as many commits as you need. All commits are local up to this point.

## Push your changes

You will now push your changes to your fork. To do that, run:

```
(venv) user@localhost:~/github-mirror$ git push
```

If this is the first time you push from this branch, you will see a message
showing the actual push command you need to execute the first time:

```
fatal: The current branch demo has no upstream branch.
To push the current branch and set the remote as upstream, use

    git push --set-upstream origin new_feature_01
```

Run that command:

```
(venv) user@localhost:~/github-mirror$ git push --set-upstream origin new_feature_01
```

Next time you want to push commits from this branch, just use `git push`.

## Pull Requests

Create a Pull Request from your fork's feature branch to the main repository's
master branch using the Web UI.

Keep up with the review, adding new commits to your local branch and pushing
them using `git push`. That will automatically update the pull request.
