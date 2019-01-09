#!/usr/bin/env bash

set -e
set -u


##################################################
##  TODO



## 1. permissions for scheduler
## 2. Missing ACCEPT in FORWARD CHAIN on Worker node


KUBERNETES_PUBLIC_ADDRESS=87.233.46.250
ETCD_IP_ADDRESS=127.0.0.1
WORKERS="test2-worker01 test2-worker02"

if [[ $1 == '--force' ]]; then
    test -e /etc/kubernetes/ssl && rm -rf /etc/kubernetes/ssl
    docker rm --force $(docker ps -aq)
fi

./init_ssl.py --workdir=/etc/kubernetes/ssl --apiserver="${KUBERNETES_PUBLIC_ADDRESS}" $WORKERS
./init_kubeconfig.py --workdir=/etc/kubernetes/ssl --apiserver="${KUBERNETES_PUBLIC_ADDRESS}" $WORKERS

ENCRYPTION_KEY=$(head -c 32 /dev/urandom | base64)

set -x

# docker run -d -v /etci/kubernetes/ssl:/etc/ssl/certs -p 4001:4001 -p 2380:2380 -p 2379:2379 \
#  --name etcd quay.io/coreos/etcd:v2.3.8 \
#  -name etcd0 \
#  -advertise-client-urls http://${HostIP}:2379,http://${HostIP}:4001 \
#  -listen-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001 \
#  -initial-advertise-peer-urls http://${HostIP}:2380 \
#  -listen-peer-urls http://0.0.0.0:2380 \
#  -initial-cluster-token etcd-cluster-1 \
#  -initial-cluster etcd0=http://${HostIP}:2380 \
#  -initial-cluster-state new

docker inspect etcd > /dev/null 2>&1 || docker run --restart=always --name etcd --network=host -v/etc/kubernetes/ssl:/etc/kubernetes/ssl -d \
-e ETCDCTL_API=3 \
-e ETCDCTL_ENDPOINTS=https://${ETCD_IP_ADDRESS}:2379 \
-e ETCDCTL_CACERT=/etc/kubernetes/ssl/ca.pem \
-e ETCDCTL_CERT=/etc/kubernetes/ssl/kubernetes.pem \
-e ETCDCTL_KEY=/etc/kubernetes/ssl/kubernetes-key.pem \
 \
quay.io/coreos/etcd:v3.2 etcd \
--name=etcd1 \
--advertise-client-urls=https://${ETCD_IP_ADDRESS}:2379 \
--listen-client-urls=https://${ETCD_IP_ADDRESS}:2379 \
\
\
--trusted-ca-file=/etc/kubernetes/ssl/ca.pem \
--cert-file=/etc/kubernetes/ssl/kubernetes.pem \
--key-file=/etc/kubernetes/ssl/kubernetes-key.pem \
--client-cert-auth

# Default admission plugins:

# DefaultStorageClass
# DefaultTolerationSeconds
# LimitRanger
# MutatingAdmissionWebhook
# NamespaceLifecycle
# PersistentVolumeClaimResize
# Priority
# ResourceQuota
# ServiceAccount
# ValidatingAdmissionWebhook

# TODO: ENABLE ENCRYPTION OF SECRETS
# docker rm --force kube-apiserver; export ETCD_IP_ADDRESS=127.0.0.1; \
docker inspect kube-apiserver > /dev/null 2>&1 || docker run --restart=always --name kube-apiserver --network=host -v/etc/kubernetes/ssl:/etc/kubernetes/ssl -d k8s.gcr.io/hyperkube:v1.13.1 \
kube-apiserver \
--etcd-cafile=/etc/kubernetes/ssl/ca.pem \
--etcd-certfile=/etc/kubernetes/ssl/kubernetes.pem \
--etcd-keyfile=/etc/kubernetes/ssl/kubernetes-key.pem \
--etcd-servers=https://${ETCD_IP_ADDRESS}:2379 \
--client-ca-file=/etc/kubernetes/ssl/ca.pem \
--advertise-address=0.0.0.0 \
--bind-address=0.0.0.0 \
--authorization-mode=Node,RBAC \
--kubelet-certificate-authority=/etc/kubernetes/ssl/ca.pem \
--kubelet-client-certificate=/etc/kubernetes/ssl/kubernetes.pem \
--kubelet-client-key=/etc/kubernetes/ssl/kubernetes-key.pem \
--kubelet-https=true \
--service-account-key-file=/etc/kubernetes/ssl/service-account-key.pem \
--tls-cert-file=/etc/kubernetes/ssl/kubernetes.pem \
--tls-private-key-file=/etc/kubernetes/ssl/kubernetes-key.pem \
--allow-privileged \
--enable-admission-plugins=AlwaysAdmit \
--v 2


