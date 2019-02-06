#!/usr/bin/env python3

import os
import sys
import json
import base64
import yaml
import argparse

from hardway.kubeconfig import KubeConfig


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
