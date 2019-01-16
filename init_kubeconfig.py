#!/usr/bin/env python3

import os
import sys
import json
import base64
import yaml
import argparse


def read_base64(filename):
    return base64.b64encode(open(filename, 'rb').read()).decode('utf-8')


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', help='Path to PKI folder', default='/etc/kubernetes/ssl', metavar='workdir', required=False)
    parser.add_argument('--apiserver', help='IP address of API server of worker node', metavar='ip', required=True, action='append')
    parser.add_argument('node', help='hostname of worker node', metavar='worker', nargs='+')
    args = parser.parse_args()

    workdir = args.workdir
    apiserver = args.apiserver
    nodes = args.node

    kc = KubeConfig(workdir, apiserver)

    kc.save_config('kube-proxy', username='system:kube-proxy')
    kc.save_config('kube-controller-manager', username='system:kube-controller-manager')
    kc.save_config('kube-scheduler', username='system:kube-scheduler')


    for node in nodes:
        username = f'system:node:{node}'
        kc.save_config(node, username=username)



if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        exit(1)
