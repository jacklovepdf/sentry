from __future__ import absolute_import

import responses

from sentry.coreapi import APIError
from sentry.mediators.external_requests import SelectRequester
from sentry.testutils import TestCase


class TestSelectRequester(TestCase):
    def setUp(self):
        super(TestSelectRequester, self).setUp()

        self.user = self.create_user(name='foo')
        self.org = self.create_organization(owner=self.user)
        self.project = self.create_project(slug='boop', organization=self.org)

        self.sentry_app = self.create_sentry_app(
            name='foo',
            organization=self.org,
            webhook_url='https://example.com',
            scopes=(),
        )

        self.install = self.create_sentry_app_installation(
            slug='foo',
            organization=self.org,
            user=self.user,
        )

    @responses.activate
    def test_makes_request(self):
        options = [
            {
                'label': 'An Issue',
                'value': '123',
                'default': True,
            },
            {
                'label': 'Another Issue',
                'value': '456',
            },

        ]
        responses.add(
            method=responses.GET,
            url='https://example.com/get-issues?projectSlug=boop&installationId=f3d37e3a-9a87-4651-8463-d375118f4996',
            json=options,
            status=200,
            content_type='application/json',
        )

        result = SelectRequester.run(
            install=self.install,
            project=self.project,
            uri='/get-issues',
        )
        assert result == {
            'choices': [
                ['An Issue', '123'],
                ['Another Issue', '456']
            ],
            'default': ['An Issue', '123'],
        }

        request = responses.calls[0].request
        assert request.headers['Sentry-App-Signature']

    @responses.activate
    def test_invalid_response_format(self):
        # missing 'label'
        invalid_format = {
            'value': '12345',
        }
        responses.add(
            method=responses.GET,
            url='https://example.com/get-issues?projectSlug=boop&installationId=f3d37e3a-9a87-4651-8463-d375118f4996',
            json=invalid_format,
            status=200,
            content_type='application/json',
        )

        with self.assertRaises(APIError):
            SelectRequester.run(
                install=self.install,
                project=self.project,
                group=self.group,
                uri='/get-issues',
                fields={},
            )

    @responses.activate
    def test_500_response(self):
        responses.add(
            method=responses.GET,
            url='https://example.com/get-issues?projectSlug=boop&installationId=f3d37e3a-9a87-4651-8463-d375118f4996',
            body='Something failed',
            status=500,
        )

        with self.assertRaises(APIError):
            SelectRequester.run(
                install=self.install,
                project=self.project,
                group=self.group,
                uri='/get-issues',
                fields={},
            )
