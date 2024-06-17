from unittest import mock

import pytest
import requests

from ghmirror.data_structures.monostate import (
    GithubStatus,
    _GithubStatus,  # noqa: PLC2701
)

EXPECTED_TIMEOUT = 10
EXPECTED_SLEEP_TIME = 1


@mock.patch("ghmirror.data_structures.monostate.threading.Thread")
def test_create_github_status_singleton(_mock_thread):
    github_status = GithubStatus()
    github_status2 = GithubStatus()

    assert isinstance(github_status, _GithubStatus)
    assert github_status is github_status2


@pytest.mark.parametrize(
    "env,expected_sleep_time,expected_timeout",
    [
        ({}, 1, 10),
        ({"GITHUB_STATUS_SLEEP_TIME": "3"}, 3, 10),
        ({"GITHUB_STATUS_TIMEOUT": "2"}, 1, 2),
    ],
)
@mock.patch("ghmirror.data_structures.monostate.HTTPAdapter")
@mock.patch("ghmirror.data_structures.monostate.requests.Session")
@mock.patch("ghmirror.data_structures.monostate.threading.Thread")
def test_create_github_status_with_sleep_time(
    mock_thread,
    mock_session,
    mock_http_adapter,
    env,
    expected_sleep_time,
    expected_timeout,
):
    with mock.patch.dict("ghmirror.data_structures.monostate.os.environ", env):
        github_status = _GithubStatus.create()

    assert github_status.online is True
    assert github_status.sleep_time == expected_sleep_time
    assert github_status.timeout == expected_timeout
    assert github_status.session is mock_session.return_value
    mock_thread.assert_called_once_with(target=github_status.check, daemon=True)
    mock_thread.return_value.start.assert_called_once_with()
    mock_session.assert_called_once_with()
    mock_http_adapter.assert_called_once_with(max_retries=3)
    mock_session.return_value.mount.assert_called_once_with(
        "https://", mock_http_adapter.return_value
    )


def build_github_status_response_builder(status):
    return {
        "page": {
            "id": "kctbh9vrtdwd",
            "name": "GitHub",
            "url": "https://www.githubstatus.com",
            "updated_at": "2023-08-31T07:56:30Z",
        },
        "components": [
            {
                "created_at": "2014-05-03T01:22:07.274Z",
                "description": None,
                "group": False,
                "group_id": None,
                "id": "b13yz5g2cw10",
                "name": "API Requests",
                "only_show_if_degraded": False,
                "page_id": "kctbh9vrtdwd",
                "position": 1,
                "showcase": True,
                "start_date": None,
                "status": status,
                "updated_at": "2014-05-14T20:34:43.340Z",
            },
            {
                "created_at": "2014-05-03T01:22:07.286Z",
                "description": None,
                "group": False,
                "group_id": None,
                "id": "9397cnvk62zn",
                "name": "Management Portal",
                "only_show_if_degraded": False,
                "page_id": "kctbh9vrtdwd",
                "position": 2,
                "showcase": True,
                "start_date": None,
                "status": "major_outage",
                "updated_at": "2014-05-14T20:34:44.470Z",
            },
        ],
    }


@pytest.mark.parametrize(
    "status",
    [
        "operational",
        "degraded_performance",
        "partial_outage",
    ],
)
@mock.patch(
    "ghmirror.data_structures.monostate.time.sleep", side_effect=InterruptedError
)
@mock.patch("ghmirror.data_structures.monostate.threading.Thread")
def test_github_status_check_success(_mock_thread, mock_sleep, status):
    mocked_response = mock.create_autospec(requests.Response)
    mocked_response.json.return_value = build_github_status_response_builder(status)
    session = mock.create_autospec(requests.Session)
    session.get.return_value = mocked_response
    github_status = _GithubStatus(
        sleep_time=EXPECTED_SLEEP_TIME, timeout=EXPECTED_TIMEOUT, session=session
    )

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is True
    session.get.assert_called_once_with(
        "https://www.githubstatus.com/api/v2/components.json", timeout=EXPECTED_TIMEOUT
    )
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(EXPECTED_SLEEP_TIME)


@mock.patch("ghmirror.data_structures.monostate.LOG")
@mock.patch(
    "ghmirror.data_structures.monostate.time.sleep", side_effect=InterruptedError
)
@mock.patch("ghmirror.data_structures.monostate.threading.Thread")
def test_github_status_check_outage(_mock_thread, mock_sleep, mock_log):
    mocked_response = mock.create_autospec(requests.Response)
    mocked_response.json.return_value = build_github_status_response_builder(
        "major_outage"
    )
    session = mock.create_autospec(requests.Session)
    session.get.return_value = mocked_response
    github_status = _GithubStatus(
        sleep_time=EXPECTED_SLEEP_TIME, timeout=EXPECTED_TIMEOUT, session=session
    )

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is False
    mock_log.warning.assert_called_once_with(
        "Github API is offline, response: %s", mocked_response.text
    )
    session.get.assert_called_once_with(
        "https://www.githubstatus.com/api/v2/components.json", timeout=EXPECTED_TIMEOUT
    )
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(EXPECTED_SLEEP_TIME)


@pytest.mark.parametrize(
    "error",
    [
        (requests.exceptions.ConnectionError("Connection error")),
        (requests.exceptions.HTTPError("429 Client Error: too many requests")),
        (requests.exceptions.Timeout("Timeout")),
    ],
)
@mock.patch("ghmirror.data_structures.monostate.LOG")
@mock.patch(
    "ghmirror.data_structures.monostate.time.sleep", side_effect=InterruptedError
)
@mock.patch("ghmirror.data_structures.monostate.threading.Thread")
def test_github_status_check_fail(_mock_thread, mock_sleep, mock_log, error):
    mocked_response = mock.create_autospec(requests.Response)
    session = mock.create_autospec(requests.Session)
    session.get.return_value = mocked_response
    mocked_response.raise_for_status.side_effect = error
    github_status = _GithubStatus(
        sleep_time=EXPECTED_SLEEP_TIME, timeout=EXPECTED_TIMEOUT, session=session
    )

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is False
    mock_log.warning.assert_called_once_with("Github API is offline, reason: %s", error)
    session.get.assert_called_once_with(
        "https://www.githubstatus.com/api/v2/components.json", timeout=EXPECTED_TIMEOUT
    )
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(EXPECTED_SLEEP_TIME)
