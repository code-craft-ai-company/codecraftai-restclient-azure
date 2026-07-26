"""
    .. module:: networkcollections
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The ``Microsoft.Network`` resource collections.

    The method and keyword names match the ``azure-mgmt-network`` operation
    groups exactly — ``begin_create_or_update(resource_group_name=,
    virtual_network_name=, parameters=)`` — because consumer code already
    calls them that way, and the keyword names differ per collection
    (``parameters`` here, ``subnet_parameters`` for subnets).

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.azure.apigroups.armcollection import ArmCollection
from ccai.restclient.azure.azureobject import AzureObject


NETWORK_API_VERSION = "2023-05-01"


class VirtualNetworksCollection(ArmCollection):
    """
        The virtual networks collection.
    """

    PROVIDER = "Microsoft.Network"
    RESOURCE_TYPE = "virtualNetworks"
    API_VERSION = NETWORK_API_VERSION

    def get(self, *, resource_group_name: str,
            virtual_network_name: str) -> AzureObject:
        """
            Fetch one virtual network.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The network name.

            :returns: The virtual network.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=virtual_network_name)
        return rtnval

    def list(self, resource_group_name: str) -> List[AzureObject]:
        """
            List the resource group's virtual networks.

            Accepts the group positionally as well, since the SDK's list
            operations are commonly called that way.

            :param resource_group_name: The resource group.

            :returns: The virtual networks.
        """
        rtnval = self._list(resource_group_name=resource_group_name)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               virtual_network_name: str,
                               parameters: Dict[str, Any]) -> Any:
        """
            Create or replace a virtual network.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The network name.
            :param parameters: The network body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._put(resource_group_name=resource_group_name,
                           name=virtual_network_name, parameters=parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str,
                     virtual_network_name: str) -> Any:
        """
            Delete a virtual network.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The network name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._delete(resource_group_name=resource_group_name,
                              name=virtual_network_name)
        return rtnval


class SubnetsCollection(ArmCollection):
    """
        The subnets collection.

        Subnets are children of a virtual network rather than of the resource
        group, so every path carries the parent network.
    """

    PROVIDER = "Microsoft.Network"
    RESOURCE_TYPE = "virtualNetworks"
    API_VERSION = NETWORK_API_VERSION

    def _subnet_collection_path(self, *, resource_group_name: str,
                                virtual_network_name: str) -> str:
        """
            Build the subnets collection path under a network.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The parent network.

            :returns: The collection path.
        """
        rtnval = "{}/subnets".format(
            self._item_path(resource_group_name=resource_group_name,
                            name=virtual_network_name))
        return rtnval

    def _subnet_item_path(self, *, resource_group_name: str,
                          virtual_network_name: str,
                          subnet_name: str) -> str:
        """
            Build one subnet's path.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The parent network.
            :param subnet_name: The subnet name.

            :returns: The item path.
        """
        rtnval = "{}/{}".format(
            self._subnet_collection_path(
                resource_group_name=resource_group_name,
                virtual_network_name=virtual_network_name), subnet_name)
        return rtnval

    def get(self, *, resource_group_name: str, virtual_network_name: str,
            subnet_name: str) -> AzureObject:
        """
            Fetch one subnet.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The parent network.
            :param subnet_name: The subnet name.

            :returns: The subnet.
        """
        rtnval = self._client.request(
            method="GET",
            path=self._subnet_item_path(
                resource_group_name=resource_group_name,
                virtual_network_name=virtual_network_name,
                subnet_name=subnet_name),
            api_version=self.API_VERSION)
        return rtnval

    def list(self, resource_group_name: str,
             virtual_network_name: str) -> List[AzureObject]:
        """
            List a network's subnets.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The parent network.

            :returns: The subnets.
        """
        rtnval = self._client.paginate(
            path=self._subnet_collection_path(
                resource_group_name=resource_group_name,
                virtual_network_name=virtual_network_name),
            api_version=self.API_VERSION)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               virtual_network_name: str, subnet_name: str,
                               subnet_parameters: Dict[str, Any]) -> Any:
        """
            Create or replace a subnet.

            The body keyword is ``subnet_parameters``, not ``parameters``;
            that is the SDK's spelling for this collection and what consumer
            code passes.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The parent network.
            :param subnet_name: The subnet name.
            :param subnet_parameters: The subnet body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._client.begin(
            method="PUT",
            path=self._subnet_item_path(
                resource_group_name=resource_group_name,
                virtual_network_name=virtual_network_name,
                subnet_name=subnet_name),
            api_version=self.API_VERSION, body=subnet_parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str,
                     virtual_network_name: str, subnet_name: str) -> Any:
        """
            Delete a subnet.

            :param resource_group_name: The resource group.
            :param virtual_network_name: The parent network.
            :param subnet_name: The subnet name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._client.begin(
            method="DELETE",
            path=self._subnet_item_path(
                resource_group_name=resource_group_name,
                virtual_network_name=virtual_network_name,
                subnet_name=subnet_name),
            api_version=self.API_VERSION)
        return rtnval


