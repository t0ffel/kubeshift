import unittest

import mock

from kubeshift.exceptions import KubePatchError
from kubeshift import patcher


class TestPatcher(unittest.TestCase):

    def test_empty_metadata_patch(self):
        patch = patcher.metadata_patch({}, {})
        self.assertEqual(patch, {})

    def test_src_labels_metadata_patch(self):
        src = {'labels': [{'blah': 'val'}]}
        patch = patcher.metadata_patch(src, {})
        self.assertEqual(patch, src)

    def test_src_annotations_metadata_patch(self):
        src = {'annotations': [{'blah': 'val'}]}
        patch = patcher.metadata_patch(src, {})
        self.assertEqual(patch, src)

    def test_dst_labels_metadata_patch(self):
        dst = {'labels': [{'blah': 'val'}]}
        res = {'labels': 'null'}
        patch = patcher.metadata_patch({}, dst)
        self.assertEqual(patch, res)

    def test_dst_annotations_metadata_patch(self):
        dst = {'annotations': [{'blah': 'val'}]}
        res = {'annotations': 'null'}
        patch = patcher.metadata_patch({}, dst)
        self.assertEqual(patch, res)

    def test_merge_labels_metadata_patch(self):
        src = {'labels': [{'blah': 'val'}]}
        dst = {'labels': [{'blah2': 'val2'}]}
        patch = patcher.metadata_patch(src, {})
        self.assertEqual(patch, src)

    @mock.patch('kubeshift.patcher.patch_iteration')
    def test_eq_el_in_list_false(self, patch_iter_mock):
        lst = [{'labels': [{'blah': 'val'}]}]
        patch_iter_mock.return_value = {}
        patch_ = patcher.eq_elem_in_list('a', lst)
        patch_iter_mock.assert_called_once()
        self.assertEqual(patch_, True)

    @mock.patch('kubeshift.patcher.patch_iteration')
    def test_eq_el_in_list_true(self, patch_iter_mock):
        lst = [{'blah': 'val'}]
        patch_iter_mock.return_value = [{'blah': 'val'}]
        patch_ = patcher.eq_elem_in_list({'blah': 'val'}, lst)
        patch_iter_mock.assert_called_once()
        self.assertEqual(patch_, False)

    def test_patch_list_replace(self):
        lst1 = [{'blah1': 'val'}]
        lst2 = [{'blah2': 'val'}]
        patch_ = patcher.patch_list(lst1, lst2, 'replace')
        self.assertEqual(patch_, lst1)

    def test_patch_list_not_append(self):
        lst1 = [{'blah1': 'val'}]
        lst2 = [{'blah2': 'val'}]
        with self.assertRaises(KubePatchError) as cm:
            patch_ = patcher.patch_list(lst1, lst2, 'error')
        self.assertEqual(cm.exception.message,
                         'Error patching list in mode error')

    def test_patch_list_append_non_dicts(self):
        lst1 = ['blah1', 'val']
        lst2 = ['blah2', 'val']
        patch_ = sorted(patcher.patch_list(lst1, lst2, 'append'))
        res = sorted(['blah1', 'blah2', 'val'])
        self.assertEqual(patch_, res)

    @mock.patch('kubeshift.patcher.eq_elem_in_list')
    def test_patch_list_append_dicts(self, eq_elem_mock):
        lst1 = [{'blah1': 'val'}]
        lst2 = [{'blah2': 'val'}]
        eq_elem_mock.return_value = False
        patch_ = patcher.patch_list(lst1, lst2, 'append').sort()
        lst1.extend(lst2)
        res = lst1.sort()
        self.assertEqual(patch_, res)

    @mock.patch('kubeshift.patcher.eq_elem_in_list')
    def test_patch_list_append_dicts_2el(self, eq_elem_mock):
        lst1 = [{'blah2': 'val'}, {'blah1': 'val'}]
        lst2 = [{'blah2': 'val'}]
        eq_elem_mock.side_effect = [True, False]
        patch_ = patcher.patch_list(lst1, lst2, 'append').sort()
        lst1.extend(lst2)
        res = lst1.sort()
        self.assertEqual(patch_, res)

    def test_patch_list_append_empty(self):
        lst1 = []
        lst2 = ['blah2', 'val']
        patch_ = sorted(patcher.patch_list(lst1, lst2, 'append'))
        res = sorted(['blah2', 'val'])
        self.assertEqual(patch_, res)

    def test_patch_list_append_same(self):
        lst1 = ['blah2', 'val']
        lst2 = ['blah2', 'val']
        patch_ = patcher.patch_list(lst1, lst2, 'append')
        self.assertEqual(patch_, [])

    def test_patch_iteration_list_dict(self):
        lst1 = ['blah2', 'val']
        obj2 = {'blah2': 'val'}
        with self.assertRaises(KubePatchError) as cm:
            patch_ = patcher.patch_iteration(lst1, obj2, 'append')
        err = "Trying to compare {'blah2': 'val'} to list"
        self.assertEqual(cm.exception.message, err)

    @mock.patch('kubeshift.patcher.patch_list')
    def test_patch_iteration_lists(self, patch_list_mock):
        lst1 = ['blah1', 'val']
        lst2 = ['blah2', 'val']
        patch_list_mock.return_value = ['blah1', 'blah2', 'val']
        patch_ = patcher.patch_iteration(lst1, lst2, 'append')
        patch_list_mock.assert_called_once_with(lst1, lst2, 'append')

    def test_patch_iteration_val_list(self):
        lst1 = 'str'
        lst2 = ['blah2', 'val']
        with self.assertRaises(KubePatchError) as cm:
            patch_ = patcher.patch_iteration(lst1, lst2, 'append')
        err = "Trying to compare ['blah2', 'val'] to value"
        self.assertEqual(cm.exception.message, err)

    def test_patch_iteration_val_dict(self):
        val1 = 'str'
        obj2 = {'blah2': 'val'}
        with self.assertRaises(KubePatchError) as cm:
            patch_ = patcher.patch_iteration(val1, obj2, 'append')
        err = "Trying to compare {'blah2': 'val'} to value"
        self.assertEqual(cm.exception.message, err)

    def test_patch_iteration_val_list(self):
        val1 = 'str'
        val2 = 11
        patch_ = patcher.patch_iteration(val1, val2, 'append')
        self.assertEqual(patch_, val1)

    def test_patch_iteration_eq_val_list(self):
        val1 = 11
        val2 = 11
        patch_ = patcher.patch_iteration(val1, val2, 'append')
        self.assertEqual(patch_, None)

    def test_patch_iteration_dicts(self):
        obj1 = {'blah1': 'val'}
        obj2 = {'blah2': 'val'}
        patch_ = patcher.patch_iteration(obj1, obj2, 'append')
        self.assertEqual(patch_, obj1)

    def test_patch_iteration_dicts_same_key(self):
        obj1 = {'blah1': 'val'}
        obj2 = {'blah1': 'val2'}
        patch_ = patcher.patch_iteration(obj1, obj2, 'append')
        self.assertEqual(patch_, obj1)

    def test_patch_iteration_empty_dict(self):
        obj1 = {}
        obj2 = {'blah2': 'val'}
        patch_ = patcher.patch_iteration(obj1, obj2, 'append')
        self.assertEqual(patch_, None)

    def test_patch_iteration_dicts_same_key(self):
        obj1 = {'blah1': 'val', 'blah2': 'val2'}
        obj2 = {'blah1': 'val2', 'blah2': 'val3'}
        patch_ = patcher.patch_iteration(obj1, obj2, 'append')
        self.assertEqual(patch_, obj1)

    def test_form_patch_wrong_mode(self):
        obj1 = {'blah1': 'val', 'blah2': 'val2'}
        obj2 = {'blah1': 'val2', 'blah2': 'val3'}
        with self.assertRaises(KubePatchError) as cm:
            patch_ = patcher.form_patch(obj1, obj2, 'error')
        err = "Unrecognized patching mode 'error'"
        self.assertEqual(cm.exception.message, err)

    @mock.patch('kubeshift.patcher.patch_iteration')
    @mock.patch('kubeshift.patcher.metadata_patch')
    def test_form_patch_same_key(self, metadata_mock, iteration_mock):
        obj1 = {'spec': 'val', 'status': 'val2'}
        obj2 = {'spec': 'val2', 'blah2': 'val3'}
        metadata_mock.return_value = {}
        iteration_mock.return_value = 'val'
        patch_ = patcher.form_patch(obj1, obj2, 'append')
        metadata_mock.assert_called_once_with({}, {})
        iteration_mock.assert_called_once_with('val', 'val2', 'append')
        self.assertEqual(patch_, {'spec': 'val'})

    @mock.patch('kubeshift.patcher.patch_iteration')
    @mock.patch('kubeshift.patcher.metadata_patch')
    def test_form_patch_new_key(self, metadata_mock, iteration_mock):
        obj1 = {'spec': 'val', 'metadata': {'name': 'val2'}}
        obj2 = {'blah2': 'val3'}
        metadata_mock.return_value = {'name': 'val2'}
        iteration_mock.return_value = 'val'
        patch_ = patcher.form_patch(obj1, obj2, 'append')
        metadata_mock.assert_called_once_with({'name': 'val2'}, {})
        iteration_mock.assert_not_called()
        self.assertEqual(patch_, obj1)

    @mock.patch('kubeshift.patcher.patch_iteration')
    @mock.patch('kubeshift.patcher.metadata_patch')
    def test_form_patch_two_keys(self, metadata_mock, iteration_mock):
        obj1 = {'spec': 'val1', 'blah2': 'val2'}
        obj2 = {'spec': 'val3', 'blah2': 'val4'}
        metadata_mock.return_value = {}
        iteration_mock.side_effect = ['val2', 'val1']
        patch_ = patcher.form_patch(obj1, obj2, 'append')
        metadata_mock.assert_called_once_with({}, {})
        calls = [mock.call('val2', 'val4', 'append'),
                 mock.call('val1', 'val3', 'append')]
        iteration_mock.assert_has_calls(calls, any_order=True)
        self.assertEqual(patch_, obj1)
