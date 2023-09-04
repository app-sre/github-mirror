from unittest import mock

import pytest
import requests

from ghmirror.data_structures.monostate import GithubStatus, _GithubStatus


@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_create_github_status_singleton(_mock_thread):
    github_status = GithubStatus()
    github_status2 = GithubStatus()

    assert isinstance(github_status, _GithubStatus)
    assert github_status is github_status2


@pytest.mark.parametrize('env_sleep_time,expected_sleep_time',
                         [
                             ('3', 3),
                             (1, 1),
                         ])
@mock.patch('ghmirror.data_structures.monostate.requests.Session')
@mock.patch('ghmirror.data_structures.monostate.os.environ')
@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_create_github_status(mock_thread, mock_environ, mock_session, env_sleep_time, expected_sleep_time):
    mock_environ.get.return_value = env_sleep_time

    github_status = _GithubStatus.create()

    assert github_status.online is True
    assert github_status.sleep_time == expected_sleep_time
    assert github_status.session is mock_session.return_value
    mock_thread.assert_called_once_with(target=github_status.check, daemon=True)
    mock_thread.return_value.start.assert_called_once_with()
    mock_environ.get.assert_called_once_with('GITHUB_STATUS_SLEEP_TIME', 1)
    mock_session.assert_called_once_with()


def build_github_status_response_builder(status):
    return {
        "page": {
            "id": "kctbh9vrtdwd",
            "name": "GitHub",
            "url": "https://www.githubstatus.com",
            "updated_at": "2023-08-31T07:56:30Z"
        },
        "components": [
            {
                "created_at": "2014-05-03T01:22:07.274Z",
                "description": None,
                "group": False,
                "group_id": None,
                "id": "b13yz5g2cw10",
                "name": "API",
                "only_show_if_degraded": False,
                "page_id": "kctbh9vrtdwd",
                "position": 1,
                "showcase": True,
                "start_date": None,
                "status": status,
                "updated_at": "2014-05-14T20:34:43.340Z"
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
                "updated_at": "2014-05-14T20:34:44.470Z"
            }
        ]
    }


@pytest.mark.parametrize('status',
                         [
                             'operational',
                             'degraded_performance',
                             'partial_outage',
                         ])
@mock.patch('ghmirror.data_structures.monostate.time.sleep', side_effect=InterruptedError)
@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_github_status_check_success(_mock_thread, mock_sleep, status):
    mocked_response = mock.create_autospec(requests.Response)
    mocked_response.json.return_value = build_github_status_response_builder(status)
    session = mock.create_autospec(requests.Session)
    session.get.return_value = mocked_response
    sleep_time = 1
    github_status = _GithubStatus(sleep_time=sleep_time, session=session)

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is True
    session.get.assert_called_once_with('https://www.githubstatus.com/api/v2/components.json', timeout=2)
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(sleep_time)


@mock.patch('ghmirror.data_structures.monostate.LOG')
@mock.patch('ghmirror.data_structures.monostate.time.sleep', side_effect=InterruptedError)
@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_github_status_check_outage(_mock_thread, mock_sleep, mock_log):
    mocked_response = mock.create_autospec(requests.Response)
    mocked_response.json.return_value = build_github_status_response_builder('major_outage')
    session = mock.create_autospec(requests.Session)
    session.get.return_value = mocked_response
    sleep_time = 1
    github_status = _GithubStatus(sleep_time=sleep_time, session=session)

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is False
    mock_log.warning.assert_called_once_with('Github API is offline, response: %s', mocked_response.text)
    session.get.assert_called_once_with('https://www.githubstatus.com/api/v2/components.json', timeout=2)
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(sleep_time)


@pytest.mark.parametrize('error',
                         [
                             (requests.exceptions.ConnectionError('Connection error')),
                             (requests.exceptions.HTTPError('429 Client Error: too many requests')),
                             (requests.exceptions.Timeout('Timeout')),
                         ])
@mock.patch('ghmirror.data_structures.monostate.LOG')
@mock.patch('ghmirror.data_structures.monostate.time.sleep', side_effect=InterruptedError)
@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_github_status_check_fail(_mock_thread, mock_sleep, mock_log, error):
    mocked_response = mock.create_autospec(requests.Response)
    session = mock.create_autospec(requests.Session)
    session.get.return_value = mocked_response
    mocked_response.raise_for_status.side_effect = error
    sleep_time = 1
    github_status = _GithubStatus(sleep_time=sleep_time, session=session)

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is False
    mock_log.warning.assert_called_once_with('Github API is offline, reason: %s', error)
    session.get.assert_called_once_with('https://www.githubstatus.com/api/v2/components.json', timeout=2)
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(sleep_time)
