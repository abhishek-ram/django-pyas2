from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from pyas2.models import PublicCertificate


class TestDownloadFileView(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="dummy")
        with open("pyas2/tests/fixtures/client_public.pem", "rb") as fp:
            self.cert = PublicCertificate.objects.create(
                name="test-cert", certificate=fp.read()
            )

    def test_view_is_protected(self):
        client = Client()
        response = client.get(
            reverse("download-file", kwargs={"obj_type": "public_cert", "obj_id": "1"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_download_public_certificate(self):
        client = Client()
        client.force_login(self.user)

        response = client.get(
            reverse(
                "download-file",
                kwargs={"obj_type": "public_cert", "obj_id": self.cert.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bytes(self.cert.certificate), response.content)
