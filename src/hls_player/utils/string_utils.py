"""
This file contains the string utility methods
"""

from urllib.parse import urljoin


def resolve_url(base_url: str, relative_url: str) -> str:
    """
    Resolves a relative URL against a base URL.

    :param base_url: the base URL
    :param relative_url: relative or absolute URL to resolve
    :return: fully resolved absolute URL
    """

    return urljoin(base_url, relative_url)
