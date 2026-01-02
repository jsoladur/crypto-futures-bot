import hashlib
import hmac
import json
import time
from typing import Any, override
from urllib.parse import urlencode

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
            base_url=self._base_url, headers={"ApiKey": self._api_key}, timeout=Timeout(10, connect=5, read=30)
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
        timestamp = str(int(time.time() * 1000))  # UTC timestamp in milliseconds
        signature = self._sign(
            timestamp=timestamp, method=method, params=params if method in ["GET", "DELETE"] else body
        )
        headers.update({"Request-Time": timestamp, "Content-Type": "application/json", "Signature": signature})
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
                raise ValueError(
                    f"MEXC Contract API error: HTTP {method} {self._build_full_url(url, {})} "
                    + f"- Error code: {error_code} - {json.dumps(contract_response.data)}",
                    response,
                )
            return await super()._apply_response_interceptor(
                method=method, url=url, params=params, headers=headers, body=body, response=response
            )
        except HTTPStatusError as e:
            raise ValueError(
                f"MEXC API error: HTTP {method} {self._build_full_url(url, params)} "
                + f"- Status code: {response.status_code} - {response.text}",
                response,
            ) from e

    def _sign(self, *, timestamp: str, method: str, params: dict[str, Any] | None = None) -> str:
        """
        Generates the signature based on the documentation rules.
        """
        # Step 1: Obtain the request parameter string
        if method in ["GET", "DELETE"]:
            # Sort business parameters in dictionary order
            # Exclude None (null) values as per docs
            if not params:
                param_string = ""
            else:
                sorted_params = sorted([(k, v) for k, v in params.items() if v is not None])
                # Concatenate with & and URL-encode
                param_string = urlencode(sorted_params)
        else:
            # For POST, parameters are the JSON string (no sorting)
            # separators=(',', ':') removes whitespace to ensure hash consistency
            param_string = json.dumps(params, separators=(",", ":")) if params else ""
        # Step 2: Build the target string for signing
        # Format: accessKey + timestamp + parameterString
        target_string = f"{self._api_key}{timestamp}{param_string}"
        # Step 3: HMAC-SHA256
        signature = hmac.new(
            self._api_secret.encode("utf-8"), target_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return signature
