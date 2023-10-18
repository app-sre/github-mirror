from unittest import TestCase

from ghmirror.core.mirror_response import MirrorResponse


class MockResponse:
    def __init__(self, content, headers, status_code):
        if content is None:
            self.content = content
        else:
            self.content = content.encode()
        self.headers = headers
        self.status_code = status_code


class TestResponse(TestCase):
    def test_no_headers(self):
        headers = {"Some-Other-Header": "foo"}
        mock_response = MockResponse(content="", headers=headers, status_code=200)
        response = MirrorResponse(
            original_response=mock_response, gh_api_url="foo", gh_mirror_url="bar"
        )

        # That item should not be part of the response.headers
        self.assertFalse(response.headers)

    def test_headers(self):
        headers = {
            "Link": "foobar",
            "Content-Type": "foo",
            "Last-Modified": "foo",
            "ETag": "foo",
            "Some-Other-Header": "foo",
        }
        mock_response = MockResponse(content="", headers=headers, status_code=200)

        response = MirrorResponse(
            original_response=mock_response, gh_api_url="foo", gh_mirror_url="bar"
        )

        response_headers = response.headers

        link = response_headers.pop("Link")
        # Link should have been modified, replacing the gh_api_url string
        # by the gh_mirror_url string.
        self.assertEqual(link, "barbar")

        # Those headers should be there
        for item in ["Content-Type", "Last-Modified", "ETag"]:
            header = response_headers.pop(item)
            self.assertEqual(header, "foo")

        # No other headers should be there
        self.assertFalse(response_headers)

    def test_content(self):
        mock_response = MockResponse(content=None, headers={}, status_code=200)

        response = MirrorResponse(
            original_response=mock_response, gh_api_url="foo", gh_mirror_url="bar"
        )
        # No content from the upstream response should stay the
        # same in the mirror response
        self.assertIsNone(response.content)

        mock_response = MockResponse(content="foobar", headers={}, status_code=200)
        response = MirrorResponse(
            original_response=mock_response, gh_api_url="foo", gh_mirror_url="bar"
        )
        # content should have been modified, replacing the
        # gh_api_url string by the gh_mirror_url string.
        self.assertEqual(response.content, "barbar".encode())

    def test_status_code(self):
        mock_response = MockResponse(content="foobar", headers={}, status_code=200)

        response = MirrorResponse(
            original_response=mock_response, gh_api_url="foo", gh_mirror_url="bar"
        )

        # No status code change
        self.assertEqual(response.status_code, 200)
