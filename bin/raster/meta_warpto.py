#!/usr/bin/env python3

# The MIT License (MIT)
# =====================
#
# Copyright © 2020 Azavea
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the “Software”), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.


import argparse
import copy
import os


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--metadata-file', required=True, type=str)
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--postfix', required=False, default='labels', type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    output = copy.copy(args.metadata_file).replace('.tif', '-{}.tif'.format(args.postfix))
    args.input = args.input.replace('s3://', '/vsis3/')
    args.metadata_file = args.metadata_file.replace('s3://', '/vsis3/')

    submission = 'python3 warpto.py --metadata-file {} --input {} --output /tmp/out.tif'.format(args.metadata_file, args.input)
    # print(submission)
    os.system(submission)
    os.system('aws s3 cp /tmp/out.tif {}'.format(output))
    os.system('rm -f /tmp/out.tif')
