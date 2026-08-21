# Implementation Plan — Azure Client

## Package Skeleton

- [x] 1. Create `source/packages/ccai/restclient/azure/` with the token provider, ARM client, object model, errors, and management clients, plus an `apigroups/` subpackage.

## Token Acquisition

- [x] 2. Implement `AzureTokenProvider` accepting service-principal material or `use_managed_identity`, validating the former at construction and naming every missing field.
- [x] 3. Implement the `client_credentials` exchange against `<login_host>/<tenant>/oauth2/v2.0/token` with the `.default` scope.
- [x] 4. Implement the IMDS path carrying `Metadata: true`, including `client_id` only for a user-assigned identity.
- [x] 5. Implement token caching with a 300-second early-refresh skew, halving the lifetime when it is shorter than the skew.
- [x] 6. Implement `AzureTokenError` and token-response validation for non-success status, non-JSON bodies, and a missing `access_token`.

## ARM Transport

- [x] 7. Implement `AzureArmClient` holding subscription id, token provider, endpoint, timeout, and poll interval, with an injectable `session`.
- [x] 8. Implement `subscription_path`, `request`, and `request_absolute`, dropping `None`-valued query parameters.
- [x] 9. Decode responses into `AzureObject`, tolerating empty and non-JSON success bodies.
- [x] 10. Classify failures: 404 to `ResourceNotFoundError`, everything else to `AzureRequestError`, reading code and message from the nested `error` object.
- [x] 11. Implement `paginate` following `nextLink` to exhaustion and wrapping every entry.

## Long-Running Operations

- [x] 12. Implement `begin` reading the monitor URL from `Azure-AsyncOperation` then `Location`, case-insensitively, and recording the resource URL as the final URL for `PUT` / `PATCH`.
- [x] 13. Implement `LroPoller.done` / `LroPoller.result` with terminal-state tables, the status-less `Location` monitor case, and a poll interval.
- [x] 14. Tolerate `ResourceNotFoundError` when reading back a finished resource, for the successful-DELETE case.
- [x] 15. Implement `AzureOperationError` and `AzureOperationTimeout` as distinct exceptions, the timeout message stating the operation may still be running.

## Object Model

- [x] 16. Implement `AzureObject` as an attribute-addressable `dict` with `properties` flattening and top-level precedence.
- [x] 17. Implement `normalize_name` by underscore removal and lowercasing, so acronym-suffixed fields such as `diskSizeGB` match.
- [x] 18. Return `None` for absent fields; raise `AttributeError` for private and dunder lookups.
- [x] 19. Implement `wrap_azure_value`, `as_dict`, and `resource_name_of`.

## Collections and Management Clients

- [x] 20. Implement `ArmCollection` with `_group_path`, `_item_path`, `_list`, `_get`, `_put`, `_delete`.
- [x] 21. Implement the network collections: virtual networks, subnets, network interfaces, network security groups, public IP addresses, DNS record sets.
- [x] 22. Implement the compute collections: virtual machines, VM extensions, disks, proximity placement groups.
- [x] 23. Implement the storage-account collection and the standalone resource-group collection, the latter because resource groups are subscription-scoped.
- [x] 24. Compose nested paths from the parent item path for subnets, extensions, and record sets, with the DNS record type in the path.
- [x] 25. Preserve the SDK's per-collection keyword spellings and accept the resource group positionally on `list`.
- [x] 26. Implement the five `*ManagementClient` entry points over one shared transport, plus `build_management_clients`.

## Tests

- [x] 27. Implement `FakeSession`, `FakeResponse`, `StubTokenProvider` and drive everything through the `session=` seam.
- [x] 28. `AzureObject` tests: top-level fields, `properties` flattening, acronym-suffixed matching, shadowing precedence, absent fields, private lookups, nested lists, `resource_name_of`.
- [x] 29. Token tests: both credential kinds, caching, early refresh, incomplete service principal, error-description surfacing.
- [x] 30. Transport tests: bearer token and `api-version` on the wire, 404 versus general failure, `nextLink` traversal.
- [x] 31. LRO tests: synchronous mutation not turned into a wait, successful poll, failed operation, timeout distinct from failure, `Location` fallback.
- [x] 32. Path tests per nesting shape, the `disk=` keyword, the long-running storage-account create, and the shared-transport invariant.
- [x] 33. Migrate the suite from pytest to testbase (`testbase.raises`, `testbase.parametrize`).

## Open Items

- [ ] 34. No method accepts an `aspects` parameter, which the repository coding standard requires of every behaviour-bearing method. Retry, backoff, and poll policy are not caller-controlled beyond constructor arguments.
- [ ] 35. `AzureTokenProvider` accepts a raw `client_secret` and tenant/client ids rather than a typed credential from `codecraftai-credentials`. Unwrapping happens one layer up in `AzureSessionFactory`, leaving raw secret material on this package's public surface.
- [ ] 36. No retry or throttling handling. ARM answers `429` with a `Retry-After` header that nothing here reads, so a throttled call fails as a plain `AzureRequestError`.
- [ ] 37. `LroPoller.result` blocks in `time.sleep` and cannot be cancelled or observed while waiting. It does not use `codecraftai-waiting`, the fleet's wait abstraction.
- [ ] 38. No property-based tests. `ccai.testbase.properties` is available; `normalize_name` collision behaviour and `paginate` traversal totality are the natural candidates, since a dropped page is silent and reads as "fewer resources exist".
- [ ] 39. Api-versions are pinned as literals spread across the collection modules. There is no single place to review or bump them, and no test asserts a collection's version matches what its provider accepts.
- [ ] 40. No live-API smoke tier. Every test runs against `FakeSession`.
