"""
    .. module:: managementclients
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The management clients, mirroring the ``azure-mgmt-*``
               entry points.

    Each client exposes the operation groups its SDK counterpart exposed, so
    consumer code written as ``network_client.virtual_networks.list(...)``
    keeps working.  They all share one :class:`AzureArmClient` transport,
    because ARM is a single API — the SDK's split into separate packages is
    packaging, not protocol.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any

from ccai.restclient.azure.apigroups.computecollections import (
    DisksCollection, ProximityPlacementGroupsCollection,
    ResourceGroupsCollection, StorageAccountsCollection,
    VirtualMachineExtensionsCollection, VirtualMachinesCollection
)
from ccai.restclient.azure.apigroups.networkcollections import (
    NetworkInterfacesCollection, NetworkSecurityGroupsCollection,
    PublicIpAddressesCollection, RecordSetsCollection, SubnetsCollection,
    VirtualNetworksCollection
)
from ccai.restclient.azure.azurearmclient import AzureArmClient


class ResourceManagementClient:
    """
        Mirrors ``azure.mgmt.resource.ResourceManagementClient``.
    """

    def __init__(self, *, arm_client: AzureArmClient) -> None:
        """
            Construct a ResourceManagementClient.

            :param arm_client: The shared ARM transport.
        """
        self._arm_client = arm_client
        self.resource_groups: ResourceGroupsCollection = (
            ResourceGroupsCollection(client=arm_client))
        return

    @property
    def arm_client(self) -> AzureArmClient:
        """
            Return the underlying transport.

            :returns: The :class:`AzureArmClient`.
        """
        rtnval = self._arm_client
        return rtnval


class NetworkManagementClient:
    """
        Mirrors ``azure.mgmt.network.NetworkManagementClient``.
    """

    def __init__(self, *, arm_client: AzureArmClient) -> None:
        """
            Construct a NetworkManagementClient.

            :param arm_client: The shared ARM transport.
        """
        self._arm_client = arm_client
        self.virtual_networks: VirtualNetworksCollection = (
            VirtualNetworksCollection(client=arm_client))
        self.subnets: SubnetsCollection = SubnetsCollection(
            client=arm_client)
        self.network_interfaces: NetworkInterfacesCollection = (
            NetworkInterfacesCollection(client=arm_client))
        self.network_security_groups: NetworkSecurityGroupsCollection = (
            NetworkSecurityGroupsCollection(client=arm_client))
        self.public_ip_addresses: PublicIpAddressesCollection = (
            PublicIpAddressesCollection(client=arm_client))
        return

    @property
    def arm_client(self) -> AzureArmClient:
        """
            Return the underlying transport.

            :returns: The :class:`AzureArmClient`.
        """
        rtnval = self._arm_client
        return rtnval


class ComputeManagementClient:
    """
        Mirrors ``azure.mgmt.compute.ComputeManagementClient``.
    """

    def __init__(self, *, arm_client: AzureArmClient) -> None:
        """
            Construct a ComputeManagementClient.

            :param arm_client: The shared ARM transport.
        """
        self._arm_client = arm_client
        self.virtual_machines: VirtualMachinesCollection = (
            VirtualMachinesCollection(client=arm_client))
        self.virtual_machine_extensions: (
            VirtualMachineExtensionsCollection) = (
            VirtualMachineExtensionsCollection(client=arm_client))
        self.disks: DisksCollection = DisksCollection(client=arm_client)
        self.proximity_placement_groups: (
            ProximityPlacementGroupsCollection) = (
            ProximityPlacementGroupsCollection(client=arm_client))
        return

    @property
    def arm_client(self) -> AzureArmClient:
        """
            Return the underlying transport.

            :returns: The :class:`AzureArmClient`.
        """
        rtnval = self._arm_client
        return rtnval


class StorageManagementClient:
    """
        Mirrors ``azure.mgmt.storage.StorageManagementClient``.
    """

    def __init__(self, *, arm_client: AzureArmClient) -> None:
        """
            Construct a StorageManagementClient.

            :param arm_client: The shared ARM transport.
        """
        self._arm_client = arm_client
        self.storage_accounts: StorageAccountsCollection = (
            StorageAccountsCollection(client=arm_client))
        return

    @property
    def arm_client(self) -> AzureArmClient:
        """
            Return the underlying transport.

            :returns: The :class:`AzureArmClient`.
        """
        rtnval = self._arm_client
        return rtnval


class DnsManagementClient:
    """
        Mirrors ``azure.mgmt.dns.DnsManagementClient``.
    """

    def __init__(self, *, arm_client: AzureArmClient) -> None:
        """
            Construct a DnsManagementClient.

            :param arm_client: The shared ARM transport.
        """
        self._arm_client = arm_client
        self.record_sets: RecordSetsCollection = RecordSetsCollection(
            client=arm_client)
        return

    @property
    def arm_client(self) -> AzureArmClient:
        """
            Return the underlying transport.

            :returns: The :class:`AzureArmClient`.
        """
        rtnval = self._arm_client
        return rtnval


def build_management_clients(*, arm_client: AzureArmClient) -> Any:
    """
        Build all five management clients over one transport.

        :param arm_client: The shared ARM transport.

        :returns: A dict keyed by ``resource``, ``network``, ``compute``,
            ``storage`` and ``dns``.
    """
    rtnval = {
        "resource": ResourceManagementClient(arm_client=arm_client),
        "network": NetworkManagementClient(arm_client=arm_client),
        "compute": ComputeManagementClient(arm_client=arm_client),
        "storage": StorageManagementClient(arm_client=arm_client),
        "dns": DnsManagementClient(arm_client=arm_client),
    }
    return rtnval
