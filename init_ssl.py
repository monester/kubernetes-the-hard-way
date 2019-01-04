#!/usr/bin/env python3

import argparse
import sys
from subprocess import Popen, PIPE
import json
import os


PKI_CONFIG = {
    "signing": {
        "default": {"expiry":"8760h"},
        "profiles": {"kubernetes": {
            "usages": ["signing", "key encipherment", "server auth", "client auth"], "expiry":"8760h"
        }}
    }
}



class PKI:
    def __init__(self, workdir):
        self.workdir = workdir
        self.ca = []

        self.config_path = os.path.join(workdir, "ca-config.json")
        self.gen_config()

    def gen_config(self):
        json.dump(PKI_CONFIG, open(self.config_path, 'w'), indent=4)


    def gencsr(self, cert_name, cn=None, o=None, ou=None):
        csr_path = os.path.join(self.workdir, f'{cert_name}-csr.json')
        data = {
            "key": {"algo": "rsa","size": 2048},
            "names": [{
                "C": "NL",
                "L": "Amsterdam",
                "O": o or "Kubernetes",
                "OU": ou or "Kubernetes The Hard Way"
            }]
        }

        if cn:
            data['CN'] = cn

        return json.dumps(data, indent=4)

    def gen_cert(self, cert_name, command=None, csr=None, hostname=None, **kwargs):
        workdir = self.workdir

        csr = csr or self.gencsr(cert_name, **kwargs)

        csr_path = os.path.join(workdir, f'{cert_name}-csr.json')
        cert_path = os.path.join(workdir, f'{cert_name}.pem')
        cert_key = os.path.join(workdir, f'{cert_name}-key.pem')

        if os.path.exists(cert_path) and os.path.exists(cert_key):
            print(f'{cert_path} and {cert_key} already exists')
        else:
            command = command or ['cfssl', 'gencert', '-profile=kubernetes', *self.ca, f'-config={self.config_path}']

            if hostname:
                command.append('-hostname=%s' % ','.join(hostname))

            process = Popen([*command, '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=workdir)
            output, err = process.communicate(csr.encode('utf-8'))

            if process.returncode != 0:
                print(err, file=sys.stderr)
                exit(1)

            cert = json.loads(output)

            with open(cert_path, 'w') as f:
                f.write(cert['cert'])

            with open(cert_key, 'w') as f:
                f.write(cert['key'])

        return [cert_path, cert_key]

    def init_ca(self, **kwargs):
        csr = self.gencsr('ca', **kwargs)
        ca, ca_key = self.gen_cert('ca', command=['cfssl', 'gencert', '-initca'], csr=csr)
        self.ca = [f'-ca={ca}', f'-ca-key={ca_key}']



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
    pki.gen_cert('admin', o="system:masters", ou="Kubernetes Admin")

    for instance in nodes:
        # for cert auth
        pki.gen_cert(f'{instance}', cn=f"system:node:{instance}", o="system:nodes", ou="Kubernetes Nodes")

        # for serving on https
        pki.gen_cert(f'https-{instance}', cn=f"{instance}", ou=f"Kubernetes Node {instance}")

    pki.gen_cert('kube-controller-manager', cn="system:kube-controller-manager", o="system:kube-controller-manager", ou="Kubernetes Controller")

    # Kube proxy
    pki.gen_cert('kube-proxy', cn="system:kube-proxy", o="system:node-proxier", ou="Kubernetes Proxy")

    # Kube scheduler
    pki.gen_cert('kube-scheduler', cn="system:kube-scheduler", o="system:kube-scheduler", ou="Kubernetes Scheduler")

    # https certificate for api server
    # 10.0.0.1 - first ip in --service-cluster-ip-range
    pki.gen_cert('kubernetes', cn="kubernetes", hostname=['127.0.0.1', '10.0.0.1', 'kubernetes.default', *apiserver])

    # Service account for what?
    pki.gen_cert('service-account', cn='service-accounts')


# instances = ['test2-worker01', 'test2-worker02']
# main('/tmp', instances)

if __name__ == '__main__':
    main()
