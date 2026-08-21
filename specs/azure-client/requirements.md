# Requirements

## Introduction

The `azure-client` feature provides a pure-Python client for Azure Resource
Manager, without depending on the `azure-mgmt-*` or `azure-core` SDK
packages. ARM is a single uniform REST protocol — every resource is addressed
by a path under
`/subscriptions/{id}/resourceGroups/{name}/providers/{provider}/{type}`, every
call carries an `api-version`, collections page through `nextLink`, and
mutations may be long-running — so the package is factored as one signed
transport (`AzureArmClient`) plus a thin collection layer that declares only
what differs per resource type.

The package preserves the SDK's *consumer-visible shapes* rather than
redesigning them. Management clients mirror the `azure-mgmt-*` entry points so
`network_client.virtual_networks.list(...)` keeps working; responses are
`AzureObject` instances that flatten `properties` the way the SDK models did
so `vnet.address_space.address_prefixes` keeps working; and
`ResourceNotFoundError` keeps the `azure-core` spelling because consumer code
catches that name to mean "absent, carry on".

Token acquisition is owned here (`azuretokenprovider`) and supports both a
service principal and a managed identity. This package is consumed by
`codecraftai-provisioning/venues/azure/` through `AzureSessionFactory`, which
is where an `AzureServicePrincipalCredential` or
`AzureManagedIdentityCredential` is unwrapped into the arguments this
package's token provider accepts.

---

## Requirements

### Requirement 1: Acquire ARM Access Tokens From Two Credential Kinds

**User Story:** As a venue provisioner, I want bearer tokens obtained for
either a service principal or a managed identity so that the same client works
from a workstation and from inside Azure.

#### Acceptance Criteria

1. WHEN `AzureTokenProvider` is constructed with `use_managed_identity=False`
   THE SYSTEM SHALL require a tenant id, client id, and client secret, and
   SHALL raise `AzureTokenError` naming every missing field when any is
   absent.
2. WHEN a service-principal token is needed THE SYSTEM SHALL POST the
   `client_credentials` grant to
   `<login_host>/<tenant_id>/oauth2/v2.0/token` requesting the
   `https://management.azure.com/.default` scope.
3. WHEN `use_managed_identity=True` THE SYSTEM SHALL GET the instance metadata
   token URL carrying the `Metadata: true` header, and SHALL include
   `client_id` only when one was supplied, so that a user-assigned identity
   can be selected.
4. WHEN a token request fails THE SYSTEM SHALL raise `AzureTokenError`
   carrying the status, the raw body, and the response's
   `error_description` when present.
5. WHEN a token response carries no `access_token`, is not JSON, or is not an
   object THE SYSTEM SHALL raise `AzureTokenError`.

### Requirement 2: Cache Tokens With an Early Refresh

**User Story:** As a caller mid-apply, I want tokens refreshed before they
expire so that a request never fails on a token that expired in flight.

#### Acceptance Criteria

1. WHEN a cached token has not reached its adjusted expiry THE SYSTEM SHALL
   return it without issuing a token request.
2. THE SYSTEM SHALL treat a token as expiring 300 seconds before its stated
   `expires_in`, so that it cannot expire between the check and the call it
   authenticates.
3. WHEN the stated lifetime is shorter than the skew THE SYSTEM SHALL use half
   the lifetime instead, so that a short-lived token is still usable rather
   than instantly stale.
4. WHEN `expires_in` is absent or not numeric THE SYSTEM SHALL assume 3600
   seconds.
5. THE SYSTEM SHALL accept a `now` override on `token()` so that expiry
   behaviour is testable without waiting.

### Requirement 3: Perform Signed ARM Requests

**User Story:** As a caller, I want ARM requests issued with the bearer token
and the resource type's `api-version` so that I never assemble either by hand.

#### Acceptance Criteria

1. WHEN `request(method, path, api_version, ...)` is invoked THE SYSTEM SHALL
   compose the URL from the ARM endpoint and path, set `api-version` as a
   query parameter, and send `Authorization: Bearer <token>` with
   `Accept: application/json`.
2. WHEN a body is supplied THE SYSTEM SHALL serialise it as JSON and set
   `Content-Type: application/json`.
3. WHEN extra `params` are supplied THE SYSTEM SHALL include only those whose
   value is not `None`.
