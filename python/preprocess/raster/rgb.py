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

import numpy as np
import rasterio as rio


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--v', required=True, type=float)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    if 'CURL_CA_BUNDLE' not in os.environ:
        os.environ['CURL_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'

    with rio.open(args.input, 'r') as ds:
        profile = copy.deepcopy(ds.profile)
        profile.update(count=3, dtype=np.uint8)
        in_data = ds.read()

    _, width, height = in_data.shape
    out_data = np.zeros((3, width, height), dtype=np.float32)
    out_data[0] = in_data[3] / args.v
    out_data[1] = in_data[2] / args.v
    out_data[2] = in_data[1] / args.v
    out_data = np.clip(out_data, 0.0, 1.0) * 0xff
    del in_data

    with rio.open(args.output, 'w', **profile) as ds:
        ds.write(out_data.astype(np.uint8))
