# Design

## Overview

Azure Resource Manager is one protocol, not many. Every resource type is
addressed the same way, carries an `api-version`, pages the same way, and may
answer a mutation asynchronously. The design follows that shape: all of the
protocol lives in `AzureArmClient`, and each resource type contributes only a
provider namespace, a type segment, an api-version, and the keyword spellings
its consumers already use.

The package does not subclass `RestClientBase`. What it preserves instead is
the `azure-mgmt-*` consumer contract — client names, operation-group
attribute names, `LROPoller.result()`, `ResourceNotFoundError`, and the
flattened attribute view of a resource — because the packages this replaces
were removed from the dependency tree while their call sites in
`codecraftai-provisioning` stayed.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  codecraftai-provisioning / venues / azure                 │
│  AzureSessionFactory                                       │
│  (unwraps AzureServicePrincipalCredential /                │
│            AzureManagedIdentityCredential)                 │
└──────────────────────────┬─────────────────────────────────┘
                           │ build_management_clients(arm_client=...)
                           ▼
┌────────────────────────────────────────────────────────────┐
│  Resource / Network / Compute / Storage / Dns              │
│  ManagementClient                                          │
│      └── operation groups  (ArmCollection subclasses)      │
│            PROVIDER · RESOURCE_TYPE · API_VERSION          │
└──────────────────────────┬─────────────────────────────────┘
                           │ request / paginate / begin
                           ▼
┌────────────────────────────────────────────────────────────┐
│  AzureArmClient          ── AzureTokenProvider (bearer)    │
│    request / request_absolute / paginate / begin           │
│    LroPoller             ── requests.Session (injectable)  │
│    decode -> AzureObject                                   │
└──────────────────────────┬─────────────────────────────────┘
                           ▼
           https://management.azure.com  ·  login.microsoftonline.com
                                         ·  169.254.169.254 (IMDS)
```

---

## Module Layout

```
source/packages/ccai/restclient/azure/
├── __init__.py
├── azuretokenprovider.py   # AzureTokenProvider, AzureTokenError
├── azurearmclient.py       # AzureArmClient, LroPoller
├── azureobject.py          # AzureObject, wrap_azure_value, normalize_name,
│                           #   resource_name_of
├── azurearmerror.py        # AzureRequestError, ResourceNotFoundError,
│                           #   AzureOperationError, AzureOperationTimeout
├── managementclients.py     # the five *ManagementClient entry points
└── apigroups/
    ├── armcollection.py      # ArmCollection
    ├── computecollections.py # VirtualMachines, VirtualMachineExtensions,
    │                         #   Disks, ProximityPlacementGroups,
    │                         #   StorageAccounts, BlobContainers,
    │                         #   ResourceGroups
    └── networkcollections.py # VirtualNetworks, Subnets, NetworkInterfaces,
                              #   NetworkSecurityGroups, PublicIpAddresses,
                              #   RecordSets
```

---

## Notable Choices

**Name matching normalises rather than converts.** `AzureObject` compares
field names by removing underscores and lowercasing on *both* sides instead of
translating camelCase to snake_case. ARM has acronym-suffixed fields such as
`diskSizeGB`, and a naive converter produces `disk_size_g_b` — which would
never match the `disk_size_gb` the SDK exposed and consumer code asks for. The
same normalisation is what lets one lookup serve both spellings.

**`properties` is flattened, but the top level wins.** Most of a resource's
interesting state is nested under `properties`, so lookup falls through to it.
Resolution checks the top level first so that a resource's own `id`, `name`,
and `location` are never shadowed by a same-named property.

**A missing field reads as `None`, but a private name raises.** Returning
`None` keeps SDK-era `getattr(obj, "field", None)` guards working. Dunder and
private lookups must still raise `AttributeError` or copy, pickle, and inspect
machinery would see phantom attributes on every object.

**Synchronous mutations are not turned into waits.** ARM frequently answers a
mutation with `200`/`201`, the resource, and no operation headers. `LroPoller`
treats a missing monitor URL as already done, so `result()` returns
immediately. Polling that case would add latency to the common path.

**A `PUT`'s result comes from the resource, not the monitor.** The operation
monitor reports status only, so `begin` records the resource URL as the final
URL for `PUT` and `PATCH` and re-reads it once the status succeeds. A
successful `DELETE` has nothing left to fetch, so a `ResourceNotFoundError`
during that read is tolerated rather than propagated.

**Timeout is not failure.** `AzureOperationTimeout` is a distinct exception
from `AzureOperationError`: when the budget elapses the caller stopped waiting
but ARM did not stop working, and reporting that as a failed operation would
be wrong. The message says so explicitly.

**Pagination is exhaustive by default.** `paginate` follows `nextLink` to the
end rather than exposing a page iterator. A caller listing a collection wants
all of it; a truncated listing under-reports owned resources, which on a
teardown path means leaked infrastructure.

**Collections declare, they do not implement.** `ArmCollection` owns path
building and the four CRUD shapes. A concrete collection sets three class
attributes and spells out its methods only because the SDK's keyword names are
inconsistent across collections — `disk=` on disks but `parameters=` on
networks, `get_properties` on storage accounts but `get` elsewhere — and those
spellings are the compatibility contract. `ResourceGroupsCollection` is
deliberately not an `ArmCollection`: resource groups are subscription-scoped
and have no provider or type segment, so it builds its own path.

---

## See Also

- `codecraftai-credentials` — `ccai.credentials.azureserviceprincipalcredential`
  and `ccai.credentials.azuremanagedidentitycredential`, the credential types
  the consumer unwraps.
- `codecraftai-provisioning/venues/azure/azuresessionfactory.py` — the consumer
  that builds the token provider and the management clients.
- `codecraftai-provisioning/venues/azure/azureidempotency.py` — the consumer
  that catches `ResourceNotFoundError` to mean "absent".

---

## Testing Strategy

Tests live in
`source/testroots/testbase/ccai/tests/restclient/azure/test_azureclient.py`
and run through the testbase runner, not pytest. A `FakeSession` recording
requests and replaying queued `FakeResponse` objects is injected on the
`session=` seam, and a `StubTokenProvider` stands in where a real token
exchange is not the subject.

Coverage is grouped by concern: the `AzureObject` view (top-level fields,
`properties` flattening, acronym-suffixed matching, shadowing, absent fields,
private lookups, nested lists); token acquisition (both credential kinds,
caching, early refresh, incomplete credentials, error descriptions); the
transport (bearer token and `api-version` on the wire, 404 versus general
failure, `nextLink` traversal); long-running operations (synchronous
completion, successful polling, failure, timeout-distinct-from-failure,
`Location`-header fallback); and path composition for each nesting shape
(virtual network, subnet under network, extension under machine, record set
with its type, subscription-scoped resource group), plus the SDK keyword
quirks and the shared-transport invariant.

No Azure subscription is required for any test in the suite.