4. THE SYSTEM SHALL expose `request_absolute(method, url, ...)` for URLs ARM
   returns fully qualified and already carrying their query string —
   `nextLink` and operation-status URLs.
5. THE SYSTEM SHALL expose `subscription_path(tail)` composing
   `/subscriptions/{id}{tail}`.
6. THE SYSTEM SHALL apply a default 60-second per-request timeout and accept a
   per-request override.

### Requirement 4: Classify ARM Failures

**User Story:** As a consumer, I want a 404 distinguishable from every other
failure so that "not created yet" can be recovered while a real fault is not.

#### Acceptance Criteria

1. WHEN a response status is outside `200..299` THE SYSTEM SHALL read the ARM
   error code and message from the body's nested `error` object.
2. WHEN the status is 404 THE SYSTEM SHALL raise `ResourceNotFoundError`;
   otherwise THE SYSTEM SHALL raise `AzureRequestError`.
3. THE SYSTEM SHALL carry `status_code`, `code`, and the raw `body` on the
   exception, and SHALL include method, URL, status, code, and message in its
   text.
4. WHEN the failed body is not JSON, or carries no `error` object, THE SYSTEM
   SHALL fall back to the HTTP reason phrase rather than raising while
   raising.
5. WHEN a successful response has an empty or non-JSON body THE SYSTEM SHALL
   return an empty `AzureObject` rather than failing.

### Requirement 5: Present ARM JSON as the SDK Presented It

**User Story:** As a consumer, I want resource fields readable by the
attribute names the SDK exposed so that existing code reads a resource
unchanged.

#### Acceptance Criteria

1. THE SYSTEM SHALL return decoded resources as `AzureObject`, a `dict`
   subclass that is also attribute addressable.
2. WHEN an attribute is looked up THE SYSTEM SHALL resolve in order: the
   literal key, a spelling-insensitive match at the top level, the literal key
   inside `properties`, then a spelling-insensitive match inside `properties`.
3. THE SYSTEM SHALL normalise names by removing underscores and lowercasing
   both sides, so that `disk_size_gb`, `diskSizeGB`, and `DiskSizeGb` all
   match — a camelCase-to-snake_case converter would yield `disk_size_g_b`
   and never match what consumer code asks for.
4. THE SYSTEM SHALL resolve a top-level field in preference to a same-named
   entry under `properties`, so that a resource's own `id`, `name`, and
   `location` are never shadowed.
5. WHEN a field is absent THE SYSTEM SHALL return `None`, so that
   SDK-era `getattr(obj, "field", None)` guards behave the same way.
6. WHEN an attribute name begins with `_` THE SYSTEM SHALL raise
   `AttributeError`, so that copy, pickle, and inspect machinery does not see
   phantom attributes.
7. THE SYSTEM SHALL wrap nested dicts and lists on access, and SHALL expose
   `as_dict()` returning the plain wire-shaped dictionary.
8. THE SYSTEM SHALL provide `resource_name_of(resource_id)` returning the
   trailing segment of a fully-qualified ARM resource id.

### Requirement 6: Page Collections Exhaustively

**User Story:** As a caller listing a collection, I want every page, because a
truncated listing under-reports owned resources — which on a teardown path
means leaked infrastructure.

#### Acceptance Criteria

1. WHEN `paginate(path, api_version, params)` is invoked THE SYSTEM SHALL GET
   the collection, extend the result with the `value` entries, and follow
   `nextLink` until it is absent or empty.
2. THE SYSTEM SHALL request each `nextLink` as an absolute URL without
   re-appending `api-version`.
3. THE SYSTEM SHALL wrap every entry as an `AzureObject`.
4. WHEN a page carries no `value` key THE SYSTEM SHALL stop rather than loop.

### Requirement 7: Drive Long-Running Operations

**User Story:** As a provisioner, I want mutations to return a poller I can
wait on so that the lifecycle pipeline can treat sync and async ARM responses
alike.

#### Acceptance Criteria

1. WHEN `begin(method, path, api_version, ...)` is invoked THE SYSTEM SHALL
   issue the mutation and return an `LroPoller`.
2. THE SYSTEM SHALL read the monitor URL from the `Azure-AsyncOperation`
   header, falling back to `Location`, matched case-insensitively.
