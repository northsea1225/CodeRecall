from typing import Any, Optional

from fastapi import HTTPException, status


def error_payload(code: str, message: str, detail: Optional[Any] = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "detail": {} if detail is None else detail,
    }


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    detail: Optional[Any] = None,
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
