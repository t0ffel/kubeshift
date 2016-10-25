"""Base class for providers."""
import abc
import logging
import os

import requests
import six
import six.moves.urllib.parse as urlparse
import yaml

from kubeshift.config import Config
from kubeshift.constants import (DEFAULT_NAMESPACE,
                                 LOGGER_DEFAULT)
from kubeshift.exceptions import (KubeConnectionError, KubeRequestError,
                                  KubeShiftError)
from kubeshift.queries.kube_query import KubeQueryMixin
from kubeshift import validator

logger = logging.getLogger(LOGGER_DEFAULT)


def _format_url(urlbase, urlpath):
    if not urlbase.endswith('/'):
        urlbase += '/'
    if urlpath:
        urlpath = urlpath.lstrip('/')
    return urlparse.urljoin(urlbase, urlpath)


@six.add_metaclass(abc.ABCMeta)
class _ClientBase(object):
    """Base Client."""

    def __init__(self, config):
        """Establish session using configurations.

        :param Config config: An object of the .kube/config configuration
        """
        if isinstance(config, dict):
            config = Config(config)
        # assume type is string as the previous handled input
        # as a dict, so the only remaining option when not
        # an instance of Config is a file location.
        if not isinstance(config, Config):
            config = Config.from_file(config)
        self.kubeconfig = config

        # Check the API url
        self.base_url = self.kubeconfig.cluster.get('server',
                                                    'http://localhost:8080')
        validator.check_url(self.base_url)

        # Initialize the connection using all the .kube/config credentials
        self.session = self._connection()

        # Test the connection before proceeding
        self._test_connection(self.base_url + '/api/')

        self.api_resources = {}
        # Load API Resources
        self._load_resources('api/v1/', 'v1')
        self._load_group_resources('apis/')

    def _get_groups(self, url):
        """Get the groups of APIs available."""
        data = self.request('get', url)
        if not data:
            return []

        groups = []
        for group in data.get('groups', []):
            for ver in group.get('versions', []):
                if ver.get('groupVersion'):
                    groups.append(ver.get('groupVersion'))
        return groups

    def _get_resources(self, url):
        """
        Get the resources available to the API.

        This is a list of all available API calls that can be made to the API.
        """
        data = self.request('get', url)
        return data.get('resources', []) if data else []

    def _add_resources(self, base_url, version):
        self.api_resources.setdefault(version, {})

        for res in self._get_resources(base_url) or []:
            if '/' in res['name']:
                continue
            ep = res['name']
            if res['namespaced']:
                ep = 'namespaces/{namespace}/' + ep
            self.api_resources[version][res['kind']] = _format_url(base_url,
                                                                   ep)

    def _load_resources(self, resource_path, version):
        # Gather what end-points we will be using
        self._add_resources(_format_url(self.base_url, resource_path), version)

    def _load_group_resources(self, group_path):
        # Gather what API groups are available
        base_res_api = _format_url(self.base_url, group_path)

        # Gather the group names from which resource names will be derived
        for group in self._get_groups(base_res_api):
            self._add_resources(_format_url(base_res_api, group), group)

    def _test_connection(self, url):
        """Provide way to validate connection is viable."""
        self.request('get', url)
        logger.debug('Connection successfully tested on URL %s' % url)

    def _connection(self):
        """
        Initialize the required requests session.

        Sets certs / token / authentication in order to communicate with the
        API.
        """
        connection = requests.Session()

        session_opts = self.kubeconfig.format_session()

        # Check to see if verification has been disabled, if it has
        # disable tls-verification
        if not session_opts['verify']:
            # Disable the 'InsecureRequestWarning' notifications.
            # As per: https://github.com/kennethreitz/requests/issues/2214
            # Instead make a large one-time noticable warning instead
            requests.packages.urllib3.disable_warnings()
            logger.warning('CAUTION: TLS verification has been DISABLED')
        else:
            logger.debug('Verification will be required for all API calls')

        for opt in session_opts:
            if opt:
                setattr(connection, opt, session_opts[opt])

        return connection

    def _generate_url(self, api_version, kind, namespace=None, name=None,
                      params=None):
        """
        Generate the required URL using API resources.

        Args:
            api_version (str): version of API to use
            kind (str): the object type of API to use
            namespace (str): k8s namespace
            name (str): Name of the object being passed
            params (arr): Extra params passed such as timeout=300

        Returns:
            url (str): The URL to be used / artifact URL
        """
        url = self.api_resources.get(api_version, {}).get(kind)
        if not url:
            raise KubeShiftError(
                'No API matching version={} kind={}'.format(api_version, kind))

        url = url.replace('{namespace}', namespace or '')

        if name:
            url = _format_url(url, name)

        if params:
            url = url + '?{}'.format(urlparse.urlencode(params))

        return url

    def request(self, method, url, data=None, headers=None):
        """
        Complete the request to the API and fails if the status_code is != 200/201.

        :param str method: put/get/post/patch
        :param str url: url of the api call
        :param dict data: object of the data that is being passed
        (will be converted to json)
        :param dict headers: request header
        """
        status_code = None
        return_data = None

        logger.debug("Request: {0}".format(self._to_curl(method, url,
                                                         headers)))
        logger.debug("Request body: {0}".format(data))
        try:
            res = self.session.request(method, url, headers=headers, json=data)
            status_code = res.status_code
            logger.debug("Response headers: {0}".format(res.headers))
            # if res.ok and res.text:
            return_data = res.json()
            logger.debug("Response data: {0}".format(return_data))
        except requests.exceptions.SSLError:
            raise KubeConnectionError('SSL/TLS ERROR: invalid certificate')
        except requests.exceptions.ConnectTimeout:
            raise KubeConnectionError('Timeout when connecting to  %s' % url)
        except requests.exceptions.ReadTimeout:
            raise KubeConnectionError('Timeout when reading from %s' % url)
        except requests.exceptions.ConnectionError:
            raise KubeConnectionError('Refused connection to %s' % url)

        # 200 = OK
        # 201 = PENDING
        # 409 = Already Exists
        # EVERYTHING ELSE == FAIL
        if status_code == 409 and method == 'post':
            return return_data
        elif status_code == 404 and method == 'delete':
            return return_data
        elif status_code is not 200 and status_code is not 201:
            raise KubeRequestError('Error from server: %s; For request: %s'
                                   % (return_data['message'], self._to_curl(
                                      method, url, headers)))
        return return_data

    def _to_curl(self, method, url, hdrs):
        if hdrs:
            hdr_arr = ['-H "' + k + ': ' + v +
                       '"' for k, v in hdrs.iteritems()]
            return "curl -k -v -X%s %s %s" % (method.upper(),
                                              ' '.join(hdr_arr), url)
        return "curl -k -v -X%s %s" % (method.upper(), url)


