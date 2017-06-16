from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.conf import settings


class TestIndex(TestCase):
    fixtures = ('test_auth.json', 'test_archive_api.json',)

    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_index(self):
        """ Test that the home page comes up with a login
        """
        # Issue a GET request.
        response = self.client.get('/', follow=True)

        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in with your FLUXNET credentials")
        self.assertNotContains(response, "key={}".format(settings.GOOGLE_MAPS_KEY))

        # Login
        user = User.objects.get(username="auser")
        self.client.force_login(user)

        # Check that the response is 200 OK.
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "key={}".format(settings.GOOGLE_MAPS_KEY))