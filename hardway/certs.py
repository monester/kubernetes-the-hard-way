import re
from dataclasses import dataclass


def read_base64(filename):
    return base64.b64encode(open(filename, 'rb').read()).decode('utf-8')


class Cert:
    def __init__(self, workdir, cert, pki):
        self.pem = os.path.join(wordir, f'{cert}.pem')
        self.key = os.path.join(wordir, f'{cert}-key.pem')
        self.workdir = workdir
        self.pki = pki
        if os.path.exists(self.pem) and os.path.exists(self.key):
            self.pem_content = read_base64(self.pem)
            self.key_content = read_base64(self.key)

    def create_cert(self):
        self.pki.gen_cert()


class CA(Cert):
    def __init__(self, workdir):
        super().__init__(workdir, 'ca')



class Certs:
    def __init__(self, workdir, certs=None):
        certs = certs or []

        self.workdir = workdir
        self._certs = {}
        # todo: move pki to tmp
        self.pki = PKI(workdir)

        self._ca = CA(workdir, pki)

        for cert in certs:
            self._certs = Cert(workdir, cert)


    def load(self):
        """Find all certificate pairs pem and key"""
        certs = {}
        for filename in os.listdir(self.workdir):
            regex = re.match(r'(.*?)(-key.pem|.pem)', filename)
            if regex:
                name, ending = regex.groups()
                cert = certs.setdefault(name, Cert())
                if 'key' in ending:
                    cert.key = filename
                else:
                    cert.pem = filename

        for name, cert in sorted(certs.items(), key=lambda x: '0000' if x[0] == 'ca' else x[0]):
            if cert.pem and cert.key:
                print(f'Found {name} certificate in {self.workdir}')
                self[name] = cert
            else:
                print(f'Invalid {name} certificate in {self.workdir}. Missing {name}%s file' % ('.pem' if cert.key else '-key.pem'))


    def __setitem__(self, key, cert):
        assert isinstance(cert, Cert), 'should be Cert instance'

        if not cert.pem.startswith(self.workdir):
            cert.pem = os.path.join(self.workdir, os.path.basename(cert.pem))

        if not cert.key.startswith(self.workdir):
            cert.key = os.path.join(self.workdir, os.path.basename(cert.key))

        if key == 'ca':
            self._ca = cert

        self._certs[key] = cert

    def __getitem__(self, key):
        return self._certs[key]

    @property
    def ca(self):
        return self._ca