class KubeBase(_ClientBase, KubeQueryMixin):
    """Provide common base for each provider.

    The role of Kube Base is to parse the Kube Config file and create an
    understandable API as well as initiation of connection to
    Kubernetes-based APIs (OpenShift/Kubernetes).
    """

    def _by_file(self, filepath, func):
        if not os.path.isfile(filepath):
            raise KubeShiftError('File not found: %s' % filepath)

        with open(filepath, 'r') as fd:
            resources = yaml.safe_load_all(fd.read())

        results = []
        for res in resources:
            results.append(func(res))

        return results

    def create(self, obj, namespace=DEFAULT_NAMESPACE):
        """Create an object from the Kubernetes cluster."""
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj, namespace)
        url = self._generate_url(apiver, kind, namespace)

        resp = self.request('post', url, data=obj)

#        logger.info('%s `%s` successfully created', kind.capitalize(), name)

        return resp

    def create_by_file(self, filepath):
        """Create resource by file.

        :params str filepath: file location
        :returns: created resource(s)
        :rtype: list
        :raises kubeshift.exceptions.KubeShiftError: if file not found
        """
        return self._by_file(filepath, self.create)

    def delete(self, obj, namespace=DEFAULT_NAMESPACE):
        """Delete an object from the Kubernetes cluster.

        .. note::

            Replication controllers must scale to 0 in order to delete pods.
            Kubernetes 1.3 will implement server-side cascading deletion, but
            until then, it's mandatory to scale to 0
            https://github.com/kubernetes/kubernetes/blob/master/docs/proposals/garbage-collection.md

        :param dict obj: Object of the artifact being modified
        :param str namesapce: Namespace of the kubernetes cluster to be used
        """
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj, namespace)
        url = self._generate_url(apiver, kind, namespace, name)

        if kind in ['ReplicationController']:
            self.scale(obj, namespace)
        resp = self.request('delete', url)

        logger.info('%s `%s` successfully deleted', kind.capitalize(), name)

        return resp

    def _update(self, obj):
        """Check the difference and object in the Kubernetes cluster."""
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj)
        query_name = kind.lower() + 's'
        query = getattr(self, query_name)(namespace=namespace)
        server_obj = query.by_name(name)
        patch = validator.form_patch(obj, server_obj)

        if patch == {}:
            logger.info(
                "{0} `{1}` matches what was requested".format(kind, name))
            result = {
                'response': server_obj,
                'changed': False
            }