3. WHEN ARM answers synchronously — no operation header — THE SYSTEM SHALL
   return a poller whose `done()` is true and whose `result()` returns the
   resource immediately without waiting.
4. WHEN the method is `PUT` or `PATCH` THE SYSTEM SHALL record the resource
   URL as the final URL, because the operation monitor reports status only and
   the finished state must be read back from the resource itself.
5. WHEN `result()` polls and the status reaches `succeeded` THE SYSTEM SHALL
   GET the final URL and return that resource, tolerating a
   `ResourceNotFoundError` — a successful DELETE leaves nothing to fetch.
6. WHEN the status reaches `failed`, `canceled`, or `cancelled` THE SYSTEM
   SHALL raise `AzureOperationError` carrying the rendered error detail.
7. WHEN the caller's timeout elapses THE SYSTEM SHALL raise
   `AzureOperationTimeout`, which is distinct from `AzureOperationError`
   because the operation may still be running.
8. WHEN a monitor response carries no `status` field THE SYSTEM SHALL treat
   the payload as the finished resource, which is how a `Location`-header
   monitor answers once ready.
9. THE SYSTEM SHALL poll every 5 seconds and default the operation budget to
   1800 seconds, both overridable.

### Requirement 8: Address Every Resource Type Through One Collection Shape

**User Story:** As a maintainer, I want path building and CRUD to be written
once so that adding a resource type is a declaration rather than an
implementation.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `ArmCollection` deriving its paths from
   `PROVIDER`, `RESOURCE_TYPE`, and `API_VERSION` class attributes.
2. THE SYSTEM SHALL compose the collection path as
   `/subscriptions/{id}/resourceGroups/{group}/providers/{provider}/{type}`
   and the item path by appending the resource name.
3. THE SYSTEM SHALL implement `_list` via `paginate`, `_get` via `request`,
   and `_put` / `_delete` via `begin`.
4. WHEN a resource is nested — a subnet under a virtual network, an extension
   under a virtual machine, a record set under a DNS zone — THE SYSTEM SHALL
   compose the child path from the parent's item path.
5. THE SYSTEM SHALL discriminate DNS record sets by record type in the path
   rather than in the body.

### Requirement 9: Expose the SDK's Management-Client Surface

**User Story:** As a consumer, I want the operation groups under the client
names the SDK used so that call sites do not change.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `ResourceManagementClient` (`resource_groups`),
   `NetworkManagementClient` (`virtual_networks`, `subnets`,
   `network_interfaces`, `network_security_groups`, `public_ip_addresses`),
   `ComputeManagementClient` (`virtual_machines`,
   `virtual_machine_extensions`, `disks`, `proximity_placement_groups`),
   `StorageManagementClient` (`storage_accounts`), and `DnsManagementClient`
   (`record_sets`).
2. THE SYSTEM SHALL have all five share ONE `AzureArmClient` transport,
   because ARM is a single API and the SDK's split into packages is packaging
   rather than protocol.
3. THE SYSTEM SHALL expose `build_management_clients(arm_client)` returning a
   dict keyed `resource`, `network`, `compute`, `storage`, `dns`.
4. THE SYSTEM SHALL match the SDK's per-collection keyword spellings even
   where they are inconsistent — `disk=` rather than `parameters=` on
   `DisksCollection.begin_create_or_update`, `get_properties` rather than
   `get` on `StorageAccountsCollection` — and SHALL accept the resource group
   positionally on `list` operations, which the SDK commonly is called with.
5. THE SYSTEM SHALL pin each collection to the api-version its provider
   requires, which differs per type.

### Requirement 10: Remain Injectable and SDK-Free

**User Story:** As a test author, I want to drive the whole client without an
Azure subscription and without patching module globals.

#### Acceptance Criteria

1. THE SYSTEM SHALL accept a pre-built `session` object on both
   `AzureArmClient` and `AzureTokenProvider` as the sole transport seam.
2. THE SYSTEM SHALL accept `endpoint`, `login_host`, and `imds_url` overrides
   so that no request escapes to a real Azure host in tests.
3. THE SYSTEM SHALL NOT import `azure-mgmt-*`, `azure-core`, or `azure-identity`
   at any point.
