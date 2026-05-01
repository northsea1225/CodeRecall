from typing import Any, Optional, Union

from fastapi import HTTPException, status
from pydantic import BaseModel


ErrorDetail = Union[dict[str, Any], list[dict[str, Any]], None]


class ApiErrorOut(BaseModel):
    code: str
    message: str
    detail: ErrorDetail = None


def error_payload(
    code: str,
    message: str,
    detail: ErrorDetail = None,
) -> dict[str, Any]:
    normalized: ErrorDetail = {} if detail is None else detail
    return ApiErrorOut(code=code, message=message, detail=normalized).model_dump()


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    detail: ErrorDetail = None,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=error_payload(code=code, message=message, detail=detail),
    )


def raise_not_found(resource: str, resource_id: int) -> None:
    raise_api_error(
        status_code=status.HTTP_404_NOT_FOUND,
        code=f"{resource}_not_found",
        message=f"{resource.replace('_', ' ').title()} not found.",
        detail={f"{resource}_id": resource_id},
    )
