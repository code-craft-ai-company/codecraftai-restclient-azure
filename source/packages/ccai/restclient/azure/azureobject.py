"""
    .. module:: azureobject
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`AzureObject` — ARM JSON presented the way the
               ``azure-mgmt-*`` object model presented it.

    Azure Resource Manager returns camelCase JSON with most of a resource's
    interesting state nested under ``properties``:

    .. code:: json

        {"id": "...", "name": "vnet-a", "location": "eastus",
         "properties": {"addressSpace": {"addressPrefixes": ["10.0.0.0/16"]}}}

    The SDK's models flatten that, so consumer code reads
    ``vnet.address_space.address_prefixes``.  An :class:`AzureObject` answers
    the same way: attribute lookup tries the literal key, then a
    case-and-underscore-insensitive match, then repeats both inside
    ``properties``.

    The name matching normalises by removing underscores and lowercasing on
    BOTH sides rather than converting camelCase to snake_case.  That is
    deliberate: ARM uses acronym-suffixed fields like ``diskSizeGB``, and a
    naive converter yields ``disk_size_g_b`` — which would never match the
    ``disk_size_gb`` the SDK exposed and consumer code asks for.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, Optional


def normalize_name(name: str) -> str:
    """
        Reduce a field name to a spelling-insensitive form.

        Removing underscores and lowercasing makes ``disk_size_gb``,
        ``diskSizeGB`` and ``DiskSizeGb`` all compare equal, which is what
        lets one lookup serve both the SDK's snake_case names and ARM's
        camelCase wire names.

        :param name: The field name.

        :returns: The normalised name.
    """
    rtnval = name.replace("_", "").lower()
    return rtnval


def wrap_azure_value(value: Any) -> Any:
    """
        Wrap a decoded JSON value so nested objects stay attribute
        addressable.

        :param value: The decoded JSON value.

        :returns: An :class:`AzureObject` for dicts, a list of wrapped values
            for lists, or the value unchanged.
    """
    if isinstance(value, AzureObject) is True:
        rtnval = value
        return rtnval
    if isinstance(value, dict) is True:
        rtnval = AzureObject(value)
        return rtnval
    if isinstance(value, list) is True:
        rtnval = [wrap_azure_value(item) for item in value]
        return rtnval
    rtnval = value
    return rtnval


class AzureObject(dict):
    """
        A ``dict`` of ARM JSON that is also attribute addressable, with
        ``properties`` flattened onto the object.

        A missing field reads as ``None`` so ``getattr(obj, "field", None)``
        guards written against the SDK behave the same way.
    """

    def __getattr__(self, name: str) -> Any:
        """
            Resolve a field by attribute access.

            Resolution order is: the literal key, a spelling-insensitive
            match at the top level, then the same two inside ``properties``.
            The top level wins so a resource's own ``id`` / ``name`` /
            ``location`` are never shadowed by a same-named property.

            :param name: The field name, in SDK or wire spelling.

            :returns: The wrapped field value, or ``None`` when absent.
        """
        if name.startswith("_") is True:
            # Never resolve private/dunder lookups as API fields; that would
            # make copy/pickle/inspect machinery see phantom attributes.
            raise AttributeError(name)

        found, value = self._lookup(name=name)
        if found is True:
            rtnval = wrap_azure_value(value)
            return rtnval

        rtnval = None
        return rtnval

    def _lookup(self, *, name: str) -> Any:
        """
            Find a field by literal key, then by normalised name, at the top
            level and then inside ``properties``.

            :param name: The field name.

            :returns: A ``(found, value)`` pair.
        """
        if dict.__contains__(self, name) is True:
            rtnval = (True, dict.__getitem__(self, name))
            return rtnval

        wanted = normalize_name(name)

        for key in dict.keys(self):
            if normalize_name(key) == wanted:
                rtnval = (True, dict.__getitem__(self, key))
                return rtnval

        properties = None
        for key in dict.keys(self):
            if normalize_name(key) == "properties":
                properties = dict.__getitem__(self, key)
                break

        if isinstance(properties, dict) is True:
            if name in properties:
                rtnval = (True, properties[name])
                return rtnval
            for key in properties.keys():
                if normalize_name(key) == wanted:
                    rtnval = (True, properties[key])
                    return rtnval

        rtnval = (False, None)
        return rtnval

    def __setattr__(self, name: str, value: Any) -> None:
        """
            Set a field by attribute assignment.

            :param name: The field name.
            :param value: The value to store.

            :returns: ``None``
        """
        if name.startswith("_") is True:
            object.__setattr__(self, name, value)
            return
        self[name] = value
        return

    def as_dict(self) -> Dict[str, Any]:
        """
            Return the underlying plain dictionary.

            :returns: The wire-shaped dictionary.
        """
        rtnval = {key: dict.__getitem__(self, key)
                  for key in dict.keys(self)}
        return rtnval


def resource_name_of(resource_id: Optional[str]) -> Optional[str]:
    """
        Read the trailing resource name out of an ARM resource id.

        :param resource_id: A fully-qualified ARM resource id, or None.

        :returns: The final path segment, or None.
    """
    if resource_id is None or len(resource_id) == 0:
        rtnval = None
        return rtnval

    rtnval = resource_id.rstrip("/").rsplit("/", 1)[-1]
    return rtnval
