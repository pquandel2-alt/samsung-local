"""Classified exceptions exposed by Samsung Local adapters."""

from __future__ import annotations


class SamsungLocalError(Exception):
    """Base error for the integration."""


class CannotConnectError(SamsungLocalError):
    """The device did not establish a usable local connection."""


class AuthenticationError(SamsungLocalError):
    """The device rejected local authentication."""


class UnsupportedDeviceError(SamsungLocalError):
    """The endpoint is not a supported Samsung local device."""


class CommandNotSupportedError(SamsungLocalError):
    """The requested command is not advertised by the device."""


class CommandRejectedError(SamsungLocalError):
    """The device received but refused a command."""


class RemoteControlDisabledError(CommandRejectedError):
    """A safety gate refused a write while local remote control is off."""


class InvalidCommandError(SamsungLocalError):
    """A command value failed local validation."""


class ConcurrentSessionError(CannotConnectError):
    """The device appears to be occupied by another local client."""
