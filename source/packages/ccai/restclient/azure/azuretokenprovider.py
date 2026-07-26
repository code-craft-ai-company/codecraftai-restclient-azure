"""
    .. module:: azuretokenprovider
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Access-token acquisition for Azure Resource Manager.

    Two credential kinds are supported, and neither needs any cryptography:

    * a service principal, exchanging a client id and secret for a token at
      the tenant's OAuth2 endpoint (the client-credentials grant);
    * a managed identity, asking the instance metadata service for a token
      that the platform issues to the machine itself.

    Tokens are cached until shortly before they expire.  The early refresh
    matters: a token that passes the expiry check and then expires in flight
    fails the request it was fetched for, and that failure lands mid-apply.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os
import time

from typing import Any, Dict, Optional

import requests


AZURE_LOGIN_HOST = "https://login.microsoftonline.com"

ARM_RESOURCE = "https://management.azure.com"

ARM_SCOPE = "https://management.azure.com/.default"

# The instance metadata service is a link-local address that only answers to
# requests carrying the Metadata header.
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01"
)

DEFAULT_TIMEOUT_SECONDS = 30.0

# Refresh this far ahead of the stated expiry, so a token cannot expire
# between the check and the call it authenticates.
EXPIRY_SKEW_SECONDS = 300.0


class AzureTokenError(Exception):
    """
        Raised when an access token cannot be obtained.
    """

    def __init__(self, message: str, *, status: int = 0,
                 body: Optional[str] = None) -> None:
        """
            Construct an AzureTokenError.

            :param message: The human-readable error message.
            :param status: The HTTP status code, when there was one.
            :param body: The raw response body.
        """
        super().__init__(message)
        self.status: int = status
        self.body: Optional[str] = body
        return


class AzureTokenProvider:
    """
        Acquires and caches ARM access tokens.

        :ivar tenant_id: The directory tenant, for a service principal.
    """

    def __init__(self, *, tenant_id: Optional[str] = None,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 use_managed_identity: bool = False,
                 scope: str = ARM_SCOPE,
                 login_host: str = AZURE_LOGIN_HOST,
                 imds_url: str = IMDS_TOKEN_URL,
                 session: Optional[Any] = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """
            Construct an AzureTokenProvider.

            :param tenant_id: The directory tenant id (service principal).
            :param client_id: The application (client) id.  For a managed
                identity this optionally selects a user-assigned identity.
            :param client_secret: The client secret (service principal).
            :param use_managed_identity: Ask the instance metadata service
                instead of exchanging a secret.
            :param scope: The OAuth2 scope to request.
            :param login_host: The login endpoint host.
            :param imds_url: The instance metadata token URL.
            :param session: Optional pre-built ``requests.Session`` — the
                test seam.
            :param timeout_seconds: The per-request timeout.

            :raises: :class:`AzureTokenError` when the supplied material
                cannot identify a caller.
        """
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._use_managed_identity = use_managed_identity
        self._scope = scope
        self._login_host = login_host.rstrip("/")
        self._imds_url = imds_url
        self._timeout_seconds = timeout_seconds

        self._token: Optional[str] = None
        self._expires_at: float = 0.0

        if use_managed_identity is False:
            missing = []
            if tenant_id is None or len(tenant_id) == 0:
                missing.append("tenant_id")
            if client_id is None or len(client_id) == 0:
                missing.append("client_id")
            if client_secret is None or len(client_secret) == 0:
                missing.append("client_secret")
            if len(missing) > 0:
                err_msg_lines = [
                    "A service-principal token needs the full credential."
                ]
                err_msg_lines.append("MISSING: {}".format(", ".join(missing)))
                err_msg_lines.append(
                    "Pass use_managed_identity=True to use the instance "
                    "metadata service instead.")
                err_msg = os.linesep.join(err_msg_lines)
                raise AzureTokenError(err_msg)

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()
        return

    @property
    def tenant_id(self) -> Optional[str]:
        """
            Return the directory tenant id.

            :returns: The tenant id, or None for a managed identity.
        """
        rtnval = self._tenant_id
        return rtnval

    def token(self, *, now: Optional[float] = None) -> str:
        """
            Return a valid access token, fetching one when needed.

            :param now: Optional current time, for tests.

            :returns: The bearer token.
        """
        moment = now
        if moment is None:
            moment = time.time()

        if self._token is not None and moment < self._expires_at:
            rtnval = self._token
            return rtnval

        if self._use_managed_identity is True:
            payload = self._fetch_managed_identity_token()
        else:
            payload = self._fetch_client_credentials_token()

        token = payload.get("access_token", None)
        if token is None or len(str(token)) == 0:
            err_msg = "The token response carried no access_token."
            raise AzureTokenError(err_msg)

        expires_in = payload.get("expires_in", 3600)
        try:
            lifetime = float(expires_in)
        except (TypeError, ValueError):
            lifetime = 3600.0

        # Never let the skew push the expiry into the past; a very short
        # lifetime should still be usable rather than instantly stale.
        usable = lifetime - EXPIRY_SKEW_SECONDS
        if usable <= 0:
            usable = lifetime / 2.0

        self._token = str(token)
        self._expires_at = moment + usable

        rtnval = self._token
        return rtnval

    def _fetch_client_credentials_token(self) -> Dict[str, Any]:
        """
            Exchange the client secret for a token.

            :returns: The decoded token response.

            :raises: :class:`AzureTokenError` on a non-success status.
        """
        url = "{}/{}/oauth2/v2.0/token".format(self._login_host,
                                               self._tenant_id)
        form = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": self._scope,
        }

        response = self._session.request(
            "POST", url, data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._timeout_seconds)

        rtnval = self._decode_token_response(response=response,
                                             what="service principal")
        return rtnval

    def _fetch_managed_identity_token(self) -> Dict[str, Any]:
        """
            Ask the instance metadata service for a token.

            :returns: The decoded token response.

            :raises: :class:`AzureTokenError` on a non-success status.
        """
        params: Dict[str, Any] = {"resource": ARM_RESOURCE}
        if self._client_id is not None and len(self._client_id) > 0:
            params["client_id"] = self._client_id

        response = self._session.request(
            "GET", self._imds_url, params=params,
            headers={"Metadata": "true"}, timeout=self._timeout_seconds)

        rtnval = self._decode_token_response(response=response,
                                             what="managed identity")
        return rtnval

    def _decode_token_response(self, *, response: Any,
                               what: str) -> Dict[str, Any]:
        """
            Validate and decode a token response.

            :param response: The HTTP response.
            :param what: Which credential kind was used, for the message.

            :returns: The decoded body.

            :raises: :class:`AzureTokenError` on failure.
        """
        status = getattr(response, "status_code", 0)
        text = getattr(response, "text", "")

        if status < 200 or status >= 300:
            description = text
            try:
                decoded = response.json()
                if isinstance(decoded, dict) is True:
                    described = decoded.get("error_description", None)
                    if described is not None:
                        description = str(described)
            except Exception:
                description = text

            err_msg_lines = [
                "Could not obtain an Azure access token ({}).".format(what)
            ]
            err_msg_lines.append("STATUS: {}".format(status))
            err_msg_lines.append("DETAIL: {}".format(description))
            err_msg = os.linesep.join(err_msg_lines)
            raise AzureTokenError(err_msg, status=status, body=text)

        try:
            decoded = response.json()
        except Exception:
            err_msg = "The Azure token response was not JSON."
            raise AzureTokenError(err_msg, status=status, body=text) from None

        if isinstance(decoded, dict) is False:
            err_msg = "The Azure token response was not an object."
            raise AzureTokenError(err_msg, status=status, body=text)

        rtnval = decoded
        return rtnval
