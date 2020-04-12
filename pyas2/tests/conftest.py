"""Define the test fixtures and other configurations for the test cases."""
import pytest
from pyas2.models import Organization, Partner


@pytest.fixture
def organization():
    """Create a organization object for use in the test cases."""
    return Organization.objects.create(
        name="AS2 Server",
        as2_name="as2server",
        confirmation_message="Custom confirmation message.",
    )


@pytest.fixture
def partner():
    """Create a partner object for use in the test cases."""
    return Partner.objects.create(
        name="AS2 Client",
        as2_name="as2client",
        target_url="http://localhost:8080/pyas2/as2receive",
        confirmation_message="Custom confirmation message.",
        compress=False,
        mdn=False,
    )
