class SuggestionNotFoundError(Exception):
    """Raised when a suggestion is absent or belongs to another user."""


class SuggestionNotActionableError(Exception):
    """Raised when a terminal suggestion receives another lifecycle action."""
