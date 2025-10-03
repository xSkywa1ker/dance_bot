"""Common application-wide constants."""

from datetime import timedelta

# How long a booking can remain in the ``reserved`` state without payment
RESERVATION_PAYMENT_TIMEOUT = timedelta(minutes=20)

# Metadata for system-driven booking cancellations
PAYMENT_TIMEOUT_REASON = "payment_timeout"
SYSTEM_ACTOR = "system"


__all__ = [
    "RESERVATION_PAYMENT_TIMEOUT",
    "PAYMENT_TIMEOUT_REASON",
    "SYSTEM_ACTOR",
]
