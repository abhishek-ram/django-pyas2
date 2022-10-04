import importlib
import os
from unittest import mock

from django.test import Client, override_settings
from django.test import TestCase
from pyas2lib import Message as As2Message
from pyas2lib import Mdn as As2Mdn

from pyas2 import settings
from pyas2.models import Message
from pyas2.models import Mdn
from pyas2.models import Organization
from pyas2.models import Partner
from pyas2.models import PrivateKey
from pyas2.models import PublicCertificate
from pyas2.tests.test_basic import SendMessageMock
from pyas2.tests import TEST_DIR


class AdvancedTestCases(TestCase):
    """Test cases dealing with handling of failures and other features"""

    @classmethod
    def setUpTestData(cls):
        # Every test needs a client.
        cls.client = Client()

        # Load the client and server certificates
        with open(os.path.join(TEST_DIR, "server_private.pem"), "rb") as fp:
            cls.server_key = PrivateKey.objects.create(key=fp.read(), key_pass="test")

        with open(os.path.join(TEST_DIR, "server_public.pem"), "rb") as fp:
            cls.server_crt = PublicCertificate.objects.create(certificate=fp.read())

        with open(os.path.join(TEST_DIR, "client_private.pem"), "rb") as fp:
            cls.client_key = PrivateKey.objects.create(key=fp.read(), key_pass="test")

        with open(os.path.join(TEST_DIR, "client_public.pem"), "rb") as fp:
            cls.client_crt = PublicCertificate.objects.create(certificate=fp.read())

    def setUp(self):

        # Setup the server organization and partner
        Organization.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            encryption_key=self.server_key,
            signature_key=self.server_key,
        )
        self.partner = Partner.objects.create(
            name="AS2 Client",
            as2_name="as2client",
            target_url="http://localhost:8080/pyas2/as2receive",
            compress=False,
            mdn=False,
            signature_cert=self.client_crt,
            encryption_cert=self.client_crt,
        )

        # Setup the client organization and partner
        self.organization = Organization.objects.create(
            name="AS2 Client",
            as2_name="as2client",
            encryption_key=self.client_key,
            signature_key=self.client_key,
        )

        # Initialise the payload i.e. the file to be transmitted
        with open(os.path.join(TEST_DIR, "testmessage.edi"), "rb") as fp:
            self.payload = fp.read()

    @classmethod
    def tearDownClass(cls):
        # remove all files in the inbox folders
        inbox = os.path.join("messages", "as2server", "inbox", "as2client")
        try:
            files = os.listdir(inbox)
        except OSError:
            files = []
        for the_file in files:
            file_path = os.path.join(inbox, the_file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        for message in Message.objects.all():
            message.headers.delete()
            message.payload.delete()
        for mdn in Mdn.objects.all():
            mdn.headers.delete()
            mdn.payload.delete()

    def test_post_send_command(self):
        """Test that the command after successful send gets executed."""

        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            http_auth=True,
            http_auth_user="admin",
            http_auth_pass="password",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
            cmd_send="touch %s/$messageid.sent" % TEST_DIR,
        )
        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "S")

        # Check that the command got executed
        touch_file = os.path.join(TEST_DIR, "%s.sent" % in_message.message_id)
        self.assertTrue(os.path.exists(touch_file))
        os.remove(touch_file)

    @mock.patch("requests.post")
    def test_post_send_command_async(self, mock_request):
        """Test that the command after successful send gets executed with
        asynchronous MDN."""

        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="ASYNC",
            mdn_sign="sha1",
            cmd_send="touch %s/$messageid.sent" % TEST_DIR,
        )
        in_message = self.build_and_send(partner)

        # Send the async mdn to the sender
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        mock_request.side_effect = SendMessageMock(self.client)
        out_message.mdn.send_async_mdn()

        # Check that the command got executed
        in_message.refresh_from_db()
        self.assertEqual(in_message.status, "S")

        # Check that the command got executed
        touch_file = os.path.join(TEST_DIR, "%s.sent" % in_message.message_id)
        self.assertTrue(os.path.exists(touch_file))
        os.remove(touch_file)

    def test_post_receive_command(self):
        """Test that the command after successful receive gets executed."""
        # settings.DATA_DIR = TEST_DIR
        # add the post receive command and save it
        self.partner.cmd_receive = "touch %s/$filename.received" % TEST_DIR
        self.partner.save()

        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "S")

        # Check that the command got executed
        touch_file = os.path.join(
            TEST_DIR, "%s.msg.received" % in_message.message_id.replace("@", "")
        )
        self.assertTrue(os.path.exists(touch_file))
        os.remove(touch_file)
        # shutil.rmtree(os.path.join(TEST_DIR, "messages"))
        # settings.DATA_DIR = None

    def test_use_received_filename(self):
        """Test using the filename of the payload received while saving the file."""

        # add the post receive command and save it
        self.partner.cmd_receive = "touch %s/$filename.received" % TEST_DIR
        self.partner.keep_filename = True
        self.partner.save()

        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "S")

        # Check that the command got executed
        touch_file = os.path.join(TEST_DIR, "testmessage.edi.received")
        self.assertTrue(os.path.exists(touch_file))
        os.remove(touch_file)

    def test_use_received_sender_and_receiver(self):
        """Test using the sender and receiver as2 name while the payload received."""

        # add the post receive command and save it
        self.partner.cmd_receive = "touch %s/$sender.to.$receiver" % TEST_DIR
        self.partner.keep_filename = True
        self.partner.save()

        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "S")

        # Check that the command got executed
        touch_file = os.path.join(
            TEST_DIR, "%s.to.%s" % (self.organization.as2_name, partner.as2_name)
        )
        self.assertTrue(os.path.exists(touch_file))
        os.remove(touch_file)

    @mock.patch("requests.post")
    def test_duplicate_error(self, mock_request):
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )

        # Send the message once
        as2message = As2Message(
            sender=self.organization.as2org, receiver=partner.as2partner
        )
        as2message.build(
            self.payload,
            filename="testmessage.edi",
            subject=partner.subject,
            content_type=partner.content_type,
        )
        in_message, _ = Message.objects.create_from_as2message(
            as2message=as2message, payload=self.payload, direction="OUT", status="P"
        )

        mock_request.side_effect = SendMessageMock(self.client)
        in_message.send_message(as2message.headers, as2message.content)

        # Check the status of the message
        self.assertEqual(in_message.status, "S")
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "S")

        # send it again to cause duplicate error
        in_message.send_message(as2message.headers, as2message.content)

        # Make sure out message was created
        self.assertEqual(in_message.status, "E")
        out_message = Message.objects.get(
            message_id=in_message.message_id + "_duplicate", direction="IN"
        )
        self.assertEqual(out_message.status, "E")

    def test_org_missing_error(self):
        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server2",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "E")

        # Check the status of the received message
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertTrue("Unknown AS2 organization" in out_message.detailed_status)

    def test_partner_missing_error(self):
        self.organization.as2_name = "as2partner2"
        self.organization.save()

        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "E")

        # Check the status of the received message
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertTrue("Unknown AS2 partner" in out_message.detailed_status)

    def test_insufficient_security_error(self):
        self.partner.encryption = "tripledes_192_cbc"
        self.partner.signature = "sha1"
        self.partner.save()

        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "E")

        # Check the status of the received message
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertTrue("signed message not found" in out_message.detailed_status)

        # Create the client partner and send the command
        partner.encryption = ""
        partner.save()

        in_message = self.build_and_send(partner)
        self.assertEqual(in_message.status, "E")

        # Check the status of the received message
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertTrue("encrypted message not found" in out_message.detailed_status)

    def test_decompression_error(self):
        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            compress=True,
            signature_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner, smudge=True)
        self.assertEqual(in_message.status, "E")

        # Check the status of the received message
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertTrue("Decompression failed" in out_message.detailed_status)

    def test_encryption_error(self):
        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            encryption="tripledes_192_cbc",
            encryption_cert=self.client_crt,
            signature_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner, smudge=False)
        self.assertEqual(in_message.status, "E")

        # Check the status of the received message
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertTrue("Failed to decrypt" in out_message.detailed_status)

    def test_signature_error(self):
        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        in_message = self.build_and_send(partner, smudge=True)
        self.assertEqual(in_message.status, "E")

        # Check the status of the received message
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertTrue(
            "Failed to verify message signature" in out_message.detailed_status
        )

    def test_missing_message_id(self):
        # Create the client partner and send the command
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode="ASYNC",
            mdn_sign="sha1",
        )
        out_message = self.build_and_send(partner)

        # Create MDN object without message_id
        in_message = As2Mdn()
        in_message.orig_message_id = out_message.message_id
        in_message.message_id = None
        mdn_message = Mdn.objects.create_from_as2mdn(in_message, out_message, "R")

        # Check that original message id was used to store mdn_id
        self.assertEqual(mdn_message.mdn_id, out_message.message_id)

    @mock.patch("requests.post")
    def build_and_send(self, partner, mock_request, smudge=False):
        # Build and send the message to server
        as2message = As2Message(
            sender=self.organization.as2org, receiver=partner.as2partner
        )
        as2message.build(
            self.payload,
            filename="testmessage.edi",
            subject=partner.subject,
            content_type=partner.content_type,
        )
        out_message, _ = Message.objects.create_from_as2message(
            as2message=as2message, payload=self.payload, direction="OUT", status="P"
        )
        mock_request.side_effect = SendMessageMock(self.client)
        out_message.send_message(
            as2message.headers,
            b"xxxx" + as2message.content if smudge else as2message.content,
        )

        return out_message


@override_settings(PYAS2={"DATA_DIR": TEST_DIR})
def test_setting_data_directory():
    """Test that the data directory gets set correctly."""
    assert settings.DATA_DIR is None
    importlib.reload(settings)
    assert settings.DATA_DIR is TEST_DIR
