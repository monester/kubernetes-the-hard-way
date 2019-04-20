#!/usr/bin/env python3

from textwrap import dedent
import argparse
import subprocess
import os
import base64
import yaml

from hardway.pki import PKI
# from hardway.kubeconfig import KubeConfigs

class Etcd:
    def __init__(self, name='etcd', advertise='127.0.0.1', listen='0.0.0.0', ca=None, cert=None):
        self.ca = ca
        self.cert = cert
        self.name = name

        proto = 'https' if cert else 'http'

        self.listen_client = f'{proto}://{listen}:2379'
        self.advertise = f'{proto}://{advertise}:2379'

    def cmd(self):
        image = 'quay.io/coreos/etcd:v3.2'
        env = [
            'ETCDCTL_API=3',
            f'ETCDCTL_ENDPOINTS={self.listen_client}',
            f'ETCDCTL_CACERT={self.ca.pem_path}',
            f'ETCDCTL_CERT={self.cert.pem_path}',
            f'ETCDCTL_KEY={self.cert.key_path}',
        ]
        command = [
            'etcd',
            '--client-cert-auth',
            f'--name={self.name}',
            f'--advertise-client-urls={self.advertise}',
            f'--listen-client-urls={self.listen_client}',
            f'--trusted-ca-file={self.ca.pem_path}',
            f'--cert-file={self.cert.pem_path}',
            f'--key-file={self.cert.key_path}',
        ]
        return image, env, command


class ControlPlane:
    def __init__(self, apiserver, workdir, certs):
        self.etcd_servers = '127.0.0.1'
        self.master = apiserver
        self.hyperkube = 'k8s.gcr.io/hyperkube:v1.13.1'
        self.workdir = workdir
        self.certs = certs

    def kube_apiserver(self):
        etcd_servers = f'https://{self.etcd_servers}:2379'
        env = []
        image = self.hyperkube
        command = [
            'kube-apiserver',

            # we should allow priviledged containers
            '--allow-privileged=true',

            # allow RBAC for services, SA, users
            # allow Node for kubelet authorization using SSL certificates
            '--authorization-mode=Node,RBAC',

            '--bind-address=0.0.0.0',

            # allow certificates with this root CA
            f'--client-ca-file={self.certs.ca.pem_path}',

            # Admission plugins to use (TODO: check what is required)
            '--enable-admission-plugins=%s' % ','.join([
                # default admission plugins
                'NamespaceLifecycle',
                'LimitRanger',
                'ServiceAccount',
                'Priority',
                'DefaultTolerationSeconds',
                'DefaultStorageClass',
                'PersistentVolumeClaimResize',
                'MutatingAdmissionWebhook',
                'ValidatingAdmissionWebhook',
                'ResourceQuota',
            ]),

            # connection to etcd info
            f'--etcd-cafile={self.certs.ca.pem_path}',
            f'--etcd-certfile={self.certs["kubernetes"].pem_path}',
            f'--etcd-keyfile={self.certs["kubernetes"].key_path}',
            f'--etcd-servers={etcd_servers}',

            # '--encryption-provider-config=VeRyBiGSeCrEt',

            # kubelet configuration
            f'--kubelet-certificate-authority={self.workdir}/ca.pem',
            f'--kubelet-client-certificate={self.workdir}/kubernetes.pem',
            f'--kubelet-client-key={self.workdir}/kubernetes-key.pem',
            '--kubelet-https=true',

            f'--service-account-key-file={self.workdir}/service-account-key.pem',
            f'--tls-cert-file={self.workdir}/kubernetes.pem',
            f'--tls-private-key-file={self.workdir}/kubernetes-key.pem',
            '--v 2',
        ]
        return image, env, command

    def kube_controller_manager(self):
        env = []
        image = self.hyperkube
        command = [
            'kube-controller-manager',
            f'--kubeconfig={self.workdir}/kube-controller-manager.kubeconfig',
            '--address=0.0.0.0',

            # whole subnet for all pods (kubelet --pod-cidr should be part of this subnet)
            '--cluster-cidr=10.200.0.0/16',
            '--cluster-name=kubernetes',

            '--leader-elect=true',

            # '--cluster-signing-cert-file={self.workdir}/ca.pem',
            # '--cluster-signing-key-file={self.workdir}/ca-key.pem',
            # '--client-ca-file={self.workdir}/ca.pem',
            f'--service-account-private-key-file={self.workdir}/service-account-key.pem',
            '--use-service-account-credentials=true',
            '--v 2',
        ]
        return image, env, command

    def kube_scheduller(self):
        env = []
        image = self.hyperkube
        command = [
            'kube-scheduler',
            # master connection details
            f'--kubeconfig={self.workdir}/kube-scheduler.kubeconfig',
            '--leader-elect=true',
            '--v 2',
        ]
        return image, env, command


