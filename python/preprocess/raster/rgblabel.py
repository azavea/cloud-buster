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
    return parser


# Turn an RGB image into labels.  Solid red is mapped to 0x01, solid
# black is mapped to 0x02, and everything else is mapped to 0x00.  The
# idea is that one can use GIMP or photoshop or similar to label an
# RGB image, then use this script to turn that into a single band
# label file.
if __name__ == '__main__':
    args = cli_parser().parse_args()

    if 'CURL_CA_BUNDLE' not in os.environ:
        os.environ['CURL_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'

    with rio.open(args.input, 'r') as ds:
        profile = copy.deepcopy(ds.profile)
        profile.update(count=1, dtype=np.uint8,
                       compress='deflate', predictor=2, tiled=True)
        in_data = ds.read()

    red_0xff = (in_data[0] == 0xff)
    red_0x00 = (in_data[0] == 0x00)
    green_0x00 = (in_data[1] == 0x00)
    blue_0x00 = (in_data[2] == 0x00)

    _, width, height = in_data.shape
    del in_data
    out_data = np.zeros((1, width, height), dtype=np.uint8)
    out_data[0][(red_0xff * green_0x00 * blue_0x00)] = 0x01
    out_data[0][(red_0x00 * green_0x00 * blue_0x00)] = 0x02

    with rio.open(args.output, 'w', **profile) as ds:
        ds.write(out_data.astype(np.uint8))
