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
import os
import sys

import numpy as np

import rasterio as rio
import scipy.ndimage


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True, type=str)
    parser.add_argument('--index', required=True, type=int)
    parser.add_argument('--output-path', required=True, type=str)
    parser.add_argument('--sentinel-path', required=True, type=str)
    parser.add_argument('--delete', required=False,
                        default=True, type=ast.literal_eval)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    codes = []

    # Download data
    codes.append(os.system(
        'aws s3 sync s3://sentinel-s2-l1c/{}/ /tmp --exclude="*" --include="B*.jp2" --request-payer requester'.format(args.sentinel_path)))
    codes.append(os.system(
        'aws s3 sync s3://sentinel-s2-l2a/{}/qi/ /tmp --exclude="*" --include="CLD_20m.jp2" --request-payer requester'.format(args.sentinel_path)))

    # Determine resolution and filename
    info = json.loads(os.popen('gdalinfo -json /tmp/B04.jp2').read())
    geoTransform = info.get('geoTransform')
    xres = geoTransform[1]
    yres = geoTransform[5]
    filename = '/tmp/{}-{:02d}.tif'.format(args.name, args.index)

    # Prepare the cloud mask
    if os.path.isfile('/tmp/CLD_20m.jp2'):
        print('MASK FOUND')
        has_mask = True
        with rio.open('/tmp/CLD_20m.jp2') as ds:
            profile = copy.copy(ds.profile)
            mask = ds.read()
        profile.update(driver='GTiff', compress='deflate', tiled='yes')
        element = np.ones((7, 7))
        mask[0] = scipy.ndimage.binary_dilation(mask[0], structure=element)
        with rio.open('/tmp/CLD_20m.tif', 'w', **profile) as ds:
            ds.write(mask)
        if args.delete:
            codes.append(os.system('rm -f /tmp/CLD_20m.jp2'))
    else:
        print('NO MASK FOUND')
        has_mask = False

    # Merge to create first scratch file
    if has_mask:
        codes.append(os.system('gdal_merge.py -separate -o /tmp/scratch0.tif -ps {} {} -co BIGTIFF=YES /tmp/B01.jp2 /tmp/B02.jp2 /tmp/B03.jp2 /tmp/B04.jp2 /tmp/B05.jp2 /tmp/B06.jp2 /tmp/B07.jp2 /tmp/B08.jp2 /tmp/B8A.jp2 /tmp/B09.jp2 /tmp/B10.jp2 /tmp/B11.jp2 /tmp/B12.jp2 /tmp/CLD_20m.tif'.format(xres, yres)))
        if args.delete:
            codes.append(os.system('rm -f /tmp/*.jp2 /tmp/CLD_20m.tif'))
    else:
        codes.append(os.system('gdal_merge.py -separate -o /tmp/scratch0.tif -ps {} {} -co BIGTIFF=YES /tmp/B01.jp2 /tmp/B02.jp2 /tmp/B03.jp2 /tmp/B04.jp2 /tmp/B05.jp2 /tmp/B06.jp2 /tmp/B07.jp2 /tmp/B08.jp2 /tmp/B8A.jp2 /tmp/B09.jp2 /tmp/B10.jp2 /tmp/B11.jp2 /tmp/B12.jp2'.format(xres, yres)))
        if args.delete:
            codes.append(os.system('rm -f /tmp/*.jp2 /tmp/CLD_20m.tif'))

    # Apply mask to create second scratch file
    if has_mask:
        with rio.open('/tmp/scratch0.tif') as ds:
            profile = copy.copy(ds.profile)
            data = ds.read()
        MASK_INDEX = 14-1
        data[MASK_INDEX] = (data[MASK_INDEX] == 0)
        for i in range(0, MASK_INDEX):
            data[i] = data[i] * data[MASK_INDEX]
        data[MASK_INDEX] = data[MASK_INDEX] * args.index
        if args.delete:
            codes.append(os.system('rm -f /tmp/scratch0.tif'))
        with rio.open('/tmp/scratch1.tif', 'w', **profile) as ds:
            ds.write(data)
    else:
        with rio.open('/tmp/scratch0.tif') as ds:
            profile = copy.copy(ds.profile)
            data = ds.read()
        profile.update(count=14)
        xy = data[0].shape
        mask = np.ones(xy) * args.index
        mask = mask[np.newaxis].astype(data.dtype)
        data = np.concatenate([data, mask], axis=0)
        if args.delete:
            codes.append(os.system('rm -f /tmp/scratch0.tif'))
        with rio.open('/tmp/scratch1.tif', 'w', **profile) as ds:
            ds.write(data)

    # Warp and compress to create final file
    codes.append(os.system(
        'gdalwarp -srcnodata 0 -dstnodata 0 -t_srs epsg:4326 /tmp/scratch1.tif -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES {}'.format(filename)))
    if args.delete:
        codes.append(os.system('rm -f /tmp/scratch1.tif'))

    # Upload final file
    codes.append(
        os.system('aws s3 cp {} {}'.format(filename, args.output_path)))

    codes = list(map(lambda c: os.WEXITSTATUS(c) != 0, codes))
    if any(codes):
        sys.exit(-1)
