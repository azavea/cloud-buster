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
import ast
import copy
import json
import math
import os
import random

import numpy as np
import rasterio as rio
import rasterio.enums
import rasterio.transform
import rasterio.windows

# A script to generate a shuffled (sub-)list of uninteresting
# (e.g. non-cloudy) patches that is of the same format as the cloudy
# patch list.  The output from this script is used as input to the
# bigearthnet_mosaic script.  Used locally.

def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cloud-list', required=True, type=str, help='The list of interesting (e.g. cloudy) patches')
    parser.add_argument('--entire-list', required=True, type=str, help='The list of all patches')
    parser.add_argument('--output', required=True, type=str, help='The shuffled output list')
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    if 'AWS_REQUEST_PAYER' not in os.environ:
        os.environ['AWS_REQUEST_PAYER'] = 'requester'
    if 'CURL_CA_BUNDLE' not in os.environ:
        os.environ['CURL_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'

    # List of cloudy patches
    with open(args.cloud_list, 'r') as f:
        cloud_list = [line.strip() for line in f.readlines()]

    # List of all patches w/ paths to the source tile
    with open(args.entire_list, 'r') as f:
        _entire_list = [line.split(',')[0:2] for line in f.readlines()]
    entire_list = {}
    for entry in _entire_list:
        (k, v) = entry
        v = v.split('_')
        year = int(v[2][0:4])
        month = int(v[2][4:6])
        day = int(v[2][6:8])
        grid_square = v[5][-2:]
        v[5] = v[5][:-2]
        lat_band = v[5][-1:]
        v[5] = v[5][:-1][1:]
        utm_zone = int(v[5])
        v = 'tiles/{utm_zone}/{lat_band}/{grid_square}/{year}/{month}/{day}/0'.format(
            utm_zone=utm_zone, lat_band=lat_band, grid_square=grid_square, year=year, month=month, day=day)
        entire_list[k] = v
    del _entire_list

    cloud_set = set(cloud_list)
    num_clouds = len(cloud_list)

    noncloud_list = list(entire_list.keys())
    noncloud_list = list(filter(lambda s: s not in cloud_set, noncloud_list))
    random.shuffle(noncloud_list)
    noncloud_list = noncloud_list[0:num_clouds]

    with open(args.output, 'w') as f:
        f.writelines([line + '\n' for line in noncloud_list])
