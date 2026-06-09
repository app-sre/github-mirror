import pytest

from ghmirror.data_structures.monostate import (
    GithubStatus,
    InMemoryCacheBorg,
    StatsCacheBorg,
    UsersCacheBorg,
)


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset all Borg/monostate singletons between tests.

    Previously handled implicitly by pytest-forked running each test
    in a separate process. Without forking, shared state leaks across
    tests and causes false failures.
    """
    yield
    InMemoryCacheBorg._state.clear()  # noqa: SLF001
    UsersCacheBorg._state.clear()  # noqa: SLF001
    StatsCacheBorg._state.clear()  # noqa: SLF001
    GithubStatus._instance = None  # noqa: SLF001
