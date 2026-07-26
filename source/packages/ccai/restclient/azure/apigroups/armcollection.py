"""
    .. module:: armcollection
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`ArmCollection` — the shared behaviour of an ARM
               resource collection.

    Every ARM resource type is addressed the same way, so the path building,
    listing and mutation logic lives here and each concrete collection only
    declares its provider namespace, type segment and api-version — plus the
    keyword names its consumers already use, which differ per collection and
    are therefore spelled out rather than generated.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.azure.azureobject import AzureObject


class ArmCollection:
    """
        Shared behaviour for an ARM resource collection.

        :cvar PROVIDER: The resource provider, e.g. ``Microsoft.Network``.
        :cvar RESOURCE_TYPE: The type segment, e.g. ``virtualNetworks``.
        :cvar API_VERSION: The api-version this type requires.
    """

    PROVIDER: str = ""
    RESOURCE_TYPE: str = ""
    API_VERSION: str = ""

    def __init__(self, *, client: Any) -> None:
        """
            Construct a collection bound to a transport.

            :param client: The owning :class:`AzureArmClient`.
        """
        self._client = client
        return

    def _group_path(self, *, resource_group_name: str) -> str:
        """
            Build the collection path inside a resource group.

            :param resource_group_name: The resource group.

            :returns: The collection path.
        """
        rtnval = self._client.subscription_path(
            tail="/resourceGroups/{}/providers/{}/{}".format(
                resource_group_name, self.PROVIDER, self.RESOURCE_TYPE))
        return rtnval

    def _item_path(self, *, resource_group_name: str, name: str) -> str:
        """
            Build one resource's path.

            :param resource_group_name: The resource group.
            :param name: The resource name.

            :returns: The item path.
        """
        rtnval = "{}/{}".format(
            self._group_path(resource_group_name=resource_group_name), name)
        return rtnval

    def _list(self, *, resource_group_name: str) -> List[AzureObject]:
        """
            List the collection inside a resource group.

            :param resource_group_name: The resource group.

            :returns: The resources.
        """
        rtnval = self._client.paginate(
            path=self._group_path(resource_group_name=resource_group_name),
            api_version=self.API_VERSION)
        return rtnval

    def _get(self, *, resource_group_name: str, name: str) -> AzureObject:
        """
            Fetch one resource.

            :param resource_group_name: The resource group.
            :param name: The resource name.

            :returns: The resource.
        """
        rtnval = self._client.request(
            method="GET",
            path=self._item_path(resource_group_name=resource_group_name,
                                 name=name),
            api_version=self.API_VERSION)
        return rtnval

    def _put(self, *, resource_group_name: str, name: str,
             parameters: Optional[Dict[str, Any]]) -> Any:
        """
            Create or replace one resource, returning a poller.

            :param resource_group_name: The resource group.
            :param name: The resource name.
            :param parameters: The resource body.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._client.begin(
            method="PUT",
            path=self._item_path(resource_group_name=resource_group_name,
                                 name=name),
            api_version=self.API_VERSION, body=parameters)
        return rtnval

    def _delete(self, *, resource_group_name: str, name: str) -> Any:
        """
            Delete one resource, returning a poller.

            :param resource_group_name: The resource group.
            :param name: The resource name.

            :returns: An :class:`LroPoller`.
        """
        rtnval = self._client.begin(
            method="DELETE",
            path=self._item_path(resource_group_name=resource_group_name,
                                 name=name),
            api_version=self.API_VERSION)
        return rtnval
