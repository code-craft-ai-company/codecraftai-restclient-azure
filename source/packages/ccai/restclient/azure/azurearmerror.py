"""
    .. module:: azurearmerror
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Errors raised for non-success Azure Resource Manager
               responses.

    :class:`ResourceNotFoundError` keeps the name the ``azure-core`` package
    used, because consumer code catches that name to mean "absent, carry on"
    — a listing against a resource group that does not exist yet, for
    instance.  Keeping the spelling lets those handlers keep working.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Optional


class AzureRequestError(Exception):
    """
        Raised when ARM returns a non-success status.

        :ivar status_code: The HTTP status code.
        :ivar code: The ARM error code, e.g. ``ResourceGroupNotFound``.
        :ivar message: The ARM error message.
        :ivar body: The raw response body text.
    """

    def __init__(self, message: str, *, status_code: int = 0,
                 code: str = "", body: Optional[str] = None) -> None:
        """
            Construct an AzureRequestError.

            :param message: The human-readable error message.
            :param status_code: The HTTP status code.
            :param code: The ARM error code.
            :param body: The raw response body.
        """
        super().__init__(message)
        self.status_code: int = status_code
        self.code: str = code
        self.body: Optional[str] = body
        return


class ResourceNotFoundError(AzureRequestError):
    """
        Raised when ARM answers 404.

        Named to match ``azure.core.exceptions.ResourceNotFoundError``, which
        consumer code already catches to mean "absent".
    """


class AzureOperationError(AzureRequestError):
    """
        Raised when a long-running operation finishes in a non-success state.

        The HTTP call that started it succeeded, so this is distinct from a
        failed request: the work was accepted and then failed.
    """


class AzureOperationTimeout(AzureRequestError):
    """
        Raised when a long-running operation does not reach a terminal state
        inside the caller's timeout.

        Distinct from :class:`AzureOperationError` because the operation may
        still be running — the caller stopped waiting, ARM did not stop
        working, so treating this as "failed" would be wrong.
    """
