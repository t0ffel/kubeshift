"""Compare object attributes."""
import logging
from kubeshift.constants import LOGGER_DEFAULT

from kubeshift.exceptions import KubePatchError

logger = logging.getLogger(LOGGER_DEFAULT)


def del_eq_elem_in_list(elem, target_list):
    """Check if element is present in the target list.

    return False if no equivalient element exists in target list
    """
    found = False
    logging.debug('list before: {0}, elem: {1}'.format(target_list, elem))
#    import pdb; pdb.set_trace()
    for i,mele in enumerate(target_list):
        if diff_iteration(elem, mele):
            found = True
            break
#    import pdb; pdb.set_trace()
    if found:
        del target_list[i]
        logging.debug('list after purging: {}'.format(target_list))
        return True
    return False


def _diff_dict_list_iter(list1, list2):
    """Iteration comparison of the lists of dicts.
    Returns True if the lists are equal, False otherwise.
    """
    if len(list1)  == 0:
        if len(list2) != 0:
            return False
        else:
            return True
    el = list1.pop()
#    logging.debug('el is {}'.format(el))
    if not del_eq_elem_in_list(el, list2):
        return False
    return _diff_dict_list_iter(list1, list2)

def diff_list(list1, list2):
    """Compare lists to have same elements.

    If the list doesn't contain dicts - consider ordinary comparison.
    Elements are the same if they have the same name.
    Returns True if the lists are equal
    Returns False if the lists are different
    """
#    if len(list1) == 0:
#        logging.debug('Returning non-empty list {}'.format(list2))
#        if len(list2) != 0:
#            return False
#        else:
#            return True
    # Lists of non-dict elements.
#    if not isinstance(list1[0], dict):
    if sorted(list1) == sorted(list2):
        return True
    else:
        return False

#    return _diff_dict_list_iter(list1[:], list2[:])


def diff_iteration(obj1, obj2):
    """Compare dicts obj1 and obj2.

    :param obj1: resource before the modification
    :param obj2: resource after the modification
    :returns: True if objects are equal, False if objects are different.
    """
#    logging.debug('current obj is {}'.format(obj1))
    if isinstance(obj1, list):
        if type(obj1) != type(obj2):
            raise KubePatchError('Trying to compare {0} to list'.format(obj2))
        return diff_list(obj1, obj2)
    elif not isinstance(obj1, dict):
        if isinstance(obj2, dict) or isinstance(obj2, list):
            raise KubePatchError('Trying to compare {0} to value'.format(obj2))
        if obj1 != obj2:
            return False
        return True
    elif obj1 == {} and obj2 != {}:
        return False
    elif obj1 == {} and obj2 == {}:
        return True

    key, val = obj1.popitem()
    try:
        if not diff_iteration(val, obj2.pop(key)):
            return False
    except KeyError:
        return False

    return diff_iteration(obj1, obj2)


def equal_spec(local_obj, server_obj):
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
    loc = local_obj.copy()
    serv = server_obj.copy()
    serv.pop('status', None)
    loc.pop('status', None)
    return diff_iteration(loc, serv)


