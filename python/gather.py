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
import json
import os


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True, type=str)
    parser.add_argument('--index', required=True, type=int)
    parser.add_argument('--output-path', required=True, type=str)
    parser.add_argument('--sentinel-path', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    os.system('aws s3 sync s3://sentinel-s2-l1c/{}/ /tmp --exclude="*" --include="B*.jp2" --request-payer requester'.format(args.sentinel_path))
    os.system('aws s3 sync s3://sentinel-s2-l2a/{}/qi/ /tmp --exclude="*" --include="CLD_20m.jp2" --request-payer requester'.format(args.sentinel_path))
    info = json.loads(os.popen('gdalinfo -json /tmp/B04.jp2').read())
    geoTransform = info.get('geoTransform')
    xres = geoTransform[1]
    yres = geoTransform[5]
    filename = '/tmp/{}-{}.tif'.format(args.name, args.index)
    os.system('PYTHONPATH=/usr/local/lib/python3.6/site-packages gdal_merge.py -separate -o /tmp/scratch.tif -co COMPRESS=LZW -co TILED=YES -co SPARSE_OK=YES -ps {} {} /tmp/B01.jp2 /tmp/B02.jp2 /tmp/B03.jp2 /tmp/B04.jp2 /tmp/B05.jp2 /tmp/B06.jp2 /tmp/B07.jp2 /tmp/B08.jp2 /tmp/B8A.jp2 /tmp/B09.jp2 /tmp/B10.jp2 /tmp/B11.jp2 /tmp/B12.jp2 /tmp/CLD_20m.jp2'.format(xres, yres))
    os.system('rm -f /tmp/*.jp2')
    os.system('gdalwarp -t_srs epsg:4326 /tmp/scratch.tif -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES {}'.format(filename))
    os.system('aws s3 cp {} {}'.format(filename, args.output_path))
