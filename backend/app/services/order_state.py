from fastapi import HTTPException, status

ORDER_STATES = {
    "PENDING",
    "CONFIRMED",
    "PREPARING",
    "READY_FOR_PICKUP",
    "IN_TRANSIT",
    "DELIVERED",
    "CANCELLED",
}

ALLOWED_TRANSITIONS = {
    "PENDING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"PREPARING", "CANCELLED"},
    "PREPARING": {"READY_FOR_PICKUP", "CANCELLED"},
    "READY_FOR_PICKUP": {"IN_TRANSIT"},
    "IN_TRANSIT": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}

ROLE_TRANSITIONS = {
    "CONSUMER": {"CANCELLED"},
    "FARMER": {"CONFIRMED", "PREPARING", "READY_FOR_PICKUP", "CANCELLED"},
    "FPO": {"CONFIRMED", "PREPARING", "READY_FOR_PICKUP", "CANCELLED"},
    "LOGISTICS": {"IN_TRANSIT", "DELIVERED"},
    "ADMIN": ORDER_STATES,
}


def validate_transition(current: str, target: str, role: str) -> None:
    if target not in ORDER_STATES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown order state")
    if target not in ROLE_TRANSITIONS.get(role, set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This role cannot set that order state")
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid order transition: {current} -> {target}",
        )
