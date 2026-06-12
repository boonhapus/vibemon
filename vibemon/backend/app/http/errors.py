"""Map request validation errors to HTTP responses."""

from litestar import Request, Response
from litestar.exceptions import ValidationException
from litestar.status_codes import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_501_NOT_IMPLEMENTED

from app.core.errors import ProviderNotImplemented, VibemonServiceError, interface_error_code


def _validation_message(exc: ValidationException) -> str:
    if exc.extra:
        message = str(exc.extra[0].get("message", exc.detail))
        return message.removeprefix("Value error, ")
    return str(exc.detail)


def validation_exception_handler(_: Request, exc: ValidationException) -> Response:
    return Response(
        content={"status_code": HTTP_422_UNPROCESSABLE_ENTITY, "detail": _validation_message(exc)},
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    )


def service_exception_handler(_: Request, exc: VibemonServiceError) -> Response:
    status_code = HTTP_422_UNPROCESSABLE_ENTITY
    if isinstance(exc, ProviderNotImplemented):
        status_code = HTTP_501_NOT_IMPLEMENTED
    return Response(
        content={"detail": str(exc), "code": interface_error_code(exc).value},
        status_code=status_code,
    )
