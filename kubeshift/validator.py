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


def check_namespace(obj, default):
    """Get namespace from obj and validate."""
    ns = obj.get('metadata', {}).get('namespace')
    if is_valid_ns(ns):
        return ns
    return default

def metadata_patch(local_metadata, server_metadata):
    """Validates that annotations, labels are the same"""
    res = {}
    if 'labels' in local_metadata:
        if sorted(local_metadata['labels']) != sorted(server_metadata.get('labels', [])):
            res = {'labels': local_metadata['labels']}
    if 'annotations' in local_metadata:
        if sorted(local_metadata['annotations']) != sorted(server_metadata.get('annotations', [])):
            res = {'annotations': local_metadata['annotations']}
    return res


def eq_elem_in_list(elem, list):
    """Element is in the target list
    return False if no equivalient element exists in target list"""
    found = False
    for le in list:
        if 'name' not in le:
            raise Exception('Name of the element is missing!')
        if elem['name'] == le['name']:
            if simple_compare(elem, le):
                return False
            found = True
    return found

def list_compare(list1, list2):
    """Compare lists to have same elements.
    Elements are the same if they have the same name.
    """
    if len(list1) != len(list2):
        return list1
    for el in list1:
        if 'name' not in el:
            raise Exception('Name of the element is missing!')
        if not eq_elem_in_list(el, list2):
            return list1
    return None


def simple_compare(obj1, obj2):
    if isinstance(obj1, list):
        if type(obj1) != type(obj2):
            logger.debug('types compared: {0}, {1}'.format(type(obj1), type(obj2)))
            raise Exception
        return list_compare(obj1, obj2)
    elif isinstance(obj1, str):
        logger.debug('types: {0}, {1}'.format(type(obj1), type(obj2)))
        if not isinstance(obj2, unicode):
            logger.debug('object is: {0}'.format(obj2))
            raise Exception
        if obj1.encode('utf8') != obj2:
            logger.debug('Non-equal stuff found: {0}, {1}'.format(obj1, obj2))
            return obj1
        return None
    elif not isinstance(obj1, dict):
        if type(obj1) != type(obj2):
            logger.debug('types compared: {0}, {1}'.format(type(obj1), type(obj2)))
            raise Exception
        if obj1 != obj2:
            logger.debug('Non-equal stuff found: {0}, {1}'.format(obj1, obj2))
            return obj1
        return None

    for key in obj1.keys():
        if key not in obj2:
            return obj1
        else:
            cur_res = simple_compare(obj1[key], obj2[key])
            if cur_res:
                return obj1
    return None

def form_patch(local_obj, server_obj):
    """Form patch to apply to the object, based on the spec given.

    status field is not taken into account.
    If a value or a list are not equal - patch is the local's obj value/list,
    When comparing a dict:
    local object's key is absent in server obj - patch is the k/v of local obj.
    local object's key is present in server obj, but value is different - patch
    is the entire local obj(except for top level).
    Metadata is compared separately.
    """
    loc = local_obj.copy()
    serv = server_obj.copy()
    serv.pop('status', None)
    loc.pop('status', None)
    metadata_diff = metadata_patch(loc.pop('metadata'), serv.pop('metadata'))
#    import pdb; pdb.set_trace()
    if metadata_diff:
        patch = {'metadata': metadata_diff}
    else:
        patch = {}
    for key in loc.keys():
        if key in serv:
            cur_res = simple_compare(loc[key], serv[key])
            if cur_res:
                patch[key] = cur_res
        else:
            patch[key] = loc[key]

    return patch
