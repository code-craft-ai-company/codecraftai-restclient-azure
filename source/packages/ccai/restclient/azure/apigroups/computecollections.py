"""
    .. module:: computecollections
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The ``Microsoft.Compute``, ``Microsoft.Storage`` and
               resource-group collections.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List

from ccai.restclient.azure.apigroups.armcollection import ArmCollection
from ccai.restclient.azure.azureobject import AzureObject


COMPUTE_API_VERSION = "2023-09-01"

STORAGE_API_VERSION = "2023-01-01"

RESOURCE_GROUPS_API_VERSION = "2021-04-01"


class VirtualMachinesCollection(ArmCollection):
    """
        The virtual machines collection.
    """

    PROVIDER = "Microsoft.Compute"
    RESOURCE_TYPE = "virtualMachines"
    API_VERSION = COMPUTE_API_VERSION

    def get(self, *, resource_group_name: str,
            vm_name: str) -> AzureObject:
        """
            Fetch one virtual machine.

            :param resource_group_name: The resource group.
            :param vm_name: The machine name.

            :returns: The virtual machine.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=vm_name)
        return rtnval

    def list(self, resource_group_name: str) -> List[AzureObject]:
        """
            List the resource group's virtual machines.

            :param resource_group_name: The resource group.

            :returns: The virtual machines.
        """
        rtnval = self._list(resource_group_name=resource_group_name)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               vm_name: str,
                               parameters: Dict[str, Any]) -> Any:
        """
            Create or replace a virtual machine.

            :param resource_group_name: The resource group.
            :param vm_name: The machine name.
            :param parameters: The machine body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._put(resource_group_name=resource_group_name,
                           name=vm_name, parameters=parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str,
                     vm_name: str) -> Any:
        """
            Delete a virtual machine.

            :param resource_group_name: The resource group.
            :param vm_name: The machine name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._delete(resource_group_name=resource_group_name,
                              name=vm_name)
        return rtnval


class VirtualMachineExtensionsCollection(ArmCollection):
    """
        The virtual machine extensions collection.

        Extensions are children of a machine, so every path carries the
        parent VM.
    """

    PROVIDER = "Microsoft.Compute"
    RESOURCE_TYPE = "virtualMachines"
    API_VERSION = COMPUTE_API_VERSION

    def _extension_path(self, *, resource_group_name: str, vm_name: str,
                        vm_extension_name: str) -> str:
        """
            Build one extension's path.

            :param resource_group_name: The resource group.
            :param vm_name: The parent machine.
            :param vm_extension_name: The extension name.

            :returns: The item path.
        """
        rtnval = "{}/extensions/{}".format(
            self._item_path(resource_group_name=resource_group_name,
                            name=vm_name), vm_extension_name)
        return rtnval

    def get(self, *, resource_group_name: str, vm_name: str,
            vm_extension_name: str) -> AzureObject:
        """
            Fetch one extension.

            :param resource_group_name: The resource group.
            :param vm_name: The parent machine.
            :param vm_extension_name: The extension name.

            :returns: The extension.
        """
        rtnval = self._client.request(
            method="GET",
            path=self._extension_path(
                resource_group_name=resource_group_name, vm_name=vm_name,
                vm_extension_name=vm_extension_name),
            api_version=self.API_VERSION)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               vm_name: str, vm_extension_name: str,
                               extension_parameters: Dict[str, Any]) -> Any:
        """
            Create or replace a machine extension.

            The body keyword is ``extension_parameters``; that is the SDK's
            spelling for this collection and what consumer code passes.

            :param resource_group_name: The resource group.
            :param vm_name: The parent machine.
            :param vm_extension_name: The extension name.
            :param extension_parameters: The extension body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._client.begin(
            method="PUT",
            path=self._extension_path(
                resource_group_name=resource_group_name, vm_name=vm_name,
                vm_extension_name=vm_extension_name),
            api_version=self.API_VERSION, body=extension_parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str, vm_name: str,
                     vm_extension_name: str) -> Any:
        """
            Delete a machine extension.

            :param resource_group_name: The resource group.
            :param vm_name: The parent machine.
            :param vm_extension_name: The extension name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._client.begin(
            method="DELETE",
            path=self._extension_path(
                resource_group_name=resource_group_name, vm_name=vm_name,
                vm_extension_name=vm_extension_name),
            api_version=self.API_VERSION)
        return rtnval


