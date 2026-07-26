"""
    .. module:: azurearmclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`AzureArmClient` — the signed transport for Azure
               Resource Manager, including long-running-operation polling.

    ARM is one uniform REST protocol: every resource is addressed by a path
    under ``/subscriptions/{id}/resourceGroups/{name}/providers/...``, every
    call carries an ``api-version``, collections page through ``nextLink``,
    and mutations may be long-running.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import json
import os
import time

from typing import Any, Dict, List, Optional

import requests

from ccai.restclient.azure.azurearmerror import (
    AzureOperationError, AzureOperationTimeout, AzureRequestError,
    ResourceNotFoundError
)
from ccai.restclient.azure.azureobject import AzureObject, wrap_azure_value
from ccai.restclient.azure.azuretokenprovider import AzureTokenProvider


ARM_ENDPOINT = "https://management.azure.com"

DEFAULT_TIMEOUT_SECONDS = 60.0

DEFAULT_POLL_INTERVAL_SECONDS = 5.0

DEFAULT_OPERATION_TIMEOUT_SECONDS = 1800.0

TERMINAL_SUCCESS = ("succeeded",)

TERMINAL_FAILURE = ("failed", "canceled", "cancelled")


class LroPoller:
    """
        A handle on a long-running ARM operation.

        Mirrors the SDK's ``LROPoller`` closely enough for consumer code:
        :meth:`result` blocks until the operation reaches a terminal state and
        returns the resource.

        When ARM answers a mutation synchronously — a ``200`` or ``201`` with
        the resource and no operation headers — there is nothing to poll, so
        :meth:`result` returns immediately.  That case is common and must not
        be turned into a wait.
    """

    def __init__(self, *, client: Any, resource: AzureObject,
                 monitor_url: Optional[str] = None,
                 final_url: Optional[str] = None,
                 poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS
                 ) -> None:
        """
            Construct an LroPoller.

            :param client: The owning :class:`AzureArmClient`.
            :param resource: The resource body from the initial response.
            :param monitor_url: The URL reporting operation status, from the
                ``Azure-AsyncOperation`` or ``Location`` header.
            :param final_url: The URL to GET for the finished resource.
            :param poll_interval: Seconds between status checks.
        """
        self._client = client
        self._resource: AzureObject = resource
        self._monitor_url: Optional[str] = monitor_url
        self._final_url: Optional[str] = final_url
        self._poll_interval: float = poll_interval
        return

    def done(self) -> bool:
        """
            Report whether the operation needs no further polling.

            :returns: True when there is nothing to wait on.
        """
        rtnval = self._monitor_url is None
        return rtnval

    def result(self, timeout: Optional[float] = None) -> AzureObject:
        """
            Wait for the operation and return the resource.

            :param timeout: Seconds to wait before giving up.

            :returns: The resource.

            :raises: :class:`AzureOperationError` when the operation reports
                a failed or cancelled terminal state;
                :class:`AzureOperationTimeout` when it has not finished in
                time.
        """
        if self._monitor_url is None:
            rtnval = self._resource
            return rtnval

        budget = timeout
        if budget is None:
            budget = DEFAULT_OPERATION_TIMEOUT_SECONDS

        deadline = time.time() + budget

        while True:
            payload = self._client.request_absolute(method="GET",
                                                    url=self._monitor_url)

            status = payload.get("status", None)
            if status is None:
                # A Location-header monitor answers with the resource itself
                # once it is ready, and carries no status field.
                self._resource = payload
                rtnval = self._resource
                return rtnval

            lowered = str(status).lower()

            if lowered in TERMINAL_SUCCESS:
                rtnval = self._finished_resource()
                return rtnval

            if lowered in TERMINAL_FAILURE:
                detail = self._client.describe_error(payload=payload)
                err_msg_lines = [
                    "The Azure long-running operation did not succeed."
                ]
                err_msg_lines.append("STATUS: {}".format(status))
                err_msg_lines.append("DETAIL: {}".format(detail))
                err_msg = os.linesep.join(err_msg_lines)
                raise AzureOperationError(err_msg, code=str(status))

            if time.time() >= deadline:
                err_msg_lines = [
                    "Timed out waiting for an Azure long-running operation."
                ]
                err_msg_lines.append("LAST STATUS: {}".format(status))
                err_msg_lines.append("WAITED: {:.0f}s".format(budget))
                err_msg_lines.append(
                    "The operation may still be running; this is a timeout, "
                    "not a failure.")
                err_msg = os.linesep.join(err_msg_lines)
                raise AzureOperationTimeout(err_msg, code="Timeout")

            time.sleep(self._poll_interval)

    def _finished_resource(self) -> AzureObject:
        """
            Fetch the finished resource once the operation has succeeded.

            :returns: The resource.
        """
        if self._final_url is None:
            rtnval = self._resource
            return rtnval

        try:
            rtnval = self._client.request_absolute(method="GET",
                                                   url=self._final_url)
        except ResourceNotFoundError:
            # A successful DELETE leaves nothing to fetch.
            rtnval = self._resource
        return rtnval


class AzureArmClient:
    """
        Signed transport for Azure Resource Manager.
    """

    def __init__(self, *, subscription_id: str,
                 token_provider: AzureTokenProvider,
                 endpoint: str = ARM_ENDPOINT,
                 session: Optional[Any] = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
                 poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS
                 ) -> None:
        """
            Construct an AzureArmClient.

            :param subscription_id: The subscription every path is scoped to.
            :param token_provider: Supplies bearer tokens.
            :param endpoint: The ARM endpoint.
            :param session: Optional pre-built ``requests.Session`` — the
                test seam.
            :param timeout_seconds: The default per-request timeout.
            :param poll_interval: Seconds between long-running-operation
                status checks.
        """
        self._subscription_id: str = subscription_id
        self._token_provider: AzureTokenProvider = token_provider
        self._endpoint: str = endpoint.rstrip("/")
        self._timeout_seconds: float = timeout_seconds
        self._poll_interval: float = poll_interval

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()
        return

    @property
    def subscription_id(self) -> str:
        """
            Return the subscription id.

            :returns: The subscription id.
        """
        rtnval = self._subscription_id
        return rtnval

    @property
    def endpoint(self) -> str:
        """
            Return the ARM endpoint.

            :returns: The endpoint URL.
        """
        rtnval = self._endpoint
        return rtnval

    def subscription_path(self, *, tail: str = "") -> str:
        """
            Build a subscription-scoped path.

            :param tail: The remainder of the path, beginning with ``/``.

            :returns: The full path.
        """
        rtnval = "/subscriptions/{}{}".format(self._subscription_id, tail)
        return rtnval

    def request(self, *, method: str, path: str, api_version: str,
                params: Optional[Dict[str, Any]] = None,
                body: Optional[Dict[str, Any]] = None,
                timeout_seconds: Optional[float] = None) -> AzureObject:
        """
            Perform one ARM request against a path.

            :param method: The HTTP method.
            :param path: The ARM path, beginning with ``/``.
            :param api_version: The API version the resource type requires.
            :param params: Optional extra query parameters.
            :param body: Optional JSON request body.
            :param timeout_seconds: Optional per-request timeout override.

            :returns: The decoded response.
        """
        url = "{}{}".format(self._endpoint, path)

        query: Dict[str, Any] = {"api-version": api_version}
        if params is not None:
            for key, value in params.items():
                if value is not None:
                    query[key] = value

        rtnval = self.request_absolute(method=method, url=url, params=query,
                                       body=body,
                                       timeout_seconds=timeout_seconds)
        return rtnval

    def request_absolute(self, *, method: str, url: str,
                         params: Optional[Dict[str, Any]] = None,
                         body: Optional[Dict[str, Any]] = None,
                         timeout_seconds: Optional[float] = None
                         ) -> AzureObject:
        """
            Perform one ARM request against an absolute URL.

            Used for ``nextLink`` pagination and operation-status URLs, which
            ARM returns fully qualified and already carrying their query
            string.

            :param method: The HTTP method.
            :param url: The absolute URL.
            :param params: Optional query parameters.
            :param body: Optional JSON request body.
            :param timeout_seconds: Optional per-request timeout override.

            :returns: The decoded response.

            :raises: :class:`ResourceNotFoundError` on 404, otherwise
                :class:`AzureRequestError` on a non-success status.
        """
        response = self._send(method=method, url=url, params=params,
                              body=body, timeout_seconds=timeout_seconds)

        rtnval = self._decode(response=response, method=method, url=url)
        return rtnval

    def _send(self, *, method: str, url: str,
              params: Optional[Dict[str, Any]] = None,
              body: Optional[Dict[str, Any]] = None,
              timeout_seconds: Optional[float] = None) -> Any:
        """
            Send one authenticated request.

            :returns: The raw response.
        """
        headers: Dict[str, str] = {
            "Authorization": "Bearer {}".format(self._token_provider.token()),
            "Accept": "application/json",
        }

        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers["Content-Type"] = "application/json"

        timeout = timeout_seconds
        if timeout is None:
            timeout = self._timeout_seconds

        rtnval = self._session.request(method, url, params=params or {},
                                       data=payload, headers=headers,
                                       timeout=timeout)
        return rtnval

    def _decode(self, *, response: Any, method: str,
                url: str) -> AzureObject:
        """
            Validate and decode a response.

            :returns: The decoded body, empty when there is none.
        """
        status = getattr(response, "status_code", 0)

        if status < 200 or status >= 300:
            text = getattr(response, "text", "")
            code, message = self._error_of(response=response)

            err_msg_lines = ["The Azure Resource Manager request failed."]
            err_msg_lines.append("METHOD: {}".format(method))
            err_msg_lines.append("URL: {}".format(url))
            err_msg_lines.append("STATUS: {}".format(status))
            err_msg_lines.append("CODE: {}".format(code))
            err_msg_lines.append("MESSAGE: {}".format(message))
            err_msg = os.linesep.join(err_msg_lines)

            if status == 404:
                raise ResourceNotFoundError(err_msg, status_code=status,
                                            code=code, body=text)

            raise AzureRequestError(err_msg, status_code=status, code=code,
                                    body=text)

        text = getattr(response, "text", "")
        if text is None or len(text.strip()) == 0:
            rtnval = AzureObject()
            return rtnval

        try:
            decoded = response.json()
        except Exception:
            rtnval = AzureObject()
            return rtnval

        wrapped = wrap_azure_value(decoded)
        if isinstance(wrapped, AzureObject) is True:
            rtnval = wrapped
            return rtnval

        rtnval = AzureObject({"value": wrapped})
        return rtnval

    def _error_of(self, *, response: Any) -> Any:
        """
            Pull the ARM error code and message out of a failed response.

            ARM nests them under ``error``, which is far more useful than the
            HTTP phrase — ``ResourceGroupNotFound`` says exactly what is
            wrong.

            :returns: A ``(code, message)`` pair.
        """
        fallback = getattr(response, "reason", "")

        try:
            decoded = response.json()
        except Exception:
            rtnval = ("", fallback)
            return rtnval

        if isinstance(decoded, dict) is False:
            rtnval = ("", fallback)
            return rtnval

        error = decoded.get("error", None)
        if isinstance(error, dict) is False:
            rtnval = ("", str(decoded.get("message", fallback)))
            return rtnval

        rtnval = (str(error.get("code", "")),
                  str(error.get("message", fallback)))
        return rtnval

    def describe_error(self, *, payload: AzureObject) -> str:
        """
            Render the error carried by a failed operation-status body.

            :param payload: The operation status body.

            :returns: A human-readable description.
        """
        error = payload.get("error", None)
        if isinstance(error, dict) is True:
            rtnval = "{}: {}".format(error.get("code", ""),
                                     error.get("message", ""))
            return rtnval

        rtnval = str(payload.get("status", "unknown"))
        return rtnval

    def begin(self, *, method: str, path: str, api_version: str,
              body: Optional[Dict[str, Any]] = None,
              params: Optional[Dict[str, Any]] = None) -> LroPoller:
        """
            Start a possibly long-running mutation.

            :param method: The HTTP method.
            :param path: The ARM path.
            :param api_version: The API version.
            :param body: Optional JSON request body.
            :param params: Optional extra query parameters.

            :returns: An :class:`LroPoller`.  When ARM answered
                synchronously the poller is already done and
                :meth:`LroPoller.result` returns without waiting.
        """
        url = "{}{}".format(self._endpoint, path)

        query: Dict[str, Any] = {"api-version": api_version}
        if params is not None:
            for key, value in params.items():
                if value is not None:
                    query[key] = value

        response = self._send(method=method, url=url, params=query,
                              body=body)
        resource = self._decode(response=response, method=method, url=url)

        headers = getattr(response, "headers", None) or {}
        monitor = self._header_of(headers=headers,
                                  name="azure-asyncoperation")
        if monitor is None:
            monitor = self._header_of(headers=headers, name="location")

        final_url = None
        if method.upper() in ("PUT", "PATCH"):
            # A PUT's finished state is read back from the resource URL, not
            # from the operation monitor, which only reports status.
            final_url = "{}?api-version={}".format(url, api_version)

        rtnval = LroPoller(client=self, resource=resource,
                           monitor_url=monitor, final_url=final_url,
                           poll_interval=self._poll_interval)
        return rtnval

    def _header_of(self, *, headers: Any, name: str) -> Optional[str]:
        """
            Read a header case-insensitively.

            :param headers: The response headers.
            :param name: The lowercase header name.

            :returns: The header value, or None.
        """
        getter = getattr(headers, "get", None)
        if getter is not None:
            found = getter(name, None)
            if found is not None:
                rtnval = str(found)
                return rtnval

        for key in getattr(headers, "keys", lambda: [])():
            if str(key).lower() == name:
                rtnval = str(headers[key])
                return rtnval

        rtnval = None
        return rtnval

    def paginate(self, *, path: str, api_version: str,
                 params: Optional[Dict[str, Any]] = None
                 ) -> List[AzureObject]:
        """
            Walk every page of a collection and return the entries.

            ARM pages with a fully-qualified ``nextLink``.  A caller listing a
            collection expects all of it — a truncated listing under-reports
            owned resources, which on a teardown path means leaked
            infrastructure.

            :param path: The collection path.
            :param api_version: The API version.
            :param params: Optional extra query parameters.

            :returns: The concatenated entries.
        """
        collected: List[AzureObject] = []

        payload = self.request(method="GET", path=path,
                               api_version=api_version, params=params)

        while True:
            entries = payload.get("value", None)
            if entries is None:
                break
            collected.extend([wrap_azure_value(entry) for entry in entries])

            following = payload.get("nextLink", None)
            if following is None or len(str(following)) == 0:
                break

            payload = self.request_absolute(method="GET",
                                            url=str(following))

        rtnval = collected
        return rtnval