class NetworkInterfacesCollection(ArmCollection):
    """
        The network interfaces collection.
    """

    PROVIDER = "Microsoft.Network"
    RESOURCE_TYPE = "networkInterfaces"
    API_VERSION = NETWORK_API_VERSION

    def get(self, *, resource_group_name: str,
            network_interface_name: str) -> AzureObject:
        """
            Fetch one network interface.

            :param resource_group_name: The resource group.
            :param network_interface_name: The interface name.

            :returns: The network interface.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=network_interface_name)
        return rtnval

    def list(self, resource_group_name: str) -> List[AzureObject]:
        """
            List the resource group's network interfaces.

            :param resource_group_name: The resource group.

            :returns: The network interfaces.
        """
        rtnval = self._list(resource_group_name=resource_group_name)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               network_interface_name: str,
                               parameters: Dict[str, Any]) -> Any:
        """
            Create or replace a network interface.

            :param resource_group_name: The resource group.
            :param network_interface_name: The interface name.
            :param parameters: The interface body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._put(resource_group_name=resource_group_name,
                           name=network_interface_name,
                           parameters=parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str,
                     network_interface_name: str) -> Any:
        """
            Delete a network interface.

            :param resource_group_name: The resource group.
            :param network_interface_name: The interface name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._delete(resource_group_name=resource_group_name,
                              name=network_interface_name)
        return rtnval


class NetworkSecurityGroupsCollection(ArmCollection):
    """
        The network security groups collection.
    """

    PROVIDER = "Microsoft.Network"
    RESOURCE_TYPE = "networkSecurityGroups"
    API_VERSION = NETWORK_API_VERSION

    def get(self, *, resource_group_name: str,
            network_security_group_name: str) -> AzureObject:
        """
            Fetch one network security group.

            :param resource_group_name: The resource group.
            :param network_security_group_name: The group name.

            :returns: The network security group.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=network_security_group_name)
        return rtnval

    def list(self, resource_group_name: str) -> List[AzureObject]:
        """
            List the resource group's network security groups.

            :param resource_group_name: The resource group.

            :returns: The network security groups.
        """
        rtnval = self._list(resource_group_name=resource_group_name)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               network_security_group_name: str,
                               parameters: Dict[str, Any]) -> Any:
        """
            Create or replace a network security group.

            :param resource_group_name: The resource group.
            :param network_security_group_name: The group name.
            :param parameters: The group body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._put(resource_group_name=resource_group_name,
                           name=network_security_group_name,
                           parameters=parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str,
                     network_security_group_name: str) -> Any:
        """
            Delete a network security group.

            :param resource_group_name: The resource group.
            :param network_security_group_name: The group name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._delete(resource_group_name=resource_group_name,
                              name=network_security_group_name)
        return rtnval


