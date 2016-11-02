"""Validate Common object attributes."""
import re
import logging
from kubeshift.constants import (DEFAULT_NAMESPACE,
                                 LOGGER_DEFAULT)

from kubeshift.exceptions import KubeShiftError
logger = logging.getLogger(LOGGER_DEFAULT)


def validate(obj):
    """Verify the object has the require attributes.

    :params dict obj: an instance of a kubernetes / openshift types.
    :returns: apiVersion, kind, name
    :rtype: tuple
    :raises kubeshift.exceptions.KubeShiftError: if any of the attributes are missing
    """
    if not obj or not isinstance(obj, dict):
        raise KubeShiftError('Resource object missing or incorrect type')

    api_version = obj.get('apiVersion')
    if api_version is None:
        raise KubeShiftError('Resource object missing apiVersion')

    kind = obj.get('kind')
    if kind is None:
        raise KubeShiftError('Resource object missing kind')

    name = obj.get('metadata', {}).get('name')
    if name is None:
        raise KubeShiftError('Resource object missing metadata.name')

    return (api_version, kind, name)


def check_url(url):
    """Verify URL is properly constructed."""
    if not re.match('(?:http|https)://', url):
        raise KubeShiftError('URL does not include HTTP or HTTPS')


def is_valid_ns(ns):
    """Verify namespace format."""
    valid = True
    if not ns:
        valid = False
    elif len(ns) > 63:
        valid = False
    elif not re.match('^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', ns):
        valid = False
    return valid


def check_namespace(obj, namespace=None):
    """Get namespace from obj and validate."""
    ns = obj.get('metadata', {}).get('namespace')
    if is_valid_ns(ns):
        return ns
    return namespace
