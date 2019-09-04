import os.path

import mock
import pytest
from django.test import Client
from pyas2lib import Message as As2Message

from pyas2.models import Message, Partner
from pyas2.tests.test_basic import SendMessageMock
from pyas2.tests.factories import OrganizationFactory, PartnerFactory


TEST_DIR = os.path.join((os.path.dirname(
    os.path.abspath(__file__))),  'fixtures')


def build_and_send(organization, payload, partner, mock_request, smudge=False):
    # Build and send the message to server
    as2message = As2Message(
        sender=organization.as2org,
        receiver=partner.as2partner)
    as2message.build(
        payload,
        filename='testmessage.edi',
        subject=partner.subject,
        content_type=partner.content_type
    )
    out_message, _ = Message.objects.create_from_as2message(
        as2message=as2message,
        payload=payload,
        direction='OUT',
        status='P'
    )
    mock_request.side_effect = SendMessageMock(Client())
    out_message.send_message(
        as2message.headers,
        b'xxxx' + as2message.content if smudge else as2message.content
    )

    return out_message


@pytest.mark.django_db
class TestEnableInboxSwitch:

    @pytest.fixture
    def payload(self):
        with open(os.path.join(TEST_DIR, "testmessage.edi"), "rb") as fd:
            return fd.read()

    @pytest.fixture
    def mocked_request(self, mocker):
        return mocker.patch("requests.post")

    @pytest.fixture
    def server_org(self):
        return OrganizationFactory(is_server=True)

    @pytest.fixture
    def client_org(sefl):
        return OrganizationFactory(is_client=True)

    @pytest.fixture
    def server_partner(self):
        return PartnerFactory(is_server=True)

    @pytest.fixture
    def client_partner(self):
        return PartnerFactory(is_client=True)

    @pytest.fixture
    def disabled_inbox(self, mocker):
        settings = mocker.patch("pyas2.models.settings")
        settings.ENABLE_INBOX = False
        return settings

    @pytest.fixture
    def mocked_store_file(self, mocker):
        return mocker.patch("pyas2.models.store_file")

    def test_use_disable_inbox_storage(self, disabled_inbox, mocked_store_file, server_org, 
                                       client_org, server_partner, client_partner, mocked_request, payload):
      
        in_message = build_and_send(client_org, payload, server_partner, mocked_request)
        assert in_message.status == 'S'

        # Check store_file was never called
        assert mocked_store_file.called is False
