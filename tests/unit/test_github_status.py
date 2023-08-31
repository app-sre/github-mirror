from unittest import mock

from ghmirror.data_structures.monostate import GithubStatus, _GithubStatus


@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
def test_create_github_status_singleton(mock_thread):
    github_status = GithubStatus()
    github_status2 = GithubStatus()

    assert github_status.online is True
    assert github_status is github_status2
    mock_thread.assert_called_once_with(target=github_status.check, daemon=True)
    mock_thread.return_value.start.assert_called_once()

@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
@mock.patch('ghmirror.data_structures.monostate.os.environ')
def test_create__github_status_with_sleep_time(mock_environ, _mock_thread):
    mock_environ.get.return_value = '3'

    github_status = _GithubStatus.create()

    github_status.sleep_time = 3
    mock_environ.get.assert_called_once_with('GITHUB_STATUS_SLEEP_TIME', 1)

@mock.patch('ghmirror.data_structures.monostate.threading.Thread')
@mock.patch('ghmirror.data_structures.monostate.os.environ')
def test_create__github_status_with_default_sleep_time(mock_environ, _mock_thread):
    mock_environ.get.return_value = 1

    github_status = _GithubStatus.create()

    github_status.sleep_time = 1
    mock_environ.get.assert_called_once_with('GITHUB_STATUS_SLEEP_TIME', 1)