class DisksCollection(ArmCollection):
    """
        The managed disks collection.
    """

    PROVIDER = "Microsoft.Compute"
    RESOURCE_TYPE = "disks"
    API_VERSION = "2023-04-02"

    def get(self, *, resource_group_name: str,
            disk_name: str) -> AzureObject:
        """
            Fetch one disk.

            :param resource_group_name: The resource group.
            :param disk_name: The disk name.

            :returns: The disk.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=disk_name)
        return rtnval

    def list_by_resource_group(self,
                               resource_group_name: str
                               ) -> List[AzureObject]:
        """
            List the resource group's disks.

            :param resource_group_name: The resource group.

            :returns: The disks.
        """
        rtnval = self._list(resource_group_name=resource_group_name)
        return rtnval

    def begin_create_or_update(self, *, resource_group_name: str,
                               disk_name: str,
                               disk: Dict[str, Any]) -> Any:
        """
            Create or replace a disk.

            The body keyword is ``disk``, not ``parameters``; that is the
            SDK's spelling for this collection.

            :param resource_group_name: The resource group.
            :param disk_name: The disk name.
            :param disk: The disk body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._put(resource_group_name=resource_group_name,
                           name=disk_name, parameters=disk)
        return rtnval

    def begin_delete(self, *, resource_group_name: str,
                     disk_name: str) -> Any:
        """
            Delete a disk.

            :param resource_group_name: The resource group.
            :param disk_name: The disk name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._delete(resource_group_name=resource_group_name,
                              name=disk_name)
        return rtnval


class ProximityPlacementGroupsCollection(ArmCollection):
    """
        The proximity placement groups collection.

        These writes are not long-running, so the methods return the resource
        directly rather than a poller — matching the SDK, which exposes them
        without the ``begin_`` prefix.
    """

    PROVIDER = "Microsoft.Compute"
    RESOURCE_TYPE = "proximityPlacementGroups"
    API_VERSION = COMPUTE_API_VERSION

    def get(self, *, resource_group_name: str,
            proximity_placement_group_name: str) -> AzureObject:
        """
            Fetch one placement group.

            :param resource_group_name: The resource group.
            :param proximity_placement_group_name: The group name.

            :returns: The placement group.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=proximity_placement_group_name)
        return rtnval

    def create_or_update(self, *, resource_group_name: str,
                         proximity_placement_group_name: str,
                         parameters: Dict[str, Any]) -> AzureObject:
        """
            Create or replace a placement group.

            :param resource_group_name: The resource group.
            :param proximity_placement_group_name: The group name.
            :param parameters: The group body.

            :returns: The placement group.
        """
        rtnval = self._client.request(
            method="PUT",
            path=self._item_path(
                resource_group_name=resource_group_name,
                name=proximity_placement_group_name),
            api_version=self.API_VERSION, body=parameters)
        return rtnval

    def delete(self, *, resource_group_name: str,
               proximity_placement_group_name: str) -> AzureObject:
        """
            Delete a placement group.

            :param resource_group_name: The resource group.
            :param proximity_placement_group_name: The group name.

            :returns: The decoded response.
        """
        rtnval = self._client.request(
            method="DELETE",
            path=self._item_path(
                resource_group_name=resource_group_name,
                name=proximity_placement_group_name),
            api_version=self.API_VERSION)
        return rtnval


