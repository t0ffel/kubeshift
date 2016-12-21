import unittest

import mock

from kubeshift.exceptions import KubePatchError
from kubeshift import comparator


class TestComparator(unittest.TestCase):

    @mock.patch('kubeshift.comparator.diff_iteration')
    def test_eq_el_in_list_false(self, patch_iter_mock):
        lst = [{'labels': [{'blah': 'val'}]}]
        patch_iter_mock.return_value = False
        res = comparator.del_eq_elem_in_list('a', lst)
        patch_iter_mock.assert_called_once()
        self.assertEqual(res, False)

    @mock.patch('kubeshift.comparator.diff_iteration')
    def test_eq_el_in_list_true(self, patch_iter_mock):
        lst = [{'blah': 'val'}]
        patch_iter_mock.return_value = True
        res = comparator.del_eq_elem_in_list({'blah': 'val'}, lst)
        patch_iter_mock.assert_called_once()
        self.assertEqual(res, True)
        self.assertEqual(lst, [])

    @mock.patch('kubeshift.comparator.del_eq_elem_in_list')
    def test_diff_list_iter_different(self, patch_del_item):
        lst1 = [{'blah1': 'val'}]
        lst2 = [{'blah2': 'val'}]
        patch_del_item.return_value = False
        res = comparator._diff_dict_list_iter(lst1, lst2)
        patch_del_item.assert_called_once()
        self.assertEqual(res, False)

    @mock.patch('kubeshift.comparator.del_eq_elem_in_list')
    def test_diff_list_iter_non_empty_2nd(self, eq_elem_mock):
        lst1 = []
        lst2 = [{'blah2': 'val'}]
        res = comparator._diff_dict_list_iter(lst1, lst2)
        self.assertEqual(res, False)
        self.assertFalse(eq_elem_mock.called)

    @mock.patch('kubeshift.comparator.del_eq_elem_in_list')
    def test_diff_list_iter_empty_lists(self, eq_elem_mock):
        lst1 = []
        lst2 = []
        res = comparator._diff_dict_list_iter(lst1, lst2)
        self.assertEqual(res, True)
        self.assertFalse(eq_elem_mock.called)

    @mock.patch('kubeshift.comparator.del_eq_elem_in_list')
    def test_diff_list_iter_only_1st(self, del_eq_elem_mock):
        lst1 = [{'blah2': 'val'}]
        lst2 = []
        del_eq_elem_mock.return_value = False
        res = comparator._diff_dict_list_iter(lst1, lst2)
        self.assertEqual(res, False)
        del_eq_elem_mock.assert_called_once()

    def test_diff_list_2els(self):
        lst1 = [{'blah2': 'val'},{'blah1':'val1'}]
        lst2 = [{'blah2': 'val'},{'blah1':'val1'}]
        res = comparator.diff_list(lst1, lst2)
        self.assertEqual(res, True)

    @mock.patch('kubeshift.comparator._diff_dict_list_iter')
    def test_diff_list_empty(self, list_iter_mock):
        lst1 = []
        lst2 = ['blah2', 'val']
        res = comparator.diff_list(lst1, lst2)
        self.assertEqual(res, False)
        self.assertFalse(list_iter_mock.called)

    @mock.patch('kubeshift.comparator._diff_dict_list_iter')
    def test_diff_list_same(self, list_iter_mock):
        lst1 = ['blah2', 'val']
        lst2 = ['blah2', 'val']
        res = comparator.diff_list(lst1, lst2)
        self.assertEqual(res, True)
        self.assertFalse(list_iter_mock.called)

    def test_diff_iteration_list_dict(self):
        lst1 = ['blah2', 'val']
        obj2 = {'blah2': 'val'}
        with self.assertRaises(KubePatchError) as cm:
            patch_ = comparator.diff_iteration(lst1, obj2)
        err = "Trying to compare {'blah2': 'val'} to list"
        self.assertEqual(cm.exception.message, err)

    @mock.patch('kubeshift.comparator.diff_list')
    def test_diff_iteration_lists(self, diff_list_mock):
        lst1 = ['blah1', 'val']
        lst2 = ['blah2', 'val']
        diff_list_mock.return_value = False
        res = comparator.diff_iteration(lst1, lst2)
        diff_list_mock.assert_called_once_with(lst1, lst2)
        self.assertEqual(res, False)

    def test_diff_iteration_val_list(self):
        lst1 = 'str'
        lst2 = ['blah2', 'val']
        with self.assertRaises(KubePatchError) as cm:
            patch_ = comparator.diff_iteration(lst1, lst2)
        err = "Trying to compare ['blah2', 'val'] to value"
        self.assertEqual(cm.exception.message, err)

    def test_diff_iteration_val_dict(self):
        val1 = 'str'
        obj2 = {'blah2': 'val'}
        with self.assertRaises(KubePatchError) as cm:
            patch_ = comparator.diff_iteration(val1, obj2)
        err = "Trying to compare {'blah2': 'val'} to value"
        self.assertEqual(cm.exception.message, err)

    def test_diff_iteration_different_types(self):
        val1 = 'str'
        val2 = 11
        res = comparator.diff_iteration(val1, val2)
        self.assertEqual(res, False)

    def test_diff_iteration_eq_vals(self):
        val1 = 11
        val2 = 11
        res = comparator.diff_iteration(val1, val2)
        self.assertEqual(res, True)

    def test_diff_iteration_simple_dicts(self):
        obj1 = {'blah1': 'val'}
        obj2 = {'blah2': 'val'}
        res = comparator.diff_iteration(obj1, obj2)
        self.assertEqual(res, False)

    def test_diff_iteration_dicts_simple_same_key(self):
        obj1 = {'blah1': 'val'}
        obj2 = {'blah1': 'val2'}
        res = comparator.diff_iteration(obj1, obj2)
        self.assertEqual(res, False)

    def test_diff_iteration_empty_dict(self):
        obj1 = {}
        obj2 = {'blah2': 'val'}
        res = comparator.diff_iteration(obj1, obj2)
        self.assertEqual(res, False)

    def test_diff_iteration_dicts_same_key(self):
        obj1 = {'blah1': 'val', 'blah2': 'val2'}
        obj2 = {'blah1': 'val2', 'blah2': 'val3'}
        res = comparator.diff_iteration(obj1, obj2)
        self.assertEqual(res, False)

    @mock.patch('kubeshift.comparator.diff_iteration')
    def test_equal_spec_same_key(self, iteration_mock):
        obj1 = {'spec': 'val', 'status': 'val2'}
        obj2 = {'spec': 'val2', 'blah2': 'val3'}
        obj1_no_status = {'spec': 'val'}
        iteration_mock.return_value = False
        res = comparator.equal_spec(obj1, obj2)
        iteration_mock.assert_called_once_with(obj1_no_status, obj2)
        self.assertEqual(res, False)

    @mock.patch('kubeshift.comparator.diff_iteration')
    def test_equal_spec_new_key(self, iteration_mock):
        obj1 = {'spec': 'val', 'metadata': {'name': 'val2'}}
        obj2 = {'blah2': 'val3'}
        iteration_mock.return_value = False
        res = comparator.equal_spec(obj1, obj2)
        iteration_mock.assert_called_once_with(obj1, obj2)
        self.assertEqual(res, False)

