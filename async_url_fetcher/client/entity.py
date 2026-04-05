import enum
from enum import StrEnum
from typing import Any

import attrs


class RequestStatus(StrEnum):
    SUCCESS = enum.auto()
    HTTP_ERROR = enum.auto()
    SERVER_ERROR = enum.auto()


@attrs.define(frozen=True)
class RequestResult:
    url: str
    result: Any | None
    status: RequestStatus
    error_details: str | None


@attrs.define(frozen=True)
class RequestResults:
    total: int
    results: list[RequestResult]
