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


def eq_elem_in_list(elem, target_list):
    """Element is in the target list
    return False if no equivalient element exists in target list"""
    for mele in target_list:
#        if 'name' not in le:
#            raise Exception('Name of the element is missing!')
        if not simple_compare(elem, mele):
            return True
    return False

def list_compare(list1, list2):
    """Compare lists to have same elements.
    If the list doesn't contain dicts - consider ordinary comparison.
    Elements are the same if they have the same name.
    """
    if len(list1) != len(list2):
        return list1
    if len(list1) == 0:
        return None

    if not isinstance(list1[0], dict):
        if set(list1) == set(list2):
            return None
        else:
            return list1

    for el in list1:
        if not eq_elem_in_list(el, list2):
            return list1
    return None


def simple_compare(obj1, obj2):
    if isinstance(obj1, list):
        if type(obj1) != type(obj2):
            raise Exception
        return list_compare(obj1, obj2)
    elif isinstance(obj1, str):
        if not isinstance(obj2, unicode):
            raise Exception
        if obj1.encode('utf8') != obj2:
            return obj1
        return None
    elif not isinstance(obj1, dict):
        if type(obj1) != type(obj2):
            raise Exception
        if obj1 != obj2:
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

def merge_dict(obj1, obj2):
    if isinstance(obj1, list):
        if type(obj1) != type(obj2):
            raise Exception
        res = merge_lists(obj1, obj2)
        return res
    logger.debug("merge_dict didn't find stuff!")

def merge_lists(list1, list2):

    if not isinstance(list1[0], dict):
        set_diff = set(list1) - set(list2)
        res = list2 + list(set_diff)
        if set(res) == set(list2):
            return None
    diff = []
    for el in list1:
        if el not in list2:
            diff.append(el)
#    import pdb; pdb.set_trace()
#    logger.debug("merge_lists result is {0}".format(res))
    if diff:
        list2.extend(diff)
        return list2
    return None

def merge_objs(server_obj, patch):
    """Merge all the lists from patch with those in server_obj."""
    loc = patch.copy()
    serv = server_obj.copy()
    serv.pop('status', None)
    loc.pop('status', None)
#    metadata_diff = metadata_patch(loc.pop('metadata'), serv.pop('metadata'))

    if not patch:
        return {}
    diff = {}
    # Deal with real dicts
    for key in loc.keys():
        if key in serv:
            cur_res = merge_dict(loc[key], serv[key])
#            import pdb; pdb.set_trace()
            if cur_res:
                diff[key] = cur_res
        else:
            diff[key] = loc[key]
    logger.debug("merge_objs result is {0}".format(diff))
    return diff
