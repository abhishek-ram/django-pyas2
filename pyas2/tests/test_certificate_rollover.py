"""Test cases for the certificate rollover lists of a Partner."""
import os
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from pyas2lib import Message as As2Message

from pyas2.forms import PartnerForm
from pyas2.models import Mdn
from pyas2.models import Message
from pyas2.models import Organization
from pyas2.models import Partner
from pyas2.models import PrivateKey
from pyas2.models import PublicCertificate
from pyas2.models import order_certificates
from pyas2.models import select_certificate
from pyas2.tests import TEST_DIR
from pyas2.tests.test_basic import SendMessageMock


def build_certificate(name, valid_from, valid_to):
    """Return an unsaved certificate with the given validity period."""
    return PublicCertificate(name=name, valid_from=valid_from, valid_to=valid_to)


class CertificateSelectionTestCase(TestCase):
    """Test cases for choosing the certificate to be used from a rollover list."""

    def setUp(self):
        now = timezone.now()
        self.expired = build_certificate(
            "expired.pem", now - timedelta(days=800), now - timedelta(days=1)
        )
        self.current = build_certificate(
            "current.pem", now - timedelta(days=2), now + timedelta(days=400)
        )
        self.renewed = build_certificate(
            "renewed.pem", now - timedelta(days=1), now + timedelta(days=800)
        )
        self.future = build_certificate(
            "future.pem", now + timedelta(days=1), now + timedelta(days=1000)
        )

    def testValidCertificateIsSelected(self):
        """Only a certificate within its validity period is assigned."""
        certificates = [self.expired, self.future, self.current]
        self.assertEqual(select_certificate(certificates), self.current)
        self.assertEqual(
            order_certificates(certificates), [self.current, self.future, self.expired]
        )

    def testMostRecentlyIssuedCertificateIsSelected(self):
        """The newest of the valid certificates is assigned."""
        certificates = [self.current, self.renewed]
        self.assertEqual(select_certificate(certificates), self.renewed)
        self.assertEqual(order_certificates(certificates), [self.renewed, self.current])

    def testCertificateSelectedAtGivenTime(self):
        """The certificate is assigned based on the validity at the given time."""
        certificates = [self.current, self.future]
        self.assertEqual(
            select_certificate(certificates, at_time=timezone.now()), self.current
        )
        self.assertEqual(
            select_certificate(
                certificates, at_time=timezone.now() + timedelta(days=500)
            ),
            self.future,
        )

    def testLastToExpireSelectedWhenNoneAreValid(self):
        """When no certificate is valid the one expiring last is assigned."""
        certificates = [self.expired, self.future]
        self.assertEqual(select_certificate(certificates), self.future)

    def testCertificateWithoutValidityIsValid(self):
        """A certificate with an unknown validity period is considered valid."""
        certificate = build_certificate("unknown.pem", None, None)
        self.assertTrue(certificate.is_valid())
        self.assertEqual(select_certificate([self.expired, certificate]), certificate)

    def testDuplicateAndEmptyCertificates(self):
        """Duplicates are removed and certificates that are not set are ignored."""
        self.assertIsNone(select_certificate([]))
        self.assertIsNone(select_certificate([None]))
        self.assertEqual(
            order_certificates([None, self.current, self.current]), [self.current]
        )


