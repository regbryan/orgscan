import pytest
from checks import Finding


@pytest.fixture
def sample_finding():
    return Finding(
        category="Users",
        severity="Critical",
        title="Inactive user with license",
        detail="John Smith — last login 8 months ago",
        recommendation="Deactivate or reassign license",
    )


@pytest.fixture
def sample_flow_finding():
    return Finding(
        category="Flows",
        severity="Warning",
        title="Flow has no description",
        detail="Lead_Assignment has no description",
        recommendation="Generate with AI",
        flow_api_name="Lead_Assignment",
    )
