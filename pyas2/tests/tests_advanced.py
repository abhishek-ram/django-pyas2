from __future__ import unicode_literals
from django.test import TestCase, Client, LiveServerTestCase
from django.core.exceptions import ObjectDoesNotExist
from pyas2.models import PrivateKey, PublicCertificate, Organization, Partner, \
    Message, MDN
from pyas2lib.as2 import Message as As2Message, Mdn as As2Mdn
from requests import Response
from itertools import izip
import mock
import os

TEST_DIR = os.path.join((os.path.dirname(
    os.path.abspath(__file__))),  'fixtures')


