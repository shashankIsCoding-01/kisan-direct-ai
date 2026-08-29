import pytest
from fastapi import HTTPException

from app.services.order_state import validate_transition


@pytest.mark.parametrize(
    ("current", "target", "role"),
    [
        ("PENDING", "CONFIRMED", "FARMER"),
        ("CONFIRMED", "PREPARING", "FARMER"),
        ("PREPARING", "READY_FOR_PICKUP", "FPO"),
        ("READY_FOR_PICKUP", "IN_TRANSIT", "LOGISTICS"),
        ("IN_TRANSIT", "DELIVERED", "LOGISTICS"),
        ("PENDING", "CANCELLED", "CONSUMER"),
    ],
)
def test_valid_order_transitions_are_allowed(current, target, role):
    validate_transition(current, target, role)


@pytest.mark.parametrize(
    ("current", "target", "role"),
    [
        ("DELIVERED", "PENDING", "ADMIN"),
        ("CANCELLED", "CONFIRMED", "ADMIN"),
        ("PENDING", "PREPARING", "FARMER"),
        ("CONFIRMED", "DELIVERED", "LOGISTICS"),
        ("DELIVERED", "DELIVERED", "ADMIN"),
    ],
)
def test_invalid_order_transitions_are_rejected(current, target, role):
    with pytest.raises(HTTPException) as error:
        validate_transition(current, target, role)

    assert error.value.status_code in {403, 409}


def test_unknown_order_state_is_rejected():
    with pytest.raises(HTTPException) as error:
        validate_transition("PENDING", "UNKNOWN", "ADMIN")

    assert error.value.status_code == 422
