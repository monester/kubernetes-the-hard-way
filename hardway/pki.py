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
        ca, ca_key = self.gen_cert('ca', command=['cfssl', 'gencert', '-initca'], **kwargs)
        self.ca = [f'-ca={ca}', f'-ca-key={ca_key}']
