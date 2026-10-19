=============================
codecraftai-restclient-azure
=============================

A pure-Python client for `Azure Resource Manager
<https://learn.microsoft.com/en-us/rest/api/resources/>`_, replacing the
``azure-identity`` and ``azure-mgmt-*`` SDKs.

ARM is one uniform REST protocol: every resource is addressed by a path under
``/subscriptions/{id}/resourceGroups/{name}/providers/...``, every call carries
an ``api-version``, collections page through ``nextLink``, and mutations may be
long-running.  One transport therefore serves all five management clients — the
SDK's split into separate packages is packaging, not protocol.

Usage
=====

.. code-block:: python

    from ccai.restclient.azure.azurearmclient import AzureArmClient
    from ccai.restclient.azure.azuretokenprovider import AzureTokenProvider
    from ccai.restclient.azure.managementclients import (
        build_management_clients
    )

    tokens = AzureTokenProvider(tenant_id=tenant, client_id=client,
                                client_secret=secret)
    arm = AzureArmClient(subscription_id=subscription, token_provider=tokens)
    clients = build_management_clients(arm_client=arm)

    poller = clients["network"].virtual_networks.begin_create_or_update(
        resource_group_name="rg-a", virtual_network_name="vnet-a",
        parameters={"location": "eastus",
                    "properties": {"addressSpace": {
                        "addressPrefixes": ["10.0.0.0/16"]}}})
    vnet = poller.result(600)

    print(vnet.address_space.address_prefixes)

Design notes
============

**Responses flatten ``properties``.** ARM nests most of a resource's state
under ``properties``, while the SDK's models flattened it — consumer code reads
``vnet.address_space``.  ``AzureObject`` resolves the literal key first,
then a spelling-insensitive match, then repeats both inside ``properties``.
The top level wins, so a resource's own ``id`` / ``name`` / ``location`` are
never shadowed by a same-named property.

**Name matching normalises both sides** by removing underscores and
lowercasing, rather than converting camelCase to snake_case.  ARM has
acronym-suffixed fields like ``diskSizeGB``, and a naive converter yields
``disk_size_g_b`` — which would never match the ``disk_size_gb`` that consumer
code asks for.

**Authentication needs no cryptography.** A service principal exchanges its
client secret at the tenant's OAuth2 endpoint; a managed identity asks the
instance metadata service.  Tokens are cached and refreshed early, because a
token that passes the expiry check and then expires in flight fails the request
it was fetched for — mid-apply.

**Long-running operations are distinguished from failures.** A mutation that
ARM answers synchronously is not turned into a wait.  A poller that reaches
``Failed``/``Canceled`` raises ``AzureOperationError``; one that runs out
of time raises ``AzureOperationTimeout``, which is deliberately a
different type — the operation may still be running, so reporting it as a
failure would be wrong.

**``ResourceNotFoundError`` keeps its SDK name**, because consumer code catches
that name to mean "absent, carry on" — listing against a resource group that
does not exist yet, for instance.
