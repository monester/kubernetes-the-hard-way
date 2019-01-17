#!/usr/bin/env python3

import argparse
import subprocess


class ControlPlane:
    def __init__(self, apiserver, workdir):
        self.etcd_servers = '127.0.0.1',
        self.master = apiserver
        self.hyperkube = 'k8s.gcr.io/hyperkube:v1.13.1'
        self.workdir = workdir


    def etcd(self, index=0):
        image = 'quay.io/coreos/etcd:v3.2'
        ip = self.etcd_servers
        env = [
            'ETCDCTL_API=3',
            f'ETCDCTL_ENDPOINTS=https://{ip}:2379',
            f'ETCDCTL_CACERT={self.workdir}/ca.pem',
            f'ETCDCTL_CERT={self.workdir}/kubernetes.pem',
            f'ETCDCTL_KEY={self.workdir}/kubernetes-key.pem',
        ]
        command = [
            'etcd',
            '--name=etcd1',
            f'--advertise-client-urls=https://{ip}:2379',
            f'--listen-client-urls=https://{ip}:2379',
            f'--trusted-ca-file={self.workdir}/ca.pem',
            f'--cert-file={self.workdir}/kubernetes.pem',
            f'--key-file={self.workdir}/kubernetes-key.pem',
            '--client-cert-auth',
        ]
        return image, env, command

    def kube_apiserver(self):
        addresses = self.etcd_servers

        etcd_servers = ','.join([f'https://{ip}:2379' for ip in addresses])
        env = []
        image  = self.hyperkube
        command = [
            'kube-apiserver',

            # we should allow priviledged containers
            '--allow-privileged=true',

            # allow RBAC for services, SA, users
            # allow Node for kubelet authorization using SSL certificates
            '--authorization-mode=Node,RBAC',

            '--bind-address=0.0.0.0',

            # allow certificates with this root CA
            f'--client-ca-file={self.workdir}/ca.pem',

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
            f'--etcd-cafile={self.workdir}/ca.pem',
            f'--etcd-certfile={self.workdir}/kubernetes.pem',
            f'--etcd-keyfile={self.workdir}/kubernetes-key.pem',
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
        image  = self.hyperkube
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
        image  = self.hyperkube
        command = [
            'kube-scheduler',
            # master connection details
            f'--kubeconfig={self.workdir}/kube-scheduler.kubeconfig',
            '--leader-elect=true',
            '--v 2',
        ]
        return image, env, command

def docker(service, image, env, command, debug, run):
    if debug:
        run_str = '# {service} #\ndocker run --rm --network=host --name {service} -ti {env} {volumes} {image} \\\n{command}\n\n'
    else:
        run_str = '# {service} #\ndocker run --restart=always --network=host --name {service} --detach {env} {volumes} {image} \\\n{command}\n\n'
    line = run_str.format(
        service=service,
        env=' '.join([f'-e{i}' for i in env]),
        volumes='-v/etc/kubernetes/ssl:/etc/kubernetes/ssl',
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

def kube(name, image, env, command, debug, run):
    from textwrap import dedent
    config = dedent(f'''\
        ---
        apiVersion: extensions/v1
        kind: StatefulSet
        metadata:
          labels:
            app: {name}
          name: {name}
        spec:
          selector:
            matchLabels:
              app: {name}
          strategy:
            rollingUpdate:
              maxUnavailable: 0
            type: RollingUpdate
          template:
            metadata:
              labels:
                app: {name}
            spec:
              initContainers:
              - name: certficate-checker
                image: python:3.7
                env:
                - APP_NAME: {name}
              containers:
              - image: {image}
                name {name}
    ''')
    print(config)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker', action='store_true', default=False)
    parser.add_argument('--kube', action='store_true', default=True)
    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument('--run', action='store_true', default=False)
    parser.add_argument('--service', default='all')
    parser.add_argument('--workdir', help='Path to PKI folder', default='/etc/kubernetes/ssl', metavar='workdir', required=False)
    parser.add_argument('--apiserver', help='IP address of API server of worker node', metavar='ip', default='127.0.0.1')
    parser.add_argument('node', help='hostname of worker node', metavar='worker', nargs='*')
    args = parser.parse_args()

    cp = ControlPlane(args.apiserver, args.workdir)

    if args.docker:
        wrapper = docker
    elif args.kube:
        wrapper = kube

    service = args.service
    debug = args.debug
    run = args.run

    print(run, debug)
    if service in ['etcd', 'all']:
        wrapper('etcd', *cp.etcd(), debug, run)

    if service in ['apiserver', 'all']:
        wrapper('kube-apiserver', *cp.kube_apiserver(), debug, run)

    if service in ['scheduler', 'all']:
        wrapper('kube-scheduler', *cp.kube_scheduller(), debug, run)

    if service in ['controller', 'all']:
        wrapper('kube-controller-manager', *cp.kube_controller_manager(), debug, run)


if __name__ == '__main__':
    main()
