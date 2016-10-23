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
                return self._process_template(apiver, kind, action, obj, namespace)
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

    def create_or_update(self, obj):
        """Create or update an object from the Kubernetes cluster."""
        resp = super(OpenshiftClient, self).create(obj)
        logger.debug("resp in create is {0}".format(resp))

        if resp['code'] == 409:
            resp = self._update(obj)

        return resp

    def _update(self, obj):
        """Check the difference and object in the Kubernetes cluster."""
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj, None)
        url = self._generate_url(apiver, kind, namespace)
        query_name = kind.lower() + 's'
        query = getattr(self, query_name)()
        server_obj = query.by_name(name)
        patch = validator.form_patch(obj, server_obj)
#        import pdb; pdb.set_trace()

#        resp = self.request('get', url, data=obj)
        if patch == {}:
            logger.info("The `{0}` named `{1}` already exists".format(kind, name))
            resp = {
            'resource': server_obj,
            'changed': False
            }
#        logger.debug("resp in create is {0}".format(resp))
        else:
            resp = {
            'resource': self.modify(patch),
            'changed': False
            }

        return resp
