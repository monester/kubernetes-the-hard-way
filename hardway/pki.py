import os

PKI_CONFIG = {
    "signing": {
        "default": {"expiry":"8760h"},
        "profiles": {"kubernetes": {
            "usages": ["signing", "key encipherment", "server auth", "client auth"], "expiry":"8760h"
        }}
    }
}


class Cert:
    def __init__(self, name, cert_path, key_path, cert=None, key=None, **kwargs):
        self.name = name
        self.pem_path = cert_path
        self.key_path = key_path

        if cert and key:
            open(cert_path, 'w').write(cert)
            open(key_path, 'w').write(key)
        else:
            cert = open(cert_path).read(cert)
            key = open(key_path).read(key)

        self.pem = cert
        self.key = key


class PKI:
    def __init__(self, workdir):
        self.workdir = workdir
        self.ca = []

        self.config_path = os.path.join(workdir, "ca-config.json")
        self.certs = {}
        self.gen_config()

    def gen_config(self):
        """Create default settings for cfssl"""
        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir)
        json.dump(PKI_CONFIG, open(self.config_path, 'w'), indent=4)

    def gencsr(self, cert_name, cn=None, o=None, ou=None):
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

    def get_cert(self, cert_name, command=None, csr=None, hostname=None, **kwargs):
        if cert_name in self.certs:
            return self.certs[cert_name]

        csr = csr or self.gencsr(cert_name, **kwargs)
        cert_path = os.path.join(self.workdir, f'{cert_name}.pem')
        key_path = os.path.join(self.workdir, f'{cert_name}-key.pem')

        if os.path.exists(cert_path) and os.path.exists(key_path):
            print(f'{cert_path} and {cert_key} already exists. Loading existing key.')
            cert = Cert(name=cert_name, cert_path=cert_path, key_path=key_path)

        else:
            if cert_name == 'ca':
                command = ['cfssl', 'gencert', '-initca']
            else:

            if hostname:
                command.append('-hostname=%s' % ','.join(hostname))

            process = Popen([*command, '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=self.workdir)
            output, err = process.communicate(csr.encode('utf-8'))

            if process.returncode != 0:
                print(err, file=sys.stderr)
                exit(1)

            cert = Cert(name=cert_name, cert_path=cert_path, key_path=key_path, **json.loads(output))

        return self.certs[cert_name] = cert

    @property
    def ca(self):
        return self.get_cert('ca')
