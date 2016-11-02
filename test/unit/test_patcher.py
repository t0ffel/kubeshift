import unittest

from mock import patch

from kubeshift.exceptions import KubeShiftError
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

    def test_eq_el_in_list(self):
        src = {'labels': [{'blah': 'val'}]}
        dst = {'labels': [{'blah2': 'val2'}]}
        patch('patcher.patch_iteration', return_value={})
        patch_ = patcher.eq_elem_in_list(src, {})
        self.assertEqual(patch_, src)
