from fastapi import HTTPException, status


class EduScanException(Exception):
    """Base exception for EduScan application."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthenticationError(HTTPException):
    """Authentication failed."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization failed."""

    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(HTTPException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


class ValidationError(HTTPException):
    """Validation failed."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class AIServiceError(EduScanException):
    """AI service error."""

    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, code=f"AI_{provider.upper()}_ERROR")


class OCRServiceError(EduScanException):
    """OCR service error."""

    def __init__(self, message: str):
        super().__init__(message, code="OCR_ERROR")


class StorageError(EduScanException):
    """Storage service error."""

    def __init__(self, message: str):
        super().__init__(message, code="STORAGE_ERROR")
