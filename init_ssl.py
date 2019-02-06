#!/usr/bin/env python3

import argparse
import sys
from subprocess import Popen, PIPE
import json
import os

from hardway.pki import PKI


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', help='Path to PKI folder', default='/etc/kubernetes/ssl', metavar='workdir', required=False)
    parser.add_argument('--apiserver', help='IP address of API server of worker node', metavar='ip', required=True, action='append')
    parser.add_argument('node', help='hostname of worker node', metavar='worker', nargs='+')
    args = parser.parse_args()

    workdir = args.workdir
    apiserver = args.apiserver
    nodes = args.node

    if not os.path.exists(workdir):
        os.mkdir(workdir)

    pki = PKI(workdir)

    # generate ca
    pki.init_ca()

    # generate admin user
    pki.gen_cert('admin', o='system:masters', ou='Kubernetes Admin')

    for node in nodes:
        # for cert auth
        pki.gen_cert(f'{node}', cn=f'system:node:{node}', o='system:nodes', ou='Kubernetes Nodes')

        # for serving on https
        pki.gen_cert(f'https-{node}', cn=node, ou=f'Kubernetes Node {node}')

    pki.gen_cert('kube-controller-manager', cn='system:kube-controller-manager', o='system:kube-controller-manager', ou='Kubernetes Controller')

    # Kube proxy
    pki.gen_cert('kube-proxy', cn='system:kube-proxy', o='system:node-proxier', ou='Kubernetes Proxy')

    # Kube scheduler
    pki.gen_cert('kube-scheduler', cn='system:kube-scheduler', o='system:kube-scheduler', ou='Kubernetes Scheduler')

    # https certificate for api server
    # 10.0.0.1 - first ip in --service-cluster-ip-range
    pki.gen_cert('kubernetes', cn='kubernetes', hostname=['127.0.0.1', '10.0.0.1', 'kubernetes.default', *apiserver])

    # Service account for what?
    pki.gen_cert('service-account', cn='service-accounts')


# instances = ['test2-worker01', 'test2-worker02']
# main('/tmp', instances)

if __name__ == '__main__':
    main()
