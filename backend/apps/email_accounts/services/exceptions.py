class EmailAccountServiceError(Exception):
    """Base error for safe OAuth service failures."""


class OAuthConfigurationError(EmailAccountServiceError):
    pass


class InvalidOAuthState(EmailAccountServiceError):
    pass


class OAuthExchangeFailed(EmailAccountServiceError):
    pass


class OAuthIdentityInvalid(EmailAccountServiceError):
    pass


class RefreshTokenUnavailable(EmailAccountServiceError):
    pass
