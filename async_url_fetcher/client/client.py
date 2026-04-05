import asyncio
import logging
from http import HTTPStatus
from types import TracebackType
from typing import Any, Callable, NewType, Optional, Self, Sequence, Type
from async_url_fetcher.client.entity import RequestResult, RequestResults, RequestStatus

import aiohttp
import orjson

logger = logging.getLogger(__name__)

Seconds = NewType('Seconds', int)


class AsyncUrlFetcherClient:
    def __init__(self, timeout: Seconds = 5, json_serialize: Callable[[Any], bytes] = orjson.dumps):
        self.timeout: Seconds = timeout
        self.json_serialize: Callable[[Any], bytes] = json_serialize
        self._session: aiohttp.ClientSession | None = None

    async def fetch(self, *, urls: Sequence[str], fetch_as_text: bool = False) -> RequestResults:
        if not self._session:
            raise RuntimeError("Use 'async with' to create session")

        tasks = [self._fetch(url=url, fetch_as_text=fetch_as_text) for url in urls]
        # _fetch catches all exceptions and always returns RequestResult
        # don't need call `gather` with `return_exceptions=True`
        results = await asyncio.gather(*tasks)
        return RequestResults(
            total=len(results),
            results=results,
        )

    async def _fetch(self, url: str, *, fetch_as_text: bool) -> RequestResult:
        try:
            async with self._session.get(url) as response:
                result, status, error = await self._process_response(response, fetch_as_text)
                return RequestResult(url=url, result=result, status=status, error_details=error)
        except asyncio.TimeoutError as e:
            return self._error_result(url, RequestStatus.HTTP_ERROR, f"Timeout: {repr(e)}")
        except Exception as e:
            return self._error_result(url, RequestStatus.HTTP_ERROR, f"Unexpected error: {repr(e)}")

    async def _process_response(self, response: aiohttp.ClientResponse, fetch_as_text: bool) -> tuple[
        str | None, RequestStatus, str | None]:
        if HTTPStatus.OK <= response.status < HTTPStatus.MULTIPLE_CHOICES:
            result = await response.text() if fetch_as_text else await response.json()
            return result, RequestStatus.SUCCESS, None

        status = (RequestStatus.HTTP_ERROR
                  if HTTPStatus.BAD_REQUEST <= response.status < HTTPStatus.INTERNAL_SERVER_ERROR
                  else RequestStatus.SERVER_ERROR)
        return None, status, f"{response.status}: {response.reason}"

    def _error_result(self, url: str, status: RequestStatus, error: str) -> RequestResult:
        return RequestResult(url=url, result=None, status=status, error_details=error)

    async def __aenter__(self) -> Self:
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            json_serialize=self.json_serialize,
        )
        return self

    async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]
    ):
        if exc_type is not None:
            logger.exception(f"{self.__class__.__name__} finished with error")
        if self._session:
            await self._session.close()
            self._session = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(timeout={self.timeout})"


async def main(urls: Sequence[str], *, as_text: bool, timeout: Seconds) -> None:
    async with AsyncUrlFetcherClient(timeout=timeout) as fetcher:
        result = await fetcher.fetch(urls=urls, fetch_as_text=as_text)
        logger.info("Fetching result: %s", result)
