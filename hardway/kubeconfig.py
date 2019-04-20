import os
import re
import yaml
import base64


def read_base64(path):
    return base64.b64encode(open(path, 'rb').read()).decode('utf-8')


class KubeConfig:
    def __init__(self, workdir, apiserver):
        ca_path = os.path.join(workdir, 'ca.pem')

        self.workdir = workdir
        self.apiserver = apiserver[0]
        self.ca = read_base64(ca_path)

    def save_config(self, name, cert_name=None, username='user'):
        cert_name = cert_name or name
        assert isinstance(name, str) and name != '', 'Name should be valid non empty string'

        cert_path = os.path.join(self.workdir, f'{cert_name}.pem')
        key_path = os.path.join(self.workdir, f'{cert_name}-key.pem')
        config_path = os.path.join(self.workdir, f'{name}.kubeconfig')

        cert = read_base64(cert_path)
        key = read_base64(key_path)

        config = {
            'apiVersion': 'v1',
            'kind': 'Config',
            'preferences': {},
            'clusters': [{
                'name': 'kubernetes',
                'cluster': {
                    'certificate-authority-data': self.ca,
                    'server': self.apiserver,
                },
            }],
            'users': [{
                'name': username,
                'user': {
                    'client-certificate-data': cert,
                    'client-key-data': key,
                },
            }],
            'contexts': [{
                'name': 'default',
                'context': {
                    'cluster': 'kubernetes',
                    'user': username,
                },
            }],
            'current-context': 'default',
        }

        with open(config_path, 'w') as f:
            yaml.safe_dump(config, f)


class KubeConfigs:
    def __init__(self, workdir, names):
        self.workdir = workdir
        self.kubeconfigs = {}
        self.load()

    def load(self):
        """Find all kubeconfig files in directory with certs"""
        for filename in os.listdir(self.workdir):
            regex = re.match(r'(.*)\.kubeconfig', filename)
            if regex:
                name = regex.groups()
                self.kubeconfigs[name] = os.path.join(self.workdir, filename)

    def __getitem__(self, name):
        return self.kubeconfigs[name]