class PublicIpAddressesCollection(ArmCollection):
    """
        The public IP addresses collection.
    """

    PROVIDER = "Microsoft.Network"
    RESOURCE_TYPE = "publicIPAddresses"
    API_VERSION = NETWORK_API_VERSION

    def get(self, *, resource_group_name: str,
            public_ip_address_name: str) -> AzureObject:
        """
            Fetch one public IP address.

            :param resource_group_name: The resource group.
            :param public_ip_address_name: The address name.

            :returns: The public IP address.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=public_ip_address_name)
        return rtnval

    def list(self, resource_group_name: str) -> List[AzureObject]:
        """
            List the resource group's public IP addresses.

            :param resource_group_name: The resource group.

            :returns: The public IP addresses.
        """
        rtnval = self._list(resource_group_name=resource_group_name)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               public_ip_address_name: str,
                               parameters: Dict[str, Any]) -> Any:
        """
            Create or replace a public IP address.

            :param resource_group_name: The resource group.
            :param public_ip_address_name: The address name.
            :param parameters: The address body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._put(resource_group_name=resource_group_name,
                           name=public_ip_address_name,
                           parameters=parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str,
                     public_ip_address_name: str) -> Any:
        """
            Delete a public IP address.

            :param resource_group_name: The resource group.
            :param public_ip_address_name: The address name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._delete(resource_group_name=resource_group_name,
                              name=public_ip_address_name)
        return rtnval


class RecordSetsCollection(ArmCollection):
    """
        The DNS record sets collection.

        Record sets are children of a zone AND discriminated by record type,
        so the type is part of the path rather than of the body.
    """

    PROVIDER = "Microsoft.Network"
    RESOURCE_TYPE = "dnsZones"
    API_VERSION = "2018-05-01"

    def _record_path(self, *, resource_group_name: str, zone_name: str,
                     record_type: str,
                     relative_record_set_name: str) -> str:
        """
            Build one record set's path.

            :param resource_group_name: The resource group.
            :param zone_name: The DNS zone.
            :param record_type: The record type, e.g. ``A``.
            :param relative_record_set_name: The record name within the zone.

            :returns: The item path.
        """
        rtnval = "{}/{}/{}".format(
            self._item_path(resource_group_name=resource_group_name,
                            name=zone_name),
            record_type, relative_record_set_name)
        return rtnval

    def get(self, *, resource_group_name: str, zone_name: str,
            relative_record_set_name: str,
            record_type: str) -> AzureObject:
        """
            Fetch one record set.

            :param resource_group_name: The resource group.
            :param zone_name: The DNS zone.
            :param relative_record_set_name: The record name.
            :param record_type: The record type.

            :returns: The record set.
        """
        rtnval = self._client.request(
            method="GET",
            path=self._record_path(
                resource_group_name=resource_group_name,
                zone_name=zone_name, record_type=record_type,
                relative_record_set_name=relative_record_set_name),
            api_version=self.API_VERSION)
        return rtnval

    def create_or_update(self, *, resource_group_name: str, zone_name: str,
                         relative_record_set_name: str, record_type: str,
                         parameters: Dict[str, Any]) -> AzureObject:
        """
            Create or replace a record set.

            DNS record writes are not long-running, so this returns the
            record rather than a poller.

            :param resource_group_name: The resource group.
            :param zone_name: The DNS zone.
            :param relative_record_set_name: The record name.
            :param record_type: The record type.
            :param parameters: The record body.

            :returns: The record set.
        """
        rtnval = self._client.request(
            method="PUT",
            path=self._record_path(
                resource_group_name=resource_group_name,
                zone_name=zone_name, record_type=record_type,
                relative_record_set_name=relative_record_set_name),
            api_version=self.API_VERSION, body=parameters)
        return rtnval

    def delete(self, *, resource_group_name: str, zone_name: str,
               relative_record_set_name: str,
               record_type: str) -> AzureObject:
        """
            Delete a record set.

            :param resource_group_name: The resource group.
            :param zone_name: The DNS zone.
            :param relative_record_set_name: The record name.
            :param record_type: The record type.

            :returns: The decoded response.
        """
        rtnval = self._client.request(
            method="DELETE",
            path=self._record_path(
                resource_group_name=resource_group_name,
                zone_name=zone_name, record_type=record_type,
                relative_record_set_name=relative_record_set_name),
            api_version=self.API_VERSION)
        return rtnval

    def list_by_dns_zone(self, *, resource_group_name: str,
                         zone_name: str) -> List[AzureObject]:
        """
            List every record set in a zone.

            :param resource_group_name: The resource group.
            :param zone_name: The DNS zone.

            :returns: The record sets.
        """
        rtnval = self._client.paginate(
            path="{}/recordsets".format(
                self._item_path(resource_group_name=resource_group_name,
                                name=zone_name)),
            api_version=self.API_VERSION)
        return rtnval
