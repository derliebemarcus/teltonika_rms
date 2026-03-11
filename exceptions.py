"""Exceptions for Teltonika RMS."""

from __future__ import annotations


class RmsApiError(Exception):
    """Raised for RMS API failures."""


class RmsAuthError(RmsApiError):
    """Raised for RMS auth/scope failures."""

