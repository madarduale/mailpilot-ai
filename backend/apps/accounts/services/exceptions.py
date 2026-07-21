class AuthenticationServiceError(Exception):
    """Base error raised by authentication use cases."""


class EmailAlreadyRegistered(AuthenticationServiceError):
    pass


class InvalidCredentials(AuthenticationServiceError):
    pass


class InvalidRefreshToken(AuthenticationServiceError):
    pass


class IncorrectCurrentPassword(AuthenticationServiceError):
    pass

