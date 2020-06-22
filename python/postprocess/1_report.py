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
import json
import os

# Given the location of a tif on S3, store a proto source report on
# S3.  This can be run on AWS batch or locally.

def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=str, help='The S3 location of the tif')
    parser.add_argument('--output', required=True, type=str, help='The S3 location where the geojson report should go')
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    input_name = copy.deepcopy(args.input).replace('s3://', '/vsis3/')
    info = json.loads(os.popen('gdalinfo -json {}'.format(input_name)).read())
    [x, y] = info.get('size')
    os.system('gdal_translate -b 14 -co TILED=YES -co SPARSE_OK=YES {} /tmp/out0.tif'.format(input_name))
    os.system('gdalwarp -ts {} {} -r max -co TILED=YES -co SPARSE_OK=YES /tmp/out0.tif /tmp/out1.tif'.format(x//4, y//4))
    os.system('gdal_polygonize.py /tmp/out1.tif -f GeoJSON /tmp/out.geojson')
    os.system('aws s3 cp /tmp/out.geojson {}'.format(args.output))
