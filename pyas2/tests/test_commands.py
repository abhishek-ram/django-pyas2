"""Test the management commands of the pyas2 app."""
import os
import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.core import management
from django.core.files.base import ContentFile

from pyas2 import settings as app_settings
from pyas2.models import As2Message, Message, Mdn
from pyas2.tests import TEST_DIR
from pyas2.management.commands.sendas2bulk import Command as SendBulkCommand


@pytest.mark.django_db
def test_sendbulk_command(mocker, partner, organization):
    """Test the command for sending all files in the outbox folder"""
    mocked_call_command = mocker.patch(
        "pyas2.management.commands.sendas2bulk.call_command"
    )

    # Call the command
    command = SendBulkCommand()
    command.handle()

    # Create a file for testing and try again
    outbox_dir = os.path.join(
        "messages", partner.as2_name, "outbox", organization.as2_name
    )
    test_file = Path(os.path.join(outbox_dir, "testmessage.edi"))
    test_file.touch()
    command.handle()
    mocked_call_command.assert_called_with(
        "sendas2message",
        organization.as2_name,
        partner.as2_name,
        str(test_file),
        delete=True,
    )

    # Try with the data directory
    app_settings.DATA_DIR = settings.BASE_DIR
    command.handle()

    # Delete the folder
    app_settings.DATA_DIR = None
    shutil.rmtree(outbox_dir)


@pytest.mark.django_db
def test_sendmessage_command(mocker, organization, partner):
    """Test the command for sending an as2 message"""
    test_message = os.path.join(TEST_DIR, "testmessage.edi")

    # Try to run with invalid org and client
    with pytest.raises(management.CommandError):
        management.call_command(
            "sendas2message", "AS2 Server", "AS2 Client", test_message
        )
    with pytest.raises(management.CommandError):
        management.call_command(
            "sendas2message", organization.as2_name, "AS2 Client", test_message
        )

    with pytest.raises(management.CommandError):
        management.call_command(
            "sendas2message", organization.as2_name, partner.as2_name, "testmessage.edi"
        )

    # Try again with a valid org
    management.call_command(
        "sendas2message", organization.as2_name, partner.as2_name, test_message
    )

    # Try again with delete function
    mocked_delete = mocker.patch(
        "pyas2.management.commands.sendas2message.default_storage.delete"
    )
    management.call_command(
        "sendas2message",
        organization.as2_name,
        partner.as2_name,
        test_message,
        delete=True,
    )
    assert mocked_delete.call_count == 1


@pytest.mark.django_db
def test_manageserver_command(mocker, organization, partner):
    """Test the command for managing the as2 server."""
    app_settings.MAX_ARCH_DAYS = -1

    # Create a message
    with open(os.path.join(TEST_DIR, "testmessage.edi"), "rb") as fp:
        payload = fp.read()
    as2message = As2Message(sender=organization.as2org, receiver=partner.as2partner)
    as2message.build(
        payload,
        filename="testmessage.edi",
        subject=partner.subject,
        content_type=partner.content_type,
    )
    out_message, _ = Message.objects.create_from_as2message(
        as2message=as2message, payload=payload, direction="OUT", status="P"
    )
    out_message.send_message(as2message.headers, as2message.content)

    # Test the retry command
    out_message.refresh_from_db()
    assert out_message.status == "R"
    management.call_command("manageas2server", retry=True)
    out_message.refresh_from_db()
    assert out_message.retries == 1

    # Test max retry setting
    app_settings.MAX_RETRIES = 1
    management.call_command("manageas2server", retry=True)
    out_message.refresh_from_db()
    assert out_message.retries == 2
    assert out_message.status == "E"

    # Test the async mdn command for outbound messages, retry when no MDN received
    app_settings.ASYNC_MDN_WAIT = 0
    out_message.status = "P"
    out_message.retries = 0
    out_message.save()
    management.call_command("manageas2server", async_mdns=True)
    out_message.refresh_from_db()
    assert out_message.status == "R"
    assert out_message.retries == 1

    # Test the async mdn command for outbound messages, finally fail when no MDN received
    app_settings.ASYNC_MDN_WAIT = 0
    out_message.status = "P"
    out_message.save()
    management.call_command("manageas2server", async_mdns=True)
    out_message.refresh_from_db()
    assert out_message.status == "E"

    # Test the async mdn command for outbound mdns
    mdn = Mdn.objects.create(mdn_id="some-mdn-id", message=out_message, status="P")
    mdn.headers.save("some-mdn-id.headers", ContentFile(""))
    mdn.payload.save("some-mdn-id.mdn", ContentFile("MDN Content"))
    management.call_command("manageas2server", async_mdns=True)
    mdn.refresh_from_db()
    assert mdn.status == "P"
    mocked_post = mocker.patch("requests.post")
    management.call_command("manageas2server", async_mdns=True)
    mdn.refresh_from_db()
    assert mocked_post.call_count == 1
    assert mdn.status == "S"

    # Test the clean command
    management.call_command("manageas2server", clean=True)
    assert Message.objects.filter(message_id=out_message.message_id).count() == 0
    assert Mdn.objects.filter(mdn_id=out_message.mdn.mdn_id).count() == 0

    # Test the clean command without MDN set
    out_message, _ = Message.objects.create_from_as2message(
        as2message=as2message, payload=payload, direction="OUT", status="P"
    )
    management.call_command("manageas2server", clean=True)
    assert Message.objects.filter(message_id=out_message.message_id).count() == 0
