#!/bin/bash

set -x

if ! type socat; then
    sudo apt-get update
    sudo apt-get -y install socat conntrack ipset
fi

if ! type kubectl; then
    wget -q --show-progress --https-only --timestamping \
      https://github.com/containernetworking/plugins/releases/download/v0.7.4/cni-plugins-amd64-v0.7.4.tgz \
      https://storage.googleapis.com/kubernetes-release/release/v1.13.1/bin/linux/amd64/kubectl \
      https://storage.googleapis.com/kubernetes-release/release/v1.13.1/bin/linux/amd64/kube-proxy \
      https://storage.googleapis.com/kubernetes-release/release/v1.13.1/bin/linux/amd64/kubelet

    chmod +x kubectl kube-proxy kubelet
    cp kubectl kube-proxy kubelet /usr/local/bin/
    mkdir -p /opt/cni/bin/
    tar -xvf cni-plugins-amd64-v0.7.4.tgz -C /opt/cni/bin/
fi


# docker run --rm --name kubelet --network=host -v/etc/kubernetes/ssl:/etc/kubernetes/ssl k8s.gcr.io/hyperkube:v1.13.1 \


mkdir -p /etc/kubernetes/ssl


HOSTNAME=
POD_CIDR=



mkdir -p /etc/cni/net.d
cat <<EOF | sudo tee /etc/cni/net.d/10-bridge.conf
{
    "cniVersion": "0.3.1",
    "name": "bridge",
    "type": "bridge",
    "bridge": "cnio0",
    "isGateway": true,
    "ipMasq": true,
    "ipam": {
        "type": "host-local",
        "ranges": [
          [{"subnet": "${POD_CIDR}"}]
        ],
        "routes": [{"dst": "0.0.0.0/0"}]
    }
}
EOF
cat <<EOF | sudo tee /etc/cni/net.d/99-loopback.conf
{"cniVersion": "0.3.1","type": "loopback"}
EOF




cat <<EOF | sudo tee /etc/kubernetes/kubelet-config.yaml
kind: KubeletConfiguration
apiVersion: kubelet.config.k8s.io/v1beta1
authentication:
  anonymous:
    enabled: false
  webhook:
    enabled: true
  x509:
    clientCAFile: "/etc/kubernetes/ssl/ca.pem"
authorization:
  mode: Webhook
clusterDomain: "cluster.local"
clusterDNS:
  - "8.8.8.8"
podCIDR: "${POD_CIDR}"
resolvConf: "/run/systemd/resolve/resolv.conf"
runtimeRequestTimeout: "15m"
tlsCertFile: "/etc/kubernetes/ssl/${HOSTNAME}.pem"
tlsPrivateKeyFile: "/etc/kubernetes/ssl/${HOSTNAME}-key.pem"
EOF

cat <<EOF | sudo tee /etc/systemd/system/kubelet.service
[Unit]
Description=Kubernetes Kubelet
Documentation=https://github.com/kubernetes/kubernetes
After=docker.service
Requires=docker.service

[Service]
ExecStart=/usr/local/bin/kubelet \
  --cluster-dns=8.8.8.8 \
  --config=/etc/kubernetes/kubelet-config.yaml \
  --container-runtime=docker \
  --image-pull-progress-deadline=2m \
  --kubeconfig=/etc/kubernetes/ssl/${HOSTNAME}.kubeconfig \
  --network-plugin=cni \
  --register-node=true \
  --v=2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat <<EOF | sudo tee /etc/kubernetes/kube-proxy-config.yaml
kind: KubeProxyConfiguration
apiVersion: kubeproxy.config.k8s.io/v1alpha1
clientConnection:
  kubeconfig: "/etc/kubernetes/ssl/kube-proxy.kubeconfig"
mode: "iptables"
clusterCIDR: "10.200.0.0/16"
EOF

cat <<EOF | sudo tee /etc/systemd/system/kube-proxy.service
[Unit]
Description=Kubernetes Kube Proxy
Documentation=https://github.com/kubernetes/kubernetes

[Service]
ExecStart=/usr/local/bin/kube-proxy \
  --config=/etc/kubernetes/kube-proxy-config.yaml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF


systemctl daemon-reload
systemctl restart kubelet kube-proxy
