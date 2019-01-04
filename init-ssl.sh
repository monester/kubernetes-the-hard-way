#!/usr/bin/env bash

set -x
set -e
set -u

if ! type cfssl; then
    wget -q --show-progress --https-only --timestamping \
      https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 \
    chmod +x cfssl_linux-amd64

    sudo mv cfssl_linux-amd64 /usr/local/bin/cfssl
fi

