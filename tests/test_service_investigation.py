
import pytest

from app.investigation import investigate_service


def test_payment_api_investigation():
    """Verify Payment API returns expected graph evidence."""
    report = investigate_service("Payment API")

    assert report["service"] == "Payment API"

    affected = report["potentially_affected_services"]

    checkout = next(
        item for item in affected
        if item["service"] == "Checkout"
    )
    assert checkout["hops"] == 1
    assert checkout["dependency_path"] == [
        "Checkout",
        "Payment API",
    ]

    order_management = next(
        item for item in affected
        if item["service"] == "Order Management"
    )
    assert order_management["hops"] == 2
    assert order_management["dependency_path"] == [
        "Order Management",
        "Checkout",
        "Payment API",
    ]

    assert "Payment Platform" in report["owners"]

    assert any(
        incident["id"] == "INC-1045"
        for incident in report["incidents"]
    )

    assert any(
        runbook["id"] == "RB-PAY-01"
        for runbook in report["runbooks"]
    )


def test_service_name_is_case_insensitive():
    """Verify that different capitalization works."""
    report = investigate_service("payment API")

    assert report["service"] == "Payment API"
    assert "Payment Platform" in report["owners"]


def test_unknown_service_raises_error():
    """Verify that an unknown service is rejected."""
    with pytest.raises(
        ValueError,
        match="was not found in FalkorDB",
    ):
        investigate_service("Payment AP")


def test_empty_service_name_raises_error():
    """Verify that blank input is rejected."""
    with pytest.raises(
        ValueError,
        match="Please enter a service name",
    ):
        investigate_service("   ")
