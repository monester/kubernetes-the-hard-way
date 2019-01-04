kubectl apply -f-  <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: default
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tiller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: default
    namespace: kube-system
EOF

if ! type helm; then
    wget https://storage.googleapis.com/kubernetes-helm/helm-v2.12.1-linux-amd64.tar.gz
    tar -xzvf helm-v2.12.1-linux-amd64.tar.gz
    cp linux-amd64/helm /usr/bin
    rm -rf linux-amd64 helm-v2.12.1-linux-amd64.tar.gz
fi

helm init
