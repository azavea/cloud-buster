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
import sys

import numpy as np

import rasterio as rio
from scipy import ndimage


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket-name', required=False, type=str)
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output-path', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    if args.bucket_name is None:
        filename = args.input.split('/')[-1]
        mask_filename = 'mask-{}'.format(filename)
        name = filename.split('-')[0]
        index = int(filename.split('-')[-1].split('.')[0])

        os.system('aws s3 cp {} /tmp/scratch0.tif'.format(args.input))
        with rio.open('/tmp/scratch0.tif') as ds:
            profile = copy.copy(ds.profile)
            data = ds.read()
        profile.update(compress='deflate')
        os.system('rm -f /tmp/scratch0.tif')

        intensity = (data[4-1] > 1900) * (data[3-1] > 1900) * (data[2-1] > 1900)
        s2_cloudmask = data[14-1]
        element = np.ones((33,33))
        s2_cloudmask = ndimage.binary_dilation(s2_cloudmask, structure=element)
        s2_cloudmask = (s2_cloudmask * intensity)
        s2_cloudmask = (s2_cloudmask == 0).astype(data.dtype)

        for i in range(0,13):
            data[i] = (data[i] * s2_cloudmask).astype(data.dtype)
        data[13] = s2_cloudmask * index

        profile.update(count=1)
        with rio.open('/tmp/scratch1.tif', 'w', **profile) as out_ds:
            (x, y) = data[13].shape
            out_ds.write(data[13].reshape(1, x, y))
        code = os.system('gdalwarp /tmp/scratch1.tif -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES /tmp/{}'.format(mask_filename))
        if os.WEXITSTATUS(code) != 0:
            sys.exit(-1)
        os.system('rm -f /tmp/scratch1.tif')
        code = os.system('aws s3 cp /tmp/{} {}'.format(mask_filename, args.output_path))
        os.system('rm -f /tmp/{}'.format(mask_filename))
        if os.WEXITSTATUS(code) != 0:
            sys.exit(-1)

        profile.update(count=14)
        with rio.open('/tmp/scratch2.tif', 'w', **profile) as out_ds:
            out_ds.write(data)
        code = os.system('gdalwarp /tmp/scratch2.tif -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES /tmp/{}'.format(filename))
        if os.WEXITSTATUS(code) != 0:
            sys.exit(-1)
        os.system('rm -f /tmp/scratch2.tif')
        code = os.system('aws s3 cp /tmp/{} {}'.format(filename, args.output_path))
        if os.WEXITSTATUS(code) != 0:
            sys.exit(-1)

    elif args.bucket_name is not None:
        jobname = args.input.split('/')[-1].split('.')[0]
        submission = 'aws batch submit-job --job-name {} --job-queue GDAL --job-definition GDAL:3 --container-overrides command=./download_run.sh,s3://{}/CODE/mask.py,--input,{},--output-path,{}'.format(jobname, args.bucket_name, args.input, args.output_path)
        os.system(submission)