class PartnerCertificateTestCase(TestCase):
    """Test cases for the certificates assigned to a partner."""

    @classmethod
    def setUpTestData(cls):
        with open(os.path.join(TEST_DIR, "server_public.pem"), "rb") as fp:
            cls.server_crt = PublicCertificate.objects.create(certificate=fp.read())

        with open(os.path.join(TEST_DIR, "client_public.pem"), "rb") as fp:
            cls.client_crt = PublicCertificate.objects.create(certificate=fp.read())

    @staticmethod
    def expire_certificate(certificate):
        """Move the validity period of the certificate into the past."""
        PublicCertificate.objects.filter(pk=certificate.pk).update(
            valid_from=timezone.now() - timedelta(days=800),
            valid_to=timezone.now() - timedelta(days=1),
        )

    def build_partner(self, as2_name="as2client", rollover=True):
        """Create a partner with the client certificate in its rollover lists."""
        partner = Partner.objects.create(
            name="AS2 Client",
            as2_name=as2_name,
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
            encryption="tripledes_192_cbc",
            encryption_cert=self.server_crt,
        )
        if rollover:
            partner.signature_cert_rollover.add(self.client_crt)
            partner.encryption_cert_rollover.add(self.client_crt)

        # Return a fresh copy so that the certificate validity is not cached
        return Partner.objects.get(as2_name=as2_name)

    def testAssignedCertificatesUsedWithoutRollover(self):
        """The certificates of a partner are used when no rollover list is set."""
        partner = self.build_partner(rollover=False)
        self.assertEqual(partner.active_signature_cert, self.server_crt)
        self.assertEqual(partner.active_encryption_cert, self.server_crt)
        self.assertEqual(partner.signature_cert_candidates, [self.server_crt])

    def testRolloverCertificateUsedWhenAssignedOneExpired(self):
        """The valid certificate from the rollover list is used."""
        self.expire_certificate(self.server_crt)
        partner = self.build_partner()

        self.assertEqual(partner.active_signature_cert, self.client_crt)
        self.assertEqual(partner.active_encryption_cert, self.client_crt)
        self.assertEqual(
            partner.signature_cert_candidates, [self.client_crt, self.server_crt]
        )

        as2partner = partner.as2partner
        self.assertEqual(as2partner.verify_cert, bytes(self.client_crt.certificate))
        self.assertEqual(as2partner.encrypt_cert, bytes(self.client_crt.certificate))

    def testCertificatesCanBeGivenExplicitly(self):
        """The certificates to be used can be passed in when building the partner."""
        self.expire_certificate(self.server_crt)
        partner = self.build_partner()

        as2partner = partner.build_as2partner(signature_cert=self.server_crt)
        self.assertEqual(as2partner.verify_cert, bytes(self.server_crt.certificate))
        self.assertEqual(as2partner.encrypt_cert, bytes(self.client_crt.certificate))

    def testRolloverCertificateSatisfiesValidation(self):
        """A certificate in the rollover list is enough to sign and encrypt."""
        partner_data = {
            "name": "AS2 Client",
            "as2_name": "as2client",
            "target_url": "http://localhost:8080/pyas2/as2receive",
            "subject": "EDI Message sent using pyas2",
            "content_type": "application/edi-consent",
            "signature": "sha1",
            "encryption": "tripledes_192_cbc",
        }
        form = PartnerForm(data=partner_data)
        self.assertFalse(form.is_valid())

        form = PartnerForm(
            data=dict(
                partner_data,
                signature_cert_rollover=[self.client_crt.pk],
                encryption_cert_rollover=[self.client_crt.pk],
            )
        )
        self.assertTrue(form.is_valid(), form.errors)


