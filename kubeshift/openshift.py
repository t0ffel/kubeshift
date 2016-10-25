"""Openshift Provider."""
import logging

import six

from kubeshift.base import KubeBase
from kubeshift.constants import (DEFAULT_NAMESPACE,
                                 LOGGER_DEFAULT)
from kubeshift.queries.shift_query import ShiftQueryMixin
from kubeshift import validator

logger = logging.getLogger(LOGGER_DEFAULT)


def template(action):
    """Handle template actions.

    .. py:decorator:: template

        Checks if the kind is 'template' and processes else default processing.
    """
    def decorator(func):
        @six.wraps(func)
        def handler(self, obj, namespace=None):
            apiver, kind, _ = validator.validate(obj)
            if kind == 'Template':
                return self._process_template(apiver, kind, action, obj,
                                              namespace)
            else:
                return func(self, obj, namespace)
        return handler
    return decorator


class OpenshiftClient(KubeBase, ShiftQueryMixin):
    """Openshift Provider client that provides access to APIs."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(OpenshiftClient, self).__init__(*args, **kwargs)

        # Load API Resources
        self._load_resources('oapi/v1/', 'v1')

    @template(action='post')
    def create(self, obj, namespace=DEFAULT_NAMESPACE):
        """Create an object from the Openshift cluster."""
        return super(OpenshiftClient, self).create(obj, namespace)

    @template(action='delete')
    def delete(self, obj, namespace=DEFAULT_NAMESPACE):
        """Delete an object from the Openshift cluster."""
        return super(OpenshiftClient, self).delete(obj, namespace)

    def _process_template(self, apiver, kind, method, obj, namespace):
        url = self._generate_url(apiver, kind, namespace)
        data = self.request('post', url, data=obj) or {}

        for o in data.get('objects', []):
            apiver, kind, name = validator.validate(o)
            object_url = self._generate_url(apiver, kind, namespace)
            self.request(method, object_url, data=o)
            logger.debug('%sd template object: %s', method, name)

        logger.debug('Processed template with %d objects successfully',
                     len(data.get('objects', [])))
        return data

    def ensure_present(self, obj):
        """Create or update an object from the Kubernetes cluster."""
        namespace = validator.check_namespace(obj)
        apiver, kind, name = validator.validate(obj)
        if kind != 'Namespace' and namespace:
            ns_obj = {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    'name': namespace
                }
            }
            super(OpenshiftClient, self).ensure_present(ns_obj)
        return super(OpenshiftClient, self).ensure_present(obj)

    def ensure_absent(self, obj):
        """Ensure that an object is removed from the Openshift cluster."""
        return super(OpenshiftClient, self).ensure_absent(obj)