def docker(service, image, env, command, workdir, debug, run):
    if debug:
        run_str = '# {service} #\ndocker run --rm --network=host --name {service} -ti {env} {volumes} {image} \\\n{command}\n\n'
    else:
        run_str = '# {service} #\ndocker run --restart=always --network=host --name {service} --detach {env} {volumes} {image} \\\n{command}\n\n'
    line = run_str.format(
        service=service,
        env=' '.join([f'-e{i}' for i in env]),
        volumes=f'-v{workdir}:{workdir}',
        image=image,
        command=' \\\n'.join(command),
    )
    print(line)
    if run:
        try:
            subprocess.check_call(['docker', 'rm', '--force', service])
        except subprocess.CalledProcessError:
            pass
        subprocess.check_call(line, shell=True)


def publish_secrets(certs):
    """Put certificates to the secrets"""
    config = dedent('''\
        apiVersion: v1
        kind: Secret
        metadata:
          name: mysecret
        type: Opaque
    ''')

    data = {}
    for cert in certs._certs.values():
        data[os.path.basename(cert.pem)] = base64.b64encode(open(cert.pem, 'rb').read()).decode('utf-8')
        data[os.path.basename(cert.key)] = base64.b64encode(open(cert.key, 'rb').read()).decode('utf-8')

    config += yaml.safe_dump({'data': data}, indent=2, default_flow_style=False)
    print(config)


# def kube(name, image, env, command, debug, run):
#     config = dedent(f'''\
#         ---
#         apiVersion: extensions/v1
#         kind: StatefulSet
#         metadata:
#           labels:
#             app: {name}
#           name: {name}
#         spec:
#           selector:
#             matchLabels:
#               app: {name}
#           strategy:
#             rollingUpdate:
#               maxUnavailable: 0
#             type: RollingUpdate
#           template:
#             metadata:
#               labels:
#                 app: {name}
#             spec:
#               initContainers:
#               - name: certficate-checker
#                 image: python:3.7
#                 env:
#                 - APP_NAME: {name}
#               containers:
#               - image: {image}
#                 name {name}
#     ''')
#     print(config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker', action='store_true', default=True)
    parser.add_argument('--kube', action='store_true', default=False)
    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument('--run', action='store_true', default=False)
    parser.add_argument('--service', default='all')
    parser.add_argument('--workdir', help='Path to PKI folder', default='/etc/kubernetes/ssl', metavar='workdir',
                        required=False)
    parser.add_argument('--apiserver', help='IP address of API server of worker node', metavar='ip',
                        default='127.0.0.1')
    parser.add_argument('node', help='hostname of worker node', metavar='worker', nargs='*')
    args = parser.parse_args()

    certs = PKI(args.workdir)
    # kube_configs = KubeConfigs(args.workdir)

    cp = ControlPlane(args.apiserver, args.workdir, certs)
    etcd = Etcd(ca=certs.ca, cert=certs['kubernetes'])

    from functools import partial

    if args.docker:
        wrapper = partial(docker, workdir=args.workdir, debug=args.debug, run=args.run)
    elif args.kube:
        wrapper = None

    service = args.service
    debug = args.debug
    run = args.run

    # if args.kube and not args.docker:
    #     publish_secrets(certs)

    if service in ['etcd', 'all']:
        wrapper('etcd', *etcd.cmd())

    if service in ['apiserver', 'all']:
        wrapper('kube-apiserver', *cp.kube_apiserver())

    if service in ['scheduler', 'all']:
        wrapper('kube-scheduler', *cp.kube_scheduller())

    if service in ['controller', 'all']:
        wrapper('kube-controller-manager', *cp.kube_controller_manager())


if __name__ == '__main__':
    main()