class RolloverServerClientTestCase(TestCase):
    """Test cases for exchanging messages while a partner rolls over its certificate."""

    @classmethod
    def setUpTestData(cls):
        # Load the client and server keys and certificates
        with open(os.path.join(TEST_DIR, "server_private.pem"), "rb") as fp:
            cls.server_key = PrivateKey.objects.create(key=fp.read(), key_pass="test")

        with open(os.path.join(TEST_DIR, "server_public.pem"), "rb") as fp:
            cls.server_crt = PublicCertificate.objects.create(certificate=fp.read())

        with open(os.path.join(TEST_DIR, "client_private.pem"), "rb") as fp:
            cls.client_key = PrivateKey.objects.create(key=fp.read(), key_pass="test")

        with open(os.path.join(TEST_DIR, "client_public.pem"), "rb") as fp:
            cls.client_crt = PublicCertificate.objects.create(certificate=fp.read())

        # Initialise the payload i.e. the file to be transmitted
        with open(os.path.join(TEST_DIR, "testmessage.edi"), "rb") as fp:
            cls.payload = fp.read()

    def setUp(self):
        # Setup the server organization and the partner sending to it. The partner
        # has announced a new certificate but is still signing with the old one.
        Organization.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            encryption_key=self.server_key,
            signature_key=self.server_key,
        )
        self.server_partner = Partner.objects.create(
            name="AS2 Client",
            as2_name="as2client",
            target_url="http://localhost:8080/pyas2/as2receive",
            compress=False,
            mdn=False,
            signature_cert=self.server_crt,
        )
        self.server_partner.signature_cert_rollover.add(self.client_crt)

        # Setup the client organization
        self.organization = Organization.objects.create(
            name="AS2 Client",
            as2_name="as2client",
            encryption_key=self.client_key,
            signature_key=self.client_key,
        )

    def tearDown(self):
        # remove all files in the inbox folders
        inbox = os.path.join("messages", "as2server", "inbox", "as2client")
        for the_file in os.listdir(inbox):
            file_path = os.path.join(inbox, the_file)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        for message in Message.objects.all():
            message.headers.delete()
            message.payload.delete()
        for mdn in Mdn.objects.all():
            mdn.headers.delete()
            mdn.payload.delete()

    @staticmethod
    def expire_certificate(certificate):
        """Move the validity period of the certificate into the past."""
        PublicCertificate.objects.filter(pk=certificate.pk).update(
            valid_from=timezone.now() - timedelta(days=800),
            valid_to=timezone.now() - timedelta(days=1),
        )

    def testSignedMessageVerifiedWithRolloverCertificate(self):
        """A message signed with any certificate of the rollover list is verified."""
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
        )

        # The signing certificate is not the one currently assigned to the partner
        self.assertEqual(self.server_partner.active_signature_cert, self.server_crt)

        in_message = self.build_and_send(partner)

        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "S")
        self.assertTrue(out_message.signed)

    def testSignedMessageNotVerifiedWithoutRolloverCertificate(self):
        """A message signed with an unknown certificate is not verified."""
        self.server_partner.signature_cert_rollover.clear()
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=self.server_crt,
        )
        in_message = self.build_and_send(partner)

        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "E")
        self.assertIn("Failed to verify message signature", out_message.detailed_status)

    def testMessageEncryptedWithValidRolloverCertificate(self):
        """The valid certificate of the rollover list is used for encryption."""
        self.expire_certificate(self.client_crt)
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            encryption="tripledes_192_cbc",
            encryption_cert=self.client_crt,
        )
        partner.encryption_cert_rollover.add(self.server_crt)
        partner = Partner.objects.get(as2_name="as2server")
        in_message = self.build_and_send(partner)

        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.status, "S")
        self.assertTrue(out_message.encrypted)

    def testSyncMdnVerifiedWithRolloverCertificate(self):
        """A synchronous MDN is verified against the certificates of the partner."""
        # The partner signs the MDN with a certificate that has just expired
        self.expire_certificate(self.server_crt)
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
            signature_cert=self.client_crt,
        )
        partner.signature_cert_rollover.add(self.server_crt)
        partner = Partner.objects.get(as2_name="as2server")
        self.assertEqual(partner.active_signature_cert, self.client_crt)

        in_message = self.build_and_send(partner)

        self.assertEqual(in_message.status, "S")
        self.assertIsNotNone(in_message.mdn)
        self.assertTrue(in_message.mdn.signed)

    def testSyncMdnNotVerifiedWithoutRolloverCertificate(self):
        """A synchronous MDN signed with an unknown certificate is not verified."""
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
            signature_cert=self.client_crt,
        )
        in_message = self.build_and_send(partner)

        self.assertEqual(in_message.status, "E")
        self.assertIn("Failed to parse received MDN", in_message.detailed_status)

    @mock.patch("requests.post")
    def testAsyncMdnVerifiedWithRolloverCertificate(self, mock_request):
        """An asynchronous MDN is verified against the certificates of the partner."""
        # The partner signs the MDN with a certificate that has just expired
        self.expire_certificate(self.server_crt)
        partner = Partner.objects.create(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            mdn=True,
            mdn_mode="ASYNC",
            mdn_sign="sha1",
            signature_cert=self.client_crt,
        )
        partner.signature_cert_rollover.add(self.server_crt)
        partner = Partner.objects.get(as2_name="as2server")
        self.assertEqual(partner.active_signature_cert, self.client_crt)

        in_message = self.build_and_send(partner)

        out_message = Message.objects.get(
            message_id=in_message.message_id, direction="IN"
        )
        self.assertEqual(out_message.mdn.status, "P")

        # Send the async mdn to the sender
        mock_request.side_effect = SendMessageMock(self.client)
        out_message.mdn.send_async_mdn()

        mdn = Mdn.objects.filter(message=in_message).first()
        self.assertIsNotNone(mdn)
        self.assertEqual(mdn.message.status, "S")
        self.assertTrue(mdn.signed)

    @mock.patch("requests.post")
    def build_and_send(self, partner, mock_request):
        """Build a message on the client and send it to the server."""
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

        return in_message
