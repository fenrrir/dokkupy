# Copyright 2017 Rodrigo Pinheiro Marques de Araujo <fenrrir@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
# AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
# THE SOFTWARE OR THE USE OR OTHER

import argparse
import dokkupy


def main():
    parser = argparse.ArgumentParser(description='Deploy on dokku with dokkupy')
    parser.add_argument('--project-name', required=True, help='project name')
    parser.add_argument('--address', required=True, help='address of dokku instance')
    parser.add_argument('--config', required=True, help='config file')
    parser.add_argument('command', choices=['deploy', 'remove'])

    args = parser.parse_args()

    dokku = dokkupy.Dokku(args.address)
    if args.command == 'deploy':
        dokku.deploy_from_file(args.project_name, args.config)
    else:
        dokku.remove_from_file(args.project_name, args.config)


if __name__ == '__main__':
    main()