#        logger.debug("resp in create is {0}".format(resp))
        else:
            logger.info(
                "Patch constructed: {0}".format(patch))
            result = {
                'response': self.modify(obj, patch),
                'changed': True
            }

        return result

    def ensure_present(self, obj):
        """Create or update an object from the Kubernetes cluster."""
        apiver, kind, name = validator.validate(obj)
        resp = self.create(obj)
        logger.debug("resp in create is {0}".format(resp))

        if resp.get('code', None) == 409:
            logger.info('%s `%s` Object with same name already exists', kind, name)
            result = self._update(obj)
        else:
            result = {
            'response': resp,
            'changed': True }
            logger.info('%s `%s` successfully created', kind, name)

        return result

    def ensure_absent(self, obj):
        """Ensure that object  is absent from the Kubernetes cluster.

        :param dict obj: Object of the artifact being modified
        """
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj)
        url = self._generate_url(apiver, kind, namespace, name)

        resp = self.request('delete', url)

        result = {'response': resp}
        if resp.get('code', None) == 404:
            result['changed'] = False
            logger.info('%s `%s` already absent', kind, name)
        else:
            result['changed'] = True
            logger.info('%s `%s` successfully deleted', kind, name)

        return result

    def delete_by_file(self, filepath):
        """Delete resource by file.

        :params str filepath: file location
        :returns: deleted resource(s)
        :rtype: list
        :raises kubeshift.exceptions.KubeShiftError: if file not found
        """
        return self._by_file(filepath, self.delete)

    def replace(self, obj, namespace=DEFAULT_NAMESPACE):
        """Replace a resource on the Kubernetes cluster."""
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj, namespace)
        url = self._generate_url(apiver, kind, namespace, name)

        resp = self.request('put', url, data=obj)

        logger.info('%s `%s` successfully replaced', kind.capitalize(), name)

        return resp

    def replace_by_file(self, filepath):
        """Replace resource by file.

        :params str filepath: file location
        :returns: replaced resource(s)
        :rtype: list
        :raises kubeshift.exceptions.KubeShiftError: if file not found
        """
        return self._by_file(filepath, self.replace)

    def modify(self, obj, partial, namespace=DEFAULT_NAMESPACE):
        """Modify a resource.

        The partial object provided will be strategically merged with the existing
        resource content. The top level meta data is required to enable modifying
        the correct resource instance.

        :param dict partial: changes to be applied to existing resource content
        :param str namespace: object name and auth scope, such as for teams and projects
        """
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj)
        url = self._generate_url(apiver, kind, namespace, name)

        headers = {'Content-Type': 'application/strategic-merge-patch+json'}
        resp = self.request('patch', url, data=partial, headers=headers)

        logger.info('%s `%s` successfully modified', kind.capitalize(), name)

        return resp

    def modify_by_file(self, filepath):
        """Modify resource by file.

        :params str filepath: file location
        :returns: modified resource(s)
        :rtype: list
        :raises kubeshift.exceptions.KubeShiftError: if file not found
        """
        return self._by_file(filepath, self.modify)

    def scale(self, obj, namespace=DEFAULT_NAMESPACE, replicas=0):
        """Scale replicas up or down.

        By default we scale back down to 0. This function takes an object and scales said
        object down to a specified value on the Kubernetes cluster

        :param dict obj: Object of the artifact being modified
        :param str namesapce: Namespace of the kubernetes cluster to be used
        :param int replicas: Default 0, size of the amount of replicas to scale
        """
        apiver, kind, name = validator.validate(obj)
        namespace = validator.check_namespace(obj, namespace)
        url = self._generate_url(apiver, kind, namespace, name)

        headers = {'Content-Type': 'application/json-patch+json'}
        patch = [{'op': 'replace',
                  'path': '/spec/replicas',
                  'value': replicas}]
        self.request('patch', url, data=patch, headers=headers)

        logger.info('`%s` successfully scaled to %s', name, replicas)