# --enable-admission-plugins=AlwaysAdmit \
# --enable-admission-plugins=PodSecurityPolicy \
# --enable-admission-plugins=\
# AlwaysPullImages,\
# ExtendedResourceToleration,\
# Initializers,\
# NodeRestriction,\
# PersistentVolumeLabel,\
# PodNodeSelector,\
# PodPreset, PodSecurityPolicy, PodTolerationRestriction, Priority, ResourceQuota, SecurityContextDeny, ServiceAccount, StorageObjectInUseProtection,
# ValidatingAdmissionWebhook


# kubectl config set-cluster kubernetes-the-hard-way --certificate-authority=/etc/kubernetes/ssl/ca.pem --server=https://${KUBERNETES_PUBLIC_ADDRESS}:6443
# kubectl config set-credentials admin --client-certificate=/etc/kubernetes/ssl/admin.pem --client-key=/etc/kubernetes/ssl/admin-key.pem
# kubectl config set-context default --cluster=kubernetes-the-hard-way --user=admin
# kubectl config use-context default


docker inspect kube-controller > /dev/null 2>&1 || docker run --restart=always --name kube-controller --network=host -v/etc/kubernetes/ssl:/etc/kubernetes/ssl -d k8s.gcr.io/hyperkube:v1.13.1 \
kube-controller-manager \
--kubeconfig=/etc/kubernetes/ssl/kube-controller-manager.kubeconfig \
--address=0.0.0.0 \
--cluster-cidr=10.200.0.0/16 \
--cluster-name=kubernetes \
--leader-elect=true \
--cluster-signing-cert-file=/etc/kubernetes/ssl/ca.pem \
--cluster-signing-key-file=/etc/kubernetes/ssl/ca-key.pem \
--client-ca-file=/etc/kubernetes/ssl/ca.pem \
--service-account-private-key-file=/etc/kubernetes/ssl/service-account-key.pem \
--use-service-account-credentials=true \
--v 2


# docker rm --force kube-scheduler; \
docker inspect kube-scheduler > /dev/null 2>&1 || docker run --restart=always --name kube-scheduler --network=host -v/etc/kubernetes/ssl:/etc/kubernetes/ssl -d k8s.gcr.io/hyperkube:v1.13.1 \
kube-scheduler \
--client-ca-file=/etc/kubernetes/ssl/ca.pem \
--kubeconfig=/etc/kubernetes/ssl/kube-scheduler.kubeconfig \
--leader-elect=true \
--v 2

# -advertise-client-urls=http://${NODE1}:2379 \
# -initial-advertise-peer-urls=http://${NODE1}:2380 \
# -listen-client-urls=http://0.0.0.0:2379 \
# -listen-peer-urls=http://${NODE1}:2380 \
# -initial-cluster=node1=http://${NODE1}:2380

set +x
for WORKER in "${WORKERS[@]}"; do
    echo "WORKER $WORKER"
    for i in "${!WORKERS[@]}"; do
       if [[ "${WORKERS[$i]}" = "${WORKER}" ]]; then
           POD_CIDR="10.200.$i.0/24"
           break
       fi
    done
    scp worker.sh $WORKER:
    rsync -av /etc/kubernetes/ssl/ $WORKER:/etc/kubernetes/ssl/
    ssh $WORKER "WORKER=${WORKER} POD_CIDR=${POD_CIDR} bash worker.sh" || true
done


cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  annotations:
    rbac.authorization.kubernetes.io/autoupdate: "true"
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:kube-apiserver-to-kubelet
rules:
  - apiGroups:
      - ""
    resources:
      - nodes/proxy
      - nodes/stats
      - nodes/log
      - nodes/spec
      - nodes/metrics
    verbs:
      - "*"
EOF

cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: system:kube-apiserver
  namespace: ""
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:kube-apiserver-to-kubelet
subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: kubernetes
EOF



cat <<EOF | kubectl apply -f-
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: permit-root
spec:
  privileged: false
  seLinux:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
  runAsUser:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  allowedCapabilities:
  - '*'
  volumes:
  - '*'
EOF


echo '#####################################################'
echo 'Check that traffic is allowed in iptables -L FORWARD'
echo
echo '  iptables -I FORWARD 1 -j ACCEPT  '
echo
echo '#####################################################'
