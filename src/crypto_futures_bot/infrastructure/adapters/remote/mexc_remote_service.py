import hashlib
import hmac
import json
import time
from typing import Any, override
from urllib.parse import urlencode

from httpx import AsyncClient, HTTPStatusError, Response, Timeout

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.adapters.remote.base import AbstractHttpRemoteAsyncService
from crypto_futures_bot.infrastructure.adapters.remote.dtos import MEXCPlaceOrderRequestDto, MEXCPlaceOrderResponseDto


class MEXCRemoteService(AbstractHttpRemoteAsyncService):
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties
        self._base_url = self._configuration_properties.mexc_web_api_base_url
        self._api_key = self._configuration_properties.mexc_api_key
        self._api_secret = self._configuration_properties.mexc_api_secret

    async def place_order(
        self, payload: MEXCPlaceOrderRequestDto, *, client: AsyncClient | None = None
    ) -> MEXCPlaceOrderResponseDto:
        body = payload.model_dump(mode="json", by_alias=True)
        response = await self._perform_http_request(
            method="POST",
            url="/v1/private/order/create",
            headers={"Content-Type": "application/json"},
            body=body,
            client=client,
        )
        ret = MEXCPlaceOrderResponseDto.model_validate_json(response.content)
        return ret

    async def get_http_client(self) -> AsyncClient:
        return AsyncClient(
            base_url=self._base_url, headers={"X-MEXC-APIKEY": self._api_key}, timeout=Timeout(10, connect=5, read=30)
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
        params = {
            name: value for name, value in params.items() if name not in ("signature", "timestamp") and bool(value)
        }
        params["timestamp"] = str(int(time.time() * 1000))  # UTC timestamp in milliseconds
        params["signature"] = await self._generate_signature_query_param(params, body)
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
            return await super()._apply_response_interceptor(
                method=method, url=url, params=params, headers=headers, body=body, response=response
            )
        except HTTPStatusError as e:
            raise ValueError(
                f"MEXC API error: HTTP {method} {self._build_full_url(url, params)} "
                + f"- Status code: {response.status_code} - {response.text}",
                response,
            ) from e

    async def _generate_signature_query_param(
        self, params: dict[str, Any] | None, body: dict[str, Any] | str | None
    ) -> str:
        if body:  # pragma: no cover
            params = params.copy() if params else {}
            body_dict = json.loads(body) if isinstance(body, str) else body
            params.update({key: value for key, value in body_dict.items() if bool(value)})
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(self._api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature

    async def _generate_signature_query_param(
        self, params: dict[str, Any] | None, body: dict[str, Any] | str | None
    ) -> str:
        if body:  # pragma: no cover
            params = params.copy() if params else {}
            body_dict = json.loads(body) if isinstance(body, str) else body
            params.update({key: value for key, value in body_dict.items() if bool(value)})
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(self._api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature
