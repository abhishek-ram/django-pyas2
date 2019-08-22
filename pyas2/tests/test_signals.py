from unittest.mock import Mock

import pytest

from pyas2.models import Message, Partner
from pyas2.signals import post_send, post_receive
from pyas2.utils import run_post_send, run_post_receive


@pytest.mark.django_db
class TestPostReceiveSignal:

    @pytest.fixture
    def partner(self):
        return Partner.objects.create(
            name='AS2 Client',
            as2_name='as2client',
            target_url='http://localhost:8080/pyas2/as2receive',
            compress=False,
            mdn=False,
        )

    @pytest.fixture
    def message(self, partner):
        return Message.objects.create(partner=partner)

    def test_run_post_receive_triggers_signal(self, message):
        callback = Mock()
        full_filename = "dummy_full_name"

        post_receive.connect(callback)
        run_post_receive(message, full_filename)
        post_receive.disconnect(callback)

        callback.assert_called_once_with(message=message, full_filename=full_filename, sender=Message, signal=post_receive)


@pytest.mark.django_db
class TestPostSendSignal:

    @pytest.fixture
    def partner(self):
        return Partner.objects.create(
            name='AS2 Client',
            as2_name='as2client',
            target_url='http://localhost:8080/pyas2/as2receive',
            compress=False,
            mdn=False,
        )

    @pytest.fixture
    def message(self, partner):
        return Message.objects.create(partner=partner)

    def test_run_post_send_triggers_signal(self, message):
        callback = Mock()

        post_send.connect(callback)
        run_post_send(message)
        post_send.disconnect(callback)

        callback.assert_called_once_with(message=message, sender=Message, signal=post_send)