class StorageAccountsCollection(ArmCollection):
    """
        The storage accounts collection.
    """

    PROVIDER = "Microsoft.Storage"
    RESOURCE_TYPE = "storageAccounts"
    API_VERSION = STORAGE_API_VERSION

    def get_properties(self, *, resource_group_name: str,
                       account_name: str) -> AzureObject:
        """
            Fetch one storage account.

            :param resource_group_name: The resource group.
            :param account_name: The account name.

            :returns: The storage account.
        """
        rtnval = self._get(resource_group_name=resource_group_name,
                           name=account_name)
        return rtnval

    def list_by_resource_group(self, *, resource_group_name: str
                               ) -> List[AzureObject]:
        """
            List the resource group's storage accounts.

            :param resource_group_name: The resource group.

            :returns: The storage accounts.
        """
        rtnval = self._list(resource_group_name=resource_group_name)
        return rtnval

    def begin_create(self, *, resource_group_name: str, account_name: str,
                     parameters: Dict[str, Any]) -> Any:
        """
            Create a storage account.

            The SDK names this ``begin_create``, not
            ``begin_create_or_update``, and account creation really is
            long-running.

            :param resource_group_name: The resource group.
            :param account_name: The account name.
            :param parameters: The account body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._put(resource_group_name=resource_group_name,
                           name=account_name, parameters=parameters)
        return rtnval

    def delete(self, *, resource_group_name: str,
               account_name: str) -> AzureObject:
        """
            Delete a storage account.

            Account deletion is synchronous, so this returns directly rather
            than a poller — matching the SDK's unprefixed name.

            :param resource_group_name: The resource group.
            :param account_name: The account name.

            :returns: The decoded response.
        """
        rtnval = self._client.request(
            method="DELETE",
            path=self._item_path(resource_group_name=resource_group_name,
                                 name=account_name),
            api_version=self.API_VERSION)
        return rtnval


class ResourceGroupsCollection:
    """
        The resource groups collection.

        Resource groups sit directly under the subscription rather than
        inside a group, so this does not extend :class:`ArmCollection`.
    """

    API_VERSION = RESOURCE_GROUPS_API_VERSION

    def __init__(self, *, client: Any) -> None:
        """
            Construct the collection bound to a transport.

            :param client: The owning :class:`AzureArmClient`.
        """
        self._client = client
        return

    def _path(self, *, resource_group_name: str) -> str:
        """
            Build one resource group's path.

            :param resource_group_name: The resource group name.

            :returns: The item path.
        """
        rtnval = self._client.subscription_path(
            tail="/resourcegroups/{}".format(resource_group_name))
        return rtnval

    def get(self, *, resource_group_name: str) -> AzureObject:
        """
            Fetch one resource group.

            :param resource_group_name: The resource group name.

            :returns: The resource group.
        """
        rtnval = self._client.request(
            method="GET",
            path=self._path(resource_group_name=resource_group_name),
            api_version=self.API_VERSION)
        return rtnval

    def create_or_update(self, *, resource_group_name: str,
                         parameters: Dict[str, Any]) -> AzureObject:
        """
            Create or replace a resource group.

            Group creation is synchronous.

            :param resource_group_name: The resource group name.
            :param parameters: The group body, carrying at least a location.

            :returns: The resource group.
        """
        rtnval = self._client.request(
            method="PUT",
            path=self._path(resource_group_name=resource_group_name),
            api_version=self.API_VERSION, body=parameters)
        return rtnval

    def begin_delete(self, *, resource_group_name: str) -> Any:
        """
            Delete a resource group and everything in it.

            :param resource_group_name: The resource group name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._client.begin(
            method="DELETE",
            path=self._path(resource_group_name=resource_group_name),
            api_version=self.API_VERSION)
        return rtnval

    def list(self) -> List[AzureObject]:
        """
            List the subscription's resource groups.

            :returns: The resource groups.
        """
        rtnval = self._client.paginate(
            path=self._client.subscription_path(tail="/resourcegroups"),
            api_version=self.API_VERSION)
        return rtnval
