import os
import sys
import json
from subprocess import check_output, Popen, PIPE

PKI_CONFIG = {
    "signing": {
        "default": {"expiry": "8760h"},
        "profiles": {"kubernetes": {
            "usages": ["signing", "key encipherment", "server auth", "client auth"], "expiry": "8760h"
        }}
    }
}


class Cert:
    def __init__(self, workdir, name, cert=None, key=None, **kwargs):
        self.name = name

        self.pem_path = cert_path = os.path.join(workdir, f'{name}.pem')
        self.key_path = key_path = os.path.join(workdir, f'{name}-key.pem')

        if cert and key:
            open(cert_path, 'w').write(cert)
            open(key_path, 'w').write(key)
        else:
            cert = open(cert_path).read(cert)
            key = open(key_path).read(key)
            print(f'Loading existing key from {cert_path} and {key_path}')

        self.pem = cert
        self.key = key


class PKI:
    def __init__(self, workdir):
        self.workdir = workdir

        self.config_path = os.path.join(workdir, "ca-config.json")
        self.certs = {}
        self.gen_config()

        if os.path.exists(f'{workdir}/ca.pem'):
            self.ca = Cert(workdir, 'ca')
        else:
            self.ca = self.gen_ca()

    def gen_config(self):
        """Create default settings for cfssl"""
        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir)
        json.dump(PKI_CONFIG, open(self.config_path, 'w'), indent=4)

    def gen_ca(self):
        csr = self.gencsr(cn='Kubernetes')
        command = ['cfssl', 'gencert', '-initca', '-']
        process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=self.workdir)
        output, err = process.communicate(csr.encode('utf-8'))
        cert = Cert(workdir=self.workdir, name='ca', **json.loads(output))
        return cert

    @staticmethod
    def gencsr(cn=None, o=None, ou=None):
        data = {
            "key": {"algo": "rsa", "size": 2048},
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

    def gen_cert(self, cert_name, csr=None, hostname=None, **kwargs):
        csr = csr or self.gencsr(**kwargs)

        try:
            cert = Cert(workdir=self.workdir, name=cert_name)
        except FileNotFoundError:
            command = ['cfssl', 'gencert',
                       f'-ca={self.ca.pem_path}',
                       f'-ca-key={self.ca.key_path}',
                       f'-config={self.config_path}',
                       '-profile=kubernetes'
                       ]
            if hostname:
                command.append('-hostname=%s' % ','.join(hostname))

            process = Popen([*command, '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=self.workdir)
            output, err = process.communicate(csr.encode('utf-8'))

            if process.returncode != 0:
                print(err, file=sys.stderr)
                exit(1)

            cert = Cert(workdir=self.workdir, name=cert_name, **json.loads(output))

        return cert

    def __getitem__(self, item):
        try:
            return self.certs[item]
        except KeyError:
            self.certs[item] = self.gen_cert(item)
            return self.certs[item]
