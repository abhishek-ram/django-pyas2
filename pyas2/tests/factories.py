import os.path

import factory

from pyas2.models import Organization, Partner, PrivateKey, PublicCertificate


FIXTURES_DIR = os.path.join((os.path.dirname(os.path.abspath(__file__))),  "fixtures")


def load_key(name):
    with open(os.path.join(FIXTURES_DIR, name), "rb") as fd:
        return fd.read()


class PrivateKeyFactory(factory.DjangoModelFactory):
    class Meta:
        model = PrivateKey

    class Params:
        is_server = factory.Trait(
            key=factory.LazyAttribute(lambda x: load_key("server_private.pem"))
        )
        is_client = factory.Trait(
            key=factory.LazyAttribute(lambda x: load_key("client_private.pem"))
        )

    key_pass = "test"


class PublicCertificateFactory(factory.DjangoModelFactory):
    class Meta:
        model = PublicCertificate

    class Params:
        is_server = factory.Trait(
            certificate=factory.LazyAttribute(lambda x: load_key("server_public.pem"))
        )
        is_client = factory.Trait(
            certificate=factory.LazyAttribute(lambda x: load_key("client_public.pem"))
        )


class OrganizationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Organization

    class Params:
        is_server = factory.Trait(
            name="AS2 Server",
            as2_name="as2server",
            encryption_key=factory.SubFactory(PrivateKeyFactory, is_server=True),
            signature_key=factory.SubFactory(PrivateKeyFactory, is_server=True)
        )
        is_client = factory.Trait(
            name="AS2 Client",
            as2_name="as2client",
            encryption_key=factory.SubFactory(PrivateKeyFactory, is_client=True),
            signature_key=factory.SubFactory(PrivateKeyFactory, is_client=True)
        )
    

class PartnerFactory(factory.DjangoModelFactory):
    class Meta:
        model = Partner

    class Params:
        is_server = factory.Trait(
            name="AS2 Server",
            as2_name="as2server",
            target_url="http://localhost:8080/pyas2/as2receive",
            signature="sha1",
            signature_cert=factory.SubFactory(PublicCertificateFactory, is_server=True),
            encryption="tripledes_192_cbc",
            encryption_cert=factory.SubFactory(PublicCertificateFactory, is_server=True),
            mdn=True,
            mdn_mode="SYNC",
            mdn_sign="sha1",
        )
        is_client = factory.Trait(
            name="AS2 Client",
            as2_name="as2client",
            target_url="http://localhost:8080/pyas2/as2receive",
            compress=False,
            mdn=False,
            signature_cert=factory.SubFactory(PublicCertificateFactory, is_client=True),
            encryption_cert=factory.SubFactory(PublicCertificateFactory, is_client=True),
        )
