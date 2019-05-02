from __future__ import unicode_literals
from django.test import TestCase, Client
from pyas2.models import PrivateKey, PublicCertificate, Organization, Partner, \
    Message, Mdn
from pyas2 import settings
from pyas2lib.as2 import Message as As2Message
from email.parser import HeaderParser
from requests import Response
try:
    from itertools import izip as zip
except ImportError: # will be 3.x series
    pass
import mock
import os

TEST_DIR = os.path.join((os.path.dirname(
    os.path.abspath(__file__))),  'fixtures')


class BasicServerClientTestCase(TestCase):
    """Test cases for the AS2 server and client.
    We will be testing each permutation as defined in RFC 4130 Section 2.4.2
    """
    @classmethod
    def setUpTestData(cls):
        # Every test needs a client.
        cls.client = Client()
        cls.header_parser = HeaderParser()

        # Load the client and server certificates
        with open(os.path.join(TEST_DIR, 'server_private.pem'), 'rb') as fp:
            cls.server_key = PrivateKey.objects.create(
                key=fp.read(), key_pass='test')

        with open(os.path.join(TEST_DIR, 'server_public.pem'), 'rb') as fp:
            cls.server_crt = PublicCertificate.objects.create(
                certificate=fp.read())

        with open(os.path.join(TEST_DIR, 'client_private.pem'), 'rb') as fp:
            cls.client_key = PrivateKey.objects.create(
                key=fp.read(), key_pass='test')

        with open(os.path.join(TEST_DIR, 'client_public.pem'), 'rb') as fp:
            cls.client_crt = PublicCertificate.objects.create(
                certificate=fp.read()
            )

        # Setup the server organization and partner
        Organization.objects.create(
            name='AS2 Server',
            as2_name='as2server',
            encryption_key=cls.server_key,
            signature_key=cls.server_key
        )
        Partner.objects.create(
            name='AS2 Client',
            as2_name='as2client',
            target_url='http://localhost:8080/pyas2/as2receive',
            compress=False,
            mdn=False,
            signature_cert=cls.client_crt,
            encryption_cert=cls.client_crt
        )

        # Setup the client organization and partner
        cls.organization = Organization.objects.create(
            name='AS2 Client',
            as2_name='as2client',
            encryption_key=cls.client_key,
            signature_key=cls.client_key
        )

        # Initialise the payload i.e. the file to be transmitted
        with open(os.path.join(TEST_DIR, 'testmessage.edi'), 'rb') as fp:
            cls.payload = fp.read()

    def tearDown(self):
        # remove all files in the inbox folders
        inbox = os.path.join(
            settings.DATA_DIR, 'messages', 'as2server', 'inbox', 'as2client')
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

    def testEndpoint(self):
        """ Test if the as2 reveive endpoint is active """

        response = self.client.get('/pyas2/as2receive')
        self.assertEqual(response.status_code, 200)

    def testNoEncryptMessageNoMdn(self):
        """ Test Permutation 1: Sender sends un-encrypted data and does
        NOT request a receipt. """

        # Create the partner with appropriate settings for this case
        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            mdn=False
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertFalse(hasattr(in_message, 'mdn'))

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testNoEncryptMessageMdn(self):
        """ Test Permutation 2: Sender sends un-encrypted data and requests an
        unsigned receipt. """

        # Create the partner with appropriate settings for this case
        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            mdn=True,
            mdn_mode='SYNC'
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)
        self.assertFalse(in_message.mdn.signed)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testNoEncryptMessageSignMdn(self):
        """ Test Permutation 3: Sender sends un-encrypted data and requests a
        signed receipt. """

        # Create the partner with appropriate settings for this case
        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            mdn=True,
            mdn_mode='SYNC',
            mdn_sign='sha1',
            signature_cert=self.server_crt
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)
        self.assertTrue(in_message.mdn.signed)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testEncryptMessageNoMdn(self):
        """ Test Permutation 4: Sender sends encrypted data and does NOT
        request a receipt. """

        # Create the partner with appropriate settings for this case
        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.encrypted)
        self.assertEqual(in_message.status, 'S')

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testEncryptMessageMdn(self):
        """ Test Permutation 5: Sender sends encrypted data and requests an
         unsigned receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode='SYNC'
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.encrypted)
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testEncryptMessageSignMdn(self):
        """ Test Permutation 6: Sender sends encrypted data and requests
        an signed receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode='SYNC',
            mdn_sign='sha1',
            signature_cert=self.server_crt
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.encrypted)
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)
        self.assertTrue(in_message.mdn.signed)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testSignMessageNoMdn(self):
        """ Test Permutation 7: Sender sends signed data and does NOT request
         a receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            signature='sha1',
            signature_cert=self.server_crt
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.signed)
        self.assertEqual(in_message.status, 'S')

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testSignMessageMdn(self):
        """ Test Permutation 8: Sender sends signed data and requests an
        unsigned receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            signature='sha1',
            signature_cert=self.server_crt,
            mdn=True,
            mdn_mode='SYNC',
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.signed)
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testSignMessageSignMdn(self):
        """ Test Permutation 9: Sender sends signed data and requests a
         signed receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            signature='sha1',
            signature_cert=self.server_crt,
            mdn=True,
            mdn_mode='SYNC',
            mdn_sign='sha1'
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.signed)
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)
        self.assertTrue(in_message.mdn.signed)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testEncryptSignMessageNoMdn(self):
        """ Test Permutation 10: Sender sends encrypted and signed data and
        does NOT request a receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            signature='sha1',
            signature_cert=self.server_crt,
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt,
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.signed)
        self.assertTrue(out_message.encrypted)
        self.assertEqual(in_message.status, 'S')

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testEncryptSignMessageMdn(self):
        """ Test Permutation 11: Sender sends encrypted and signed data and
        requests an unsigned receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            signature='sha1',
            signature_cert=self.server_crt,
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode='SYNC',
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.signed)
        self.assertTrue(out_message.encrypted)
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testEncryptSignMessageSignMdn(self):
        """ Test Permutation 12: Sender sends encrypted and signed data and
        requests a signed receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            signature='sha1',
            signature_cert=self.server_crt,
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode='SYNC',
            mdn_sign='sha1'
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.signed)
        self.assertTrue(out_message.encrypted)
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)
        self.assertTrue(in_message.mdn.signed)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    def testCompressEncryptSignMessageSignMdn(self):
        """ Test Permutation 13: Sender sends compressed, encrypted and signed
         data and requests an signed receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            compress=True,
            signature='sha1',
            signature_cert=self.server_crt,
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode='SYNC',
            mdn_sign='sha1'
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.compressed)
        self.assertTrue(out_message.signed)
        self.assertTrue(out_message.encrypted)
        self.assertEqual(in_message.status, 'S')
        self.assertIsNotNone(in_message.mdn)
        self.assertTrue(in_message.mdn.signed)

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    @mock.patch('requests.post')
    def testEncryptSignMessageAsyncSignMdn(self, mock_request):
        """ Test Permutation 14: Sender sends encrypted and signed data and
        requests an Asynchronous signed receipt. """

        partner = Partner.objects.create(
            name='AS2 Server', as2_name='as2server',
            target_url='http://localhost:8080/pyas2/as2receive',
            signature='sha1',
            signature_cert=self.server_crt,
            encryption='tripledes_192_cbc',
            encryption_cert=self.server_crt,
            mdn=True,
            mdn_mode='ASYNC',
            mdn_sign='sha1'
        )
        in_message = self.build_and_send(partner)

        # Check if message was processed successfully
        out_message = Message.objects.get(
            message_id=in_message.message_id, direction='IN')
        self.assertEqual(out_message.status, 'S')
        self.assertTrue(out_message.signed)
        self.assertTrue(out_message.encrypted)
        self.assertEqual(out_message.mdn.status, 'P')
        self.assertIsNotNone(out_message.mdn.return_url)

        # Check mdn not sent
        self.assertFalse(hasattr(in_message, 'mdn'))

        # Send the async mdn to the sender
        mock_request.side_effect = SendMessageMock(self.client)
        out_message.mdn.send_async_mdn()

        # Make sure the mdn has been created
        mdn = Mdn.objects.filter(message=in_message).first()
        self.assertIsNotNone(mdn)
        self.assertEqual(mdn.message.status, 'S')
        self.assertTrue(mdn.signed)
        out_message.mdn.refresh_from_db()
        self.assertEqual(out_message.mdn.status, 'S')

        # Check if input and output files are the same
        self.assertTrue(
            self.compareFiles(in_message.payload.name,
                              out_message.payload.name)
        )

    @mock.patch('requests.post')
    def build_and_send(self, partner, mock_request):
        # Build and send the message to server
        as2message = As2Message(
            sender=self.organization.as2org,
            receiver=partner.as2partner)
        as2message.build(
            self.payload,
            filename='testmessage.edi',
            subject=partner.subject,
            content_type=partner.content_type
        )
        in_message, _ = Message.objects.create_from_as2message(
            as2message=as2message,
            payload=self.payload,
            direction='OUT',
            status='P'
        )

        mock_request.side_effect = SendMessageMock(self.client)
        in_message.send_message(as2message.headers, as2message.content)

        return in_message

    @staticmethod
    def compareFiles(filename1, filename2):
        with open(filename1, "rt") as a:
            with open(filename2, "rt") as b:
                # Note that "all" and "zip" are lazy
                # (will stop at the first line that's not identical)
                return all(lineA == lineB for lineA, lineB in
                           zip(a.readlines(), b.readlines()))


class SendMessageMock(object):

    def __init__(self, test_client):
        self.test_client = test_client

    def __call__(self, *args, **kwargs):
        # Get the content type
        content_type = kwargs['headers'].pop('Content-Type')

        # build the http headers
        http_headers = {}
        for key, value in kwargs['headers'].items():
            key = 'HTTP_%s' % key.replace('-', '_').upper()
            http_headers[key] = value

        # send the test request and check response
        response = self.test_client.post(
            '/pyas2/as2receive', data=kwargs['data'],
            content_type=content_type, **http_headers)
        assert response.status_code == 200

        # Create a request.Response from django.HttpResponse
        req_response = Response()
        req_response._content = response.content

        for h_key, h_value in response._headers.values():
            req_response.headers[h_key] = h_value

        req_response.status_code = response.status_code
        return req_response
