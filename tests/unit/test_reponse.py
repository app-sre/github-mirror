from ghmirror.app.response import MirrorResponse


class MockResponse:
    def __init__(self, content, headers, status_code):
        self.content = content.encode()
        self.headers = headers
        self.status_code = status_code

    def content(self):
        return self.content

    def headers(self):
        return self.headers

    def status_code(self):
        return self.status_code


class TestResponse:

    def test_no_headers(self):
        headers = {'Some-Other-Header': 'foo'}
        mock_response = MockResponse(content='',
                                     headers=headers,
                                     status_code=200)
        response = MirrorResponse(original_response=mock_response,
                                  headers={},
                                  gh_api_url='foo',
                                  gh_mirror_url='bar')

        # That item should not be part of the response.headers
        assert not response.headers

    def test_headers(self):
        headers = {'Link': 'foobar',
                   'Content-Type': 'foo',
                   'Last-Modified': 'foo',
                   'ETag': 'foo',
                   'Some-Other-Header': 'foo'}
        mock_response = MockResponse(content='',
                                     headers=headers,
                                     status_code=200)

        response = MirrorResponse(original_response=mock_response,
                                  headers={},
                                  gh_api_url='foo',
                                  gh_mirror_url='bar')

        response_headers = response.headers

        link = response_headers.pop('Link')
        # Link should have been modified, replacing the gh_api_url string
        # by the gh_mirror_url string.
        assert link == 'barbar'

        # Those headers should be there
        for item in ['Content-Type', 'Last-Modified', 'ETag']:
            header = response_headers.pop(item)
            assert header == 'foo'

        # No other headers should be there
        assert not response_headers

    def test_content(self):
        mock_response = MockResponse(content='foobar',
                                     headers={},
                                     status_code=200)

        response = MirrorResponse(original_response=mock_response,
                                  headers={},

                                  gh_api_url='foo',
                                  gh_mirror_url='bar')

        # content should have been modified, replacing the
        # gh_api_url string by the gh_mirror_url string.
        assert response.content == 'barbar'.encode()

    def test_status_code(self):
        mock_response = MockResponse(content='foobar',
                                     headers={},
                                     status_code=200)

        response = MirrorResponse(original_response=mock_response,
                                  headers={},
                                  gh_api_url='foo',
                                  gh_mirror_url='bar')

        # No status code change
        assert response.status_code == 200
