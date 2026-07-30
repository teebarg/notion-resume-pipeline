class NotionImportError(Exception):
    """Base exception for all Notion import failures."""
    pass

class NotionPageNotFoundError(NotionImportError):
    """Raised when the requested page does not exist or lacks permissions."""
    pass

class NotionUnauthorizedError(NotionImportError):
    """Raised when the integration token is invalid or expired."""
    pass