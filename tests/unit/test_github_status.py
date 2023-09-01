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
@mock.patch('ghmirror.data_structures.monostate.os.environ')
@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_create_github_status(mock_thread, mock_environ, env_sleep_time, expected_sleep_time):
    mock_environ.get.return_value = env_sleep_time

    github_status = _GithubStatus.create()

    assert github_status.online is True
    assert github_status.sleep_time == expected_sleep_time
    mock_thread.assert_called_once_with(target=github_status.check, daemon=True)
    mock_thread.return_value.start.assert_called_once()
    mock_environ.get.assert_called_once_with('GITHUB_STATUS_SLEEP_TIME', 1)



@mock.patch('ghmirror.data_structures.monostate.requests.get')
@mock.patch('ghmirror.data_structures.monostate.time.sleep', side_effect=InterruptedError)
@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_github_status_check_success(_mock_thread, mock_sleep, mock_requests_get):
    mocked_response = mock.create_autospec(requests.Response)
    mock_requests_get.return_value = mocked_response
    sleep_time = 1
    github_status = _GithubStatus(sleep_time=sleep_time)

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is True
    mock_requests_get.assert_called_once_with('https://api.github.com/status', timeout=2)
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(sleep_time)


@pytest.mark.parametrize('error',
                         [
                             (requests.exceptions.ConnectionError('Connection error')),
                             (requests.exceptions.HTTPError('429 Client Error: too many requests')),
                             (requests.exceptions.Timeout('Timeout')),
                         ])
@mock.patch('ghmirror.data_structures.monostate.LOG')
@mock.patch('ghmirror.data_structures.monostate.requests.get')
@mock.patch('ghmirror.data_structures.monostate.time.sleep', side_effect=InterruptedError)
@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_github_status_check_fail(_mock_thread, mock_sleep, mock_requests_get, mock_log, error):
    mocked_response = mock.create_autospec(requests.Response)
    mock_requests_get.return_value = mocked_response
    mocked_response.raise_for_status.side_effect = error
    sleep_time = 1
    github_status = _GithubStatus(sleep_time=sleep_time)

    with pytest.raises(InterruptedError):
        github_status.check()

    assert github_status.online is False
    mock_log.warning.assert_called_once_with('Github API is offline, reason: %s', error)
    mock_requests_get.assert_called_once_with('https://api.github.com/status', timeout=2)
    mocked_response.raise_for_status.assert_called_once_with()
    mock_sleep.assert_called_once_with(sleep_time)
