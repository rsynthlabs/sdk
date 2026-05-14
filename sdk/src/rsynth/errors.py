class RsynthError(Exception):
    """Base class for rsynth SDK errors."""


class InvalidPayloadError(RsynthError):
    pass


class SignatureError(RsynthError):
    pass


class AnchorError(RsynthError):
    pass
