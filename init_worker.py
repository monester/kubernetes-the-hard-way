#!/usr/bin/env python3

import argparse
import sys
from subprocess import Popen, PIPE
import json
import os


def send_file_to_remote(node, filename, content, workdir):
    command = ['ssh', node, f'tee {filename}']

    process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=workdir)
    output, err = process.communicate(content)

    print(err, output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', help='Path to PKI folder', default='/etc/kubernetes/ssl', metavar='workdir', required=False)
    parser.add_argument('--apiserver', help='IP address of API server of worker node', metavar='ip', required=True, action='append')
    parser.add_argument('node', help='hostname of worker node', metavar='worker', nargs='+')
    args = parser.parse_args()

    workdir = args.workdir
    apiserver = args.apiserver
    nodes = args.node

    for node in nodes:
        # copy file to node
        content = open('worker.sh', 'rb').read()
        send_file_to_remote(node, '/root/worker.sh', , workdir)


        # run file



if __name__ == '__main__':
    main()
