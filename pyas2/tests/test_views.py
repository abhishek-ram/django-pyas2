import os

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, Client
from django.urls import reverse

from pyas2.models import PublicCertificate, PrivateKey, Message, Mdn
from pyas2.tests import TEST_DIR


class TestDownloadFileView(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="dummy")
        with open(os.path.join(TEST_DIR, "client_public.pem"), "rb") as fp:
            self.cert = PublicCertificate.objects.create(
                name="test-cert", certificate=fp.read()
            )

        with open(os.path.join(TEST_DIR, "client_private.pem"), "rb") as fp:
            self.private_key = PrivateKey.objects.create(
                name="test-key", key=fp.read(), key_pass="test"
            )

        with open(os.path.join(TEST_DIR, "testmessage.edi"), "rb") as fp:
            self.message = Message.objects.create(
                message_id="some-message-id",
                direction="IN",
                status="S",
            )
            self.message.payload.save("testmessage.edi", fp)
            self.mdn = Mdn.objects.create(
                mdn_id="some-mdn-id", message=self.message, status="S"
            )
            self.mdn.payload.save("some-mdn-id.mdn", ContentFile("MDN Content"))

    def test_view_is_protected(self):
        client = Client()
        response = client.get(
            reverse("download-file", kwargs={"obj_type": "public_cert", "obj_id": "1"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_unknown_object_type(self):
        """Test that we get 404 when an uknown object type is sent."""
        client = Client()
        client.force_login(self.user)

        response = client.get(
            reverse("download-file", kwargs={"obj_type": "some_type", "obj_id": "1"})
        )
        self.assertEqual(response.status_code, 404)

    def test_download_public_certificate(self):
        client = Client()
        client.force_login(self.user)

        response = client.get(
            reverse(
                "download-file",
                kwargs={"obj_type": "public_cert", "obj_id": self.cert.id},
            )
        )
        self.assertEqual(str(self.cert), "test-cert")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bytes(self.cert.certificate), response.content)

    def test_download_private_key(self):
        client = Client()
        client.force_login(self.user)

        response = client.get(
            reverse(
                "download-file",
                kwargs={"obj_type": "private_key", "obj_id": self.private_key.id},
            )
        )
        self.assertEqual(str(self.private_key), "test-key")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bytes(self.private_key.key), response.content)

    def test_download_message_payload(self):
        client = Client()
        client.force_login(self.user)

        response = client.get(
            reverse(
                "download-file",
                kwargs={"obj_type": "message_payload", "obj_id": self.message.id},
            )
        )
        self.assertEqual(str(self.message), self.message.message_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bytes(self.message.payload.read()), response.content)

    def test_download_mdn_payload(self):
        client = Client()
        client.force_login(self.user)

        response = client.get(
            reverse(
                "download-file",
                kwargs={"obj_type": "mdn_payload", "obj_id": self.mdn.id},
            )
        )
        self.assertEqual(str(self.mdn), self.mdn.mdn_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bytes(self.mdn.payload.read()), response.content)


def test_as2_receive_view_options(client):
    """Test the options method of the AS2 Receive endpoint."""
    response = client.options("/pyas2/as2receive")
    assert response.status_code == 200
    assert response.content == b""


def test_send_as2_message_view(mocker, client, admin_client, organization, partner):
    """Test the view for sending the AS2 message from the admin."""
    mocked_send_message = mocker.patch("pyas2.models.Message.send_message")
    response = client.get(reverse("as2-send"))
    assert response.status_code == 302

    # Try with the admin client
    response = admin_client.get(reverse("as2-send"))
    assert response.status_code == 200

    # Try posting to the form
    with open(os.path.join(TEST_DIR, "testmessage.edi"), "rb") as fp:
        post_data = {
            "organization": organization.as2_name,
            "partner": partner.as2_name,
            "file": fp,
        }
        response = admin_client.post(reverse("as2-send"), data=post_data)
    assert response.status_code == 302
    assert mocked_send_message.call_count == 1
