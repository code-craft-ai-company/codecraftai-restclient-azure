"""
    .. module:: test_azureclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tests for the Azure Resource Manager client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import json

from typing import Any, Dict, List, Optional

from ccai import testbase

from ccai.restclient.azure.azurearmclient import AzureArmClient, LroPoller
from ccai.restclient.azure.azurearmerror import (
    AzureOperationError, AzureOperationTimeout, AzureRequestError,
    ResourceNotFoundError
)
from ccai.restclient.azure.azureobject import (
    AzureObject, normalize_name, resource_name_of
)
from ccai.restclient.azure.azuretokenprovider import (
    AzureTokenError, AzureTokenProvider
)
from ccai.restclient.azure.managementclients import build_management_clients


SUBSCRIPTION = "sub-123"


class FakeResponse:
    """
        Minimal stand-in for a ``requests.Response``.
    """

    def __init__(self, *, status_code: int = 200,
                 payload: Optional[Any] = None, text: Optional[str] = None,
                 reason: str = "OK",
                 headers: Optional[Dict[str, str]] = None) -> None:
        self.status_code = status_code
        self.reason = reason
        self.headers = headers or {}
        if text is not None:
            self.text = text
        elif payload is not None:
            self.text = json.dumps(payload)
        else:
            self.text = ""
        self._payload = payload

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


class FakeSession:
    """
        Records requests and replays queued responses.
    """

    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}
        self.calls: List[Dict[str, Any]] = []
        self.responses: Dict[str, List[FakeResponse]] = {}
        self.default_response = FakeResponse(payload={})

    def queue(self, *, method: str, match: str,
              response: FakeResponse) -> None:
        key = "{} {}".format(method.upper(), match)
        self.responses.setdefault(key, []).append(response)
        return

    def request(self, method: str, url: str, params=None, data=None,
                headers=None, timeout=None) -> FakeResponse:
        body = None
        if data is not None:
            if isinstance(data, dict) is True:
                # The OAuth2 token endpoint is form-encoded, so `data` is a
                # dict there and requests encodes it; JSON bodies arrive as
                # an already-serialised string.
                body = data
            else:
                body = json.loads(data)

        self.calls.append({"method": method, "url": url,
                           "params": params or {}, "body": body,
                           "headers": headers or {}})

        for key, queued in self.responses.items():
            wanted_method, _, wanted = key.partition(" ")
            if method.upper() == wanted_method and wanted in url:
                if len(queued) > 0:
                    rtnval = queued.pop(0)
                    return rtnval

        rtnval = self.default_response
        return rtnval


class StubTokenProvider:
    """
        A token provider that never performs I/O.
    """

    def token(self, **kwargs: Any) -> str:
        return "stub-token"


def _build_client(session=None):
    """
        Build an ARM client over a fake session.

        :returns: A ``(client, session)`` pair.
    """
    if session is None:
        session = FakeSession()
    client = AzureArmClient(subscription_id=SUBSCRIPTION,
                            token_provider=StubTokenProvider(),
                            session=session, poll_interval=0.0)
    return client, session


# ----------------------------------------------------------------------
# AzureObject
# ----------------------------------------------------------------------

def test_object_reads_top_level_fields():
    obj = AzureObject({"id": "/subs/x", "name": "vnet-a",
                       "location": "eastus"})

    assert obj.name == "vnet-a"
    assert obj.location == "eastus"
    return


def test_object_flattens_properties():
    obj = AzureObject({"name": "vnet-a",
                       "properties": {"addressSpace": {
                           "addressPrefixes": ["10.0.0.0/16"]}}})

    # The SDK's models flattened properties, so consumer code reads
    # vnet.address_space.address_prefixes.
    assert obj.address_space.address_prefixes == ["10.0.0.0/16"]
    return


def test_object_matches_acronym_suffixed_fields():
    obj = AzureObject({"properties": {"diskSizeGB": 128}})

    # A camelCase->snake_case converter would produce disk_size_g_b and never
    # match what consumer code asks for.
    assert obj.disk_size_gb == 128
    return


def test_top_level_wins_over_a_same_named_property():
    obj = AzureObject({"name": "outer",
                       "properties": {"name": "inner"}})

    # A resource's own name must never be shadowed by a property.
    assert obj.name == "outer"
    return


def test_object_reads_absent_field_as_none():
    obj = AzureObject({"name": "vnet-a"})

    assert obj.tags is None
    assert getattr(obj, "address_space", None) is None
    return


def test_object_refuses_private_lookups():
    obj = AzureObject({"name": "x"})

    with testbase.raises(AttributeError):
        getattr(obj, "_ipython_canary")
    return


def test_object_wraps_nested_lists():
    obj = AzureObject({"properties": {"securityRules": [
        {"name": "r1", "properties": {"priority": 100}}]}})

    rules = obj.security_rules
    assert rules[0].name == "r1"
    assert rules[0].priority == 100
    return


def test_normalize_name_is_spelling_insensitive():
    assert normalize_name("disk_size_gb") == normalize_name("diskSizeGB")
    assert normalize_name("address_space") == normalize_name("addressSpace")
    return


def test_resource_name_of_reads_the_trailing_segment():
    resource_id = ("/subscriptions/s/resourceGroups/rg/providers/"
                   "Microsoft.Network/virtualNetworks/vnet-a")

    assert resource_name_of(resource_id) == "vnet-a"
    assert resource_name_of(None) is None
    return


# ----------------------------------------------------------------------
# token provider
# ----------------------------------------------------------------------

def test_service_principal_exchanges_the_secret():
    session = FakeSession()
    session.queue(method="POST", match="/oauth2/v2.0/token",
                  response=FakeResponse(payload={"access_token": "tok-1",
                                                 "expires_in": 3600}))
    provider = AzureTokenProvider(tenant_id="tenant-a", client_id="app-a",
                                  client_secret="secret", session=session)

    assert provider.token(now=1000.0) == "tok-1"
    call = session.calls[0]
    assert "tenant-a" in call["url"]
    return


def test_token_is_cached_until_close_to_expiry():
    session = FakeSession()
    session.queue(method="POST", match="/oauth2/v2.0/token",
                  response=FakeResponse(payload={"access_token": "tok-1",
                                                 "expires_in": 3600}))
    provider = AzureTokenProvider(tenant_id="t", client_id="c",
                                  client_secret="s", session=session)

    provider.token(now=1000.0)
    provider.token(now=1500.0)

    assert len(session.calls) == 1
    return


def test_token_is_refreshed_early():
    session = FakeSession()
    session.queue(method="POST", match="/oauth2/v2.0/token",
                  response=FakeResponse(payload={"access_token": "tok-1",
                                                 "expires_in": 3600}))
    session.queue(method="POST", match="/oauth2/v2.0/token",
                  response=FakeResponse(payload={"access_token": "tok-2",
                                                 "expires_in": 3600}))
    provider = AzureTokenProvider(tenant_id="t", client_id="c",
                                  client_secret="s", session=session)

    provider.token(now=1000.0)
    # 3600s lifetime less the 300s skew expires the cache at 4300.
    second = provider.token(now=4400.0)

    # A token that passes the expiry check and then expires in flight fails
    # the request it was fetched for.
    assert second == "tok-2"
    assert len(session.calls) == 2
    return


def test_managed_identity_asks_the_metadata_service():
    session = FakeSession()
    session.queue(method="GET", match="169.254.169.254",
                  response=FakeResponse(payload={"access_token": "imds-tok",
                                                 "expires_in": 3600}))
    provider = AzureTokenProvider(use_managed_identity=True,
                                  session=session)

    assert provider.token(now=0.0) == "imds-tok"
    assert session.calls[0]["headers"]["Metadata"] == "true"
    return


def test_incomplete_service_principal_is_refused():
    with testbase.raises(AzureTokenError):
        AzureTokenProvider(tenant_id="t", client_id="c",
                           session=FakeSession())
    return


def test_token_failure_surfaces_the_description():
    session = FakeSession()
    session.queue(method="POST", match="/oauth2/v2.0/token",
                  response=FakeResponse(
                      status_code=401, reason="Unauthorized",
                      payload={"error": "invalid_client",
                               "error_description": "secret is expired"}))
    provider = AzureTokenProvider(tenant_id="t", client_id="c",
                                  client_secret="s", session=session)

    with testbase.raises(AzureTokenError) as caught:
        provider.token(now=0.0)

    assert "secret is expired" in str(caught.value)
    return


# ----------------------------------------------------------------------
# transport
# ----------------------------------------------------------------------

def test_request_sends_the_bearer_token_and_api_version():
    client, session = _build_client()

    client.request(method="GET", path="/subscriptions/sub-123/x",
                   api_version="2023-05-01")

    call = session.calls[0]
    assert call["headers"]["Authorization"] == "Bearer stub-token"
    assert call["params"]["api-version"] == "2023-05-01"
    return


def test_404_raises_resource_not_found():
    client, session = _build_client()
    session.queue(method="GET", match="/x",
                  response=FakeResponse(
                      status_code=404, reason="Not Found",
                      payload={"error": {"code": "ResourceGroupNotFound",
                                         "message": "no such group"}}))

    with testbase.raises(ResourceNotFoundError) as caught:
        client.request(method="GET", path="/x", api_version="2023-05-01")

    # Consumer code catches this name to mean "absent, carry on".
    assert caught.value.code == "ResourceGroupNotFound"
    assert caught.value.status_code == 404
    return


def test_other_failures_raise_the_general_error():
    client, session = _build_client()
    session.queue(method="GET", match="/x",
                  response=FakeResponse(
                      status_code=403, reason="Forbidden",
                      payload={"error": {"code": "AuthorizationFailed",
                                         "message": "denied"}}))

    with testbase.raises(AzureRequestError) as caught:
        client.request(method="GET", path="/x", api_version="2023-05-01")

    assert isinstance(caught.value, ResourceNotFoundError) is False
    assert caught.value.code == "AuthorizationFailed"
    return


def test_paginate_follows_next_link():
    client, session = _build_client()
    session.queue(method="GET", match="/things",
                  response=FakeResponse(payload={
                      "value": [{"name": "a"}],
                      "nextLink": "https://management.azure.com/page2"}))
    session.queue(method="GET", match="/page2",
                  response=FakeResponse(payload={"value": [{"name": "b"}]}))

    found = client.paginate(path="/things", api_version="2023-05-01")

    # A truncated listing under-reports owned resources, which on a teardown
    # path means leaked infrastructure.
    assert [entry.name for entry in found] == ["a", "b"]
    return


# ----------------------------------------------------------------------
# long-running operations
# ----------------------------------------------------------------------

def test_synchronous_mutation_is_not_turned_into_a_wait():
    client, session = _build_client()
    session.queue(method="PUT", match="/vnets/a",
                  response=FakeResponse(status_code=200,
                                        payload={"name": "a"}))

    poller = client.begin(method="PUT", path="/vnets/a",
                          api_version="2023-05-01", body={})

    assert poller.done() is True
    assert poller.result(5).name == "a"
    # Only the mutation itself was sent.
    assert len(session.calls) == 1
    return


def test_poller_waits_for_a_succeeded_status():
    client, session = _build_client()
    session.queue(method="PUT", match="/vnets/a",
                  response=FakeResponse(
                      status_code=201, payload={"name": "a"},
                      headers={"Azure-AsyncOperation":
                               "https://management.azure.com/op/1"}))
    session.queue(method="GET", match="/op/1",
                  response=FakeResponse(payload={"status": "InProgress"}))
    session.queue(method="GET", match="/op/1",
                  response=FakeResponse(payload={"status": "Succeeded"}))
    session.queue(method="GET", match="/vnets/a",
                  response=FakeResponse(payload={"name": "a",
                                                 "properties": {"x": 1}}))

    poller = client.begin(method="PUT", path="/vnets/a",
                          api_version="2023-05-01", body={})
    result = poller.result(60)

    assert poller.done() is False
    assert result.name == "a"
    return


def test_poller_raises_on_a_failed_operation():
    client, session = _build_client()
    session.queue(method="PUT", match="/vnets/a",
                  response=FakeResponse(
                      status_code=201, payload={"name": "a"},
                      headers={"Azure-AsyncOperation":
                               "https://management.azure.com/op/2"}))
    session.queue(method="GET", match="/op/2",
                  response=FakeResponse(payload={
                      "status": "Failed",
                      "error": {"code": "QuotaExceeded",
                                "message": "no capacity"}}))

    poller = client.begin(method="PUT", path="/vnets/a",
                          api_version="2023-05-01", body={})

    with testbase.raises(AzureOperationError) as caught:
        poller.result(60)

    assert "QuotaExceeded" in str(caught.value)
    return


def test_poller_timeout_is_distinct_from_failure():
    client, session = _build_client()
    session.queue(method="PUT", match="/vnets/a",
                  response=FakeResponse(
                      status_code=201, payload={"name": "a"},
                      headers={"Azure-AsyncOperation":
                               "https://management.azure.com/op/3"}))
    for _ in range(10):
        session.queue(method="GET", match="/op/3",
                      response=FakeResponse(payload={"status": "Running"}))

    poller = client.begin(method="PUT", path="/vnets/a",
                          api_version="2023-05-01", body={})

    with testbase.raises(AzureOperationTimeout) as caught:
        poller.result(0)

    # The operation may still be running, so this must not be reported as a
    # failure.
    assert isinstance(caught.value, AzureOperationError) is False
    return


def test_location_header_is_used_when_there_is_no_async_operation():
    client, session = _build_client()
    session.queue(method="DELETE", match="/vnets/a",
                  response=FakeResponse(
                      status_code=202, text="",
                      headers={"Location":
                               "https://management.azure.com/op/4"}))
    session.queue(method="GET", match="/op/4",
                  response=FakeResponse(payload={"status": "Succeeded"}))

    poller = client.begin(method="DELETE", path="/vnets/a",
                          api_version="2023-05-01")
    poller.result(60)

    assert poller.done() is False
    return


# ----------------------------------------------------------------------
# collection paths
# ----------------------------------------------------------------------

def _clients():
    client, session = _build_client()
    return build_management_clients(arm_client=client), session


def test_virtual_network_path():
    clients, session = _clients()

    clients["network"].virtual_networks.list("rg-a")

    assert session.calls[0]["url"].endswith(
        "/subscriptions/sub-123/resourceGroups/rg-a/providers/"
        "Microsoft.Network/virtualNetworks")
    return


def test_subnet_path_is_nested_under_its_network():
    clients, session = _clients()

    clients["network"].subnets.begin_create_or_update(
        resource_group_name="rg-a", virtual_network_name="vnet-a",
        subnet_name="sub-a", subnet_parameters={"properties": {}})

    assert session.calls[0]["url"].endswith(
        "Microsoft.Network/virtualNetworks/vnet-a/subnets/sub-a")
    return


def test_extension_path_is_nested_under_its_machine():
    clients, session = _clients()

    clients["compute"].virtual_machine_extensions.begin_create_or_update(
        resource_group_name="rg-a", vm_name="vm-a",
        vm_extension_name="ext-a", extension_parameters={})

    assert session.calls[0]["url"].endswith(
        "Microsoft.Compute/virtualMachines/vm-a/extensions/ext-a")
    return


def test_record_set_path_carries_the_record_type():
    clients, session = _clients()

    clients["dns"].record_sets.create_or_update(
        resource_group_name="rg-a", zone_name="example.com",
        relative_record_set_name="srv-a", record_type="A",
        parameters={"properties": {}})

    # The record type is part of the path, not the body.
    assert session.calls[0]["url"].endswith(
        "Microsoft.Network/dnsZones/example.com/A/srv-a")
    return


def test_resource_group_path_is_subscription_scoped():
    clients, session = _clients()

    clients["resource"].resource_groups.create_or_update(
        resource_group_name="rg-a", parameters={"location": "eastus"})

    assert session.calls[0]["url"].endswith(
        "/subscriptions/sub-123/resourcegroups/rg-a")
    return


def test_disk_body_keyword_is_disk():
    clients, session = _clients()

    clients["compute"].disks.begin_create_or_update(
        resource_group_name="rg-a", disk_name="disk-a",
        disk={"location": "eastus"})

    assert session.calls[0]["body"] == {"location": "eastus"}
    return


def test_storage_account_create_is_long_running():
    clients, session = _clients()
    session.queue(method="PUT", match="storageAccounts/acct",
                  response=FakeResponse(
                      status_code=202, payload={"name": "acct"},
                      headers={"Azure-AsyncOperation":
                               "https://management.azure.com/op/9"}))
    session.queue(method="GET", match="/op/9",
                  response=FakeResponse(payload={"status": "Succeeded"}))
    session.queue(method="GET", match="storageAccounts/acct",
                  response=FakeResponse(payload={"name": "acct"}))

    poller = clients["storage"].storage_accounts.begin_create(
        resource_group_name="rg-a", account_name="acct", parameters={})

    assert poller.result(60).name == "acct"
    return


def test_all_five_management_clients_share_one_transport():
    clients, session = _clients()

    transports = {id(entry.arm_client) for entry in clients.values()}

    # ARM is a single API; the SDK's split into packages is packaging, not
    # protocol.
    assert len(transports) == 1
    return
