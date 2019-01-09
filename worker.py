#!/usr/bin/env python

from subprocess import check_call
import os
import sys


check_call(['apt', 'install', '-y', 'socat', 'conntrack', 'ipset'])

files = [
    'https://github.com/containernetworking/plugins/releases/download/v0.7.4/cni-plugins-amd64-v0.7.4.tgz',
    'https://storage.googleapis.com/kubernetes-release/release/v1.13.1/bin/linux/amd64/kubectl',
    'https://storage.googleapis.com/kubernetes-release/release/v1.13.1/bin/linux/amd64/kube-proxy',
    'https://storage.googleapis.com/kubernetes-release/release/v1.13.1/bin/linux/amd64/kubelet',
]

check_call(['wget', '-q', '--show-progress', '--https-only', '--timestamping', *files])

for i in ['kubectl', 'kube-proxy', 'kubelet']:
    os.chmod(i, 0o755)
    os.rename(i, f'/usr/local/bin/{i}')

for dirname in ['/opt', '/opt/cni', '/opt/cni/bin']:
    if not os.path.exists(dirname):
        os.mkdir(dirname)

check_call(['tar', '-xvf', 'cni-plugins-amd64-v0.7.4.tgz', '-C', '/opt/cni/bin/'])
