import hashlib
import json
import time
from typing import Any, override

from httpx import AsyncClient, HTTPStatusError, Response, Timeout

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.adapters.remote.base import AbstractHttpRemoteAsyncService
from crypto_futures_bot.infrastructure.adapters.remote.dtos import (
    MEXCContractResponseDto,
    MEXCPlaceOrderRequestDto,
    MEXCPlaceOrderResponseDto,
)


class MEXCRemoteService(AbstractHttpRemoteAsyncService):
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties
        self._base_url = self._configuration_properties.mexc_web_api_base_url
        self._api_key = self._configuration_properties.mexc_api_key
        self._api_secret = self._configuration_properties.mexc_api_secret
        self._web_auth_token = self._configuration_properties.mexc_web_auth_token

    async def place_order(
        self, payload: MEXCPlaceOrderRequestDto, *, client: AsyncClient | None = None
    ) -> MEXCPlaceOrderResponseDto:
        body = payload.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_unset=True)
        response = await self._perform_http_request(
            method="POST", url="/v1/private/order/create", body=body, client=client
        )
        ret = MEXCContractResponseDto[MEXCPlaceOrderResponseDto].model_validate_json(response.content)
        return ret.data

    async def get_http_client(self) -> AsyncClient:
        return AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": self._web_auth_token,
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9,ru;q=0.8,it;q=0.7,la;q=0.6,vi;q=0.5,lb;q=0.4",
                "cache-control": "no-cache",
                "content-type": "application/json",
                "dnt": "1",
                "language": "English",
                "origin": "https://www.mexc.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://www.mexc.com/",
                "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36"
                ),
                "x-language": "en-US",
            },
            timeout=Timeout(10, connect=5, read=30),
        )

    @override
    async def _apply_request_interceptor(
        self,
        *,
        method: str = "GET",
        url: str = "/",
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]:
        params, headers = await super()._apply_request_interceptor(
            method=method, url=url, params=params, headers=headers, body=body
        )
        headers = headers or {}
        timestamp, signature = self._sign(auth_token=self._web_auth_token, params=body if body is not None else {})
        headers.update({"x-mxc-nonce": timestamp, "x-mxc-sign": signature})
        return params, headers

    @override
    async def _apply_response_interceptor(
        self,
        *,
        method: str = "GET",
        url: str = "/",
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        body: Any | None = None,
        response: Response,
    ) -> Response:
        params = params or {}
        headers = headers or {}
        try:
            response.raise_for_status()
            contract_response = MEXCContractResponseDto[Any].model_validate_json(response.content)
            if not contract_response.success:
                error_code = str(contract_response.code)
                error_message = contract_response.message or (
                    json.dumps(contract_response.data) if contract_response.data else "No error message provided"
                )
                raise ValueError(
                    f"MEXC Contract API error: HTTP {method} {self._build_full_url(url, {})} "
                    + f"- Error code: {error_code} - {error_message}"
                )
            return await super()._apply_response_interceptor(
                method=method, url=url, params=params, headers=headers, body=body, response=response
            )
        except HTTPStatusError as e:
            raise ValueError(
                f"MEXC API error: HTTP {method} {self._build_full_url(url, params)} "
                + f"- Status code: {response.status_code} - {response.text}"
            ) from e

    def _sign(self, *, auth_token: str, params: dict[str, Any] | None = None) -> tuple[str, str]:
        """
        Generates the signature based on the documentation rules.
        """
        timestamp = str(int(time.time() * 1000))  # UTC timestamp in milliseconds
        g = self._calculate_md5(auth_token + timestamp)[7:]
        s = json.dumps(params, separators=(",", ":"), ensure_ascii=False)
        sign = self._calculate_md5(timestamp + s + g)
        return timestamp, sign

    def _calculate_md5(self, value: str) -> str:
        return hashlib.md5(value.encode("utf-8")).hexdigest()  # nosec: B324
