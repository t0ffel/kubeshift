"""Validate Common object attributes."""
import logging
from kubeshift.constants import LOGGER_DEFAULT

from kubeshift.exceptions import KubePatchError

logger = logging.getLogger(LOGGER_DEFAULT)


def metadata_patch(local_metadata, server_metadata):
    """Generate patch of top level metadata.

    server side v1.ObjectMeta usually contains more values - it's normal
    :param dict local_metadata: source metadata
    :param dict server_metadata: metadata from the server object
    :returns: dict of patch to apply to server_metadata to achieve
    local_metadata
    """
    res = {}
    if 'labels' in local_metadata:
        if sorted(local_metadata['labels']) != \
          sorted(server_metadata.get('labels', [])):
            res = {'labels': local_metadata['labels']}
    elif 'labels' in server_metadata:
        res['labels'] = 'null'
    if 'annotations' in local_metadata:
        if sorted(local_metadata['annotations']) !=\
          sorted(server_metadata.get('annotations', [])):
            res = {'annotations': local_metadata['annotations']}
    elif 'annotations' in server_metadata:
        res['annotations'] = 'null'
    return res


def eq_elem_in_list(elem, target_list):
    """Check if element is present in the target list.

    return False if no equivalient element exists in target list
    """
    for mele in target_list:
        if not patch_iteration(elem, mele):
            return True
    return False


def patch_list(list1, list2, mode):
    """Compare lists to have same elements.

    If the list doesn't contain dicts - consider ordinary comparison.
    Elements are the same if they have the same name.
    """
    if mode == 'replace':
        return list1
    elif mode != 'append':
        raise KubePatchError('Error patching list in mode {0}'.format(mode))
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


def patch_iteration(obj1, obj2, mode):
    """Form patch to apply to structure obj2 to get obj1 given mode.

    :param obj1: destination object to achieve.
    :param obj2: existing object to be transformed.
    :param string mode: append or replace
    :returns: dict patch to apply. {} if the objects are equivalient.
    """
    if isinstance(obj1, list):
        if type(obj1) != type(obj2):
            raise KubePatchError
        return patch_list(obj1, obj2, mode)
    # elif isinstance(obj1, (str, unicode)):
    #     if not isinstance(obj2, unicode):
    #         raise KubePatchError
    #     if obj1.encode('utf8') != obj2:
    #         return obj1
    #     return None
    elif not isinstance(obj1, dict):
        if type(obj1) != type(obj2):
            raise KubePatchError
        if obj1 != obj2:
            return obj1
        return None

    for key in obj1.keys():
        if key not in obj2:
            return obj1
        else:
            cur_res = patch_iteration(obj1[key], obj2[key])
            if cur_res:
                return obj1
    return None


def form_patch(local_obj, server_obj, mode):
    """Form patch to apply to the object, based on the given structure.

    The function will build strategic-merge-patch that needs to be applied to
    server_obj to make sure local_obj is created, based on the mode of patch.
    mode affects actions on how the lists are patched:
    list type              | append        | replace
    nested dicts (w/ name) | append/merge  | replace with src
    nested dicts (w/o name)| ???           | ??
    values                 | append        | replace

    Append will tell to append to the lists for lists with nested dicts.
    Replace will tell to replace lists.
    :param dict local_obj: definition of the local object
    :param dict server_obj: definition the object obtained from the server
    :param string mode: mode of the patch to form. Possible values: "append",
    "replace"
    :returns: a strategic-merge-patch dict.
    """
    if mode not in {"append", "replace"}:
        raise KubePatchError("bad, bad usage!")
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
            cur_res = patch_iteration(loc[key], serv[key])
            if cur_res:
                patch[key] = cur_res
        else:
            patch[key] = loc[key]

    return patch


def merge_dict(obj1, obj2):
    if isinstance(obj1, list):
        if type(obj1) != type(obj2):
            raise KubePatchError
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
    """Merge all the lists from patch with those in server_obj.
    """
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
