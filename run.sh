#!/bin/sh

rm -f *
docker rm --force `docker ps -aq`


BASE=$(realpath $(dirname $0))
WORKDIR=$(pwd)

$BASE/init_ssl.py --workdir "$WORKDIR" --apiserver 127.0.0.1 node01
$BASE/init_kubeconfig.py --workdir "$WORKDIR" --apiserver 127.0.0.1 node01
$BASE/control-plane.py --workdir "$WORKDIR" --run
