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

import copy
import json
import os
import sys

import numpy as np

import rasterio as rio
import scipy.ndimage


def merge(name: str,
          input_s3_uri: str,
          output_s3_uri: str,
          local_working_dir: str = '/tmp'):

    assert input_s3_uri.endswith('/')
    assert output_s3_uri.endswith('/')
    assert not local_working_dir.endswith('/')

    def working(filename):
        return os.path.join(local_working_dir, filename)

    cloudless_tif = working('{}-cloudless.tif'.format(name))
    cloudy_tif = working('{}-cloudy.tif'.format(name))

    # Download
    os.system(''.join([
       'aws s3 sync ',
       '{} '.format(input_s3_uri),
       '{}/ '.format(local_working_dir),
       '--exclude="*" --include="*.tif" --exclude="mask*.tif"'
    ]))
    backstops = int(
        os.popen('ls {} | wc -l'.format(working('backstop*.tif'))).read())

    # Produce final images
    if backstops > 0:
        # merge backstops to backstop
        os.system(''.join([
            'gdalwarp ',
            '$(ls {} | grep backstop | sort -r) '.format(working('*.tif')),
            '-multi ',
            '-co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS ',
            '-oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS ',
            '-co TILED=YES -co BIGTIFF=YES ',
            '{}'.format(working('cloudy.tif'))
        ]))
        # compress backstop
        os.system(''.join([
            'gdalwarp {} '.format(working('cloudy.tif')),
            '-multi ',
            '-co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS ',
            '-oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS ',
            '-co COMPRESS=DEFLATE -co PREDICTOR=2 ',
            '-co TILED=YES -co SPARSE_OK=YES -co BIGTIFF=YES '
            '{}'.format(cloudy_tif)
        ]))
        # delete scratch backstop
        os.system('rm {}'.format(working('cloudy.tif')))
        # upload backstop
        os.system(''.join([
            'aws s3 cp ',
            '{} '.format(cloudy_tif),
            '{}'.format(output_s3_uri)
        ]))
        # merge imagery including backstop
        os.system(''.join([
            'gdalwarp ',
            '{} '.format(cloudy_tif),
            '$(ls {} | grep -v backstop | grep -v cloudy | grep -v mask | sort -r) '.format(working('*.tif')),
            '-multi ',
            '-co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS ',
            '-oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS ',
            '-co TILED=YES -co BIGTIFF=YES ',
            '{}'.format(working('cloudless.tif'))
        ]))
        # compress imagery
        os.system(''.join([
            'gdalwarp ',
            '{} '.format(working('cloudless.tif')),
            '-multi ',
            '-co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS ',
            '-oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS ',
            '-co COMPRESS=DEFLATE -co PREDICTOR=2 ',
            '-co TILED=YES -co SPARSE_OK=YES -co BIGTIFF=YES ',
            '{}'.format(cloudless_tif)
        ]))
        # delete scratch imagery
        os.system('rm {}'.format(working('cloudless.tif')))
    else:
        # merge imagery
        os.system(''.join([
            'gdalwarp ',
            '$(ls {} | grep -v backstop | grep -v cloudy | grep -v mask | sort -r) '.format(working('*.tif')),
            '-multi ',
            '-co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS ',
            '-oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS ',
            '-co TILED=YES -co BIGTIFF=YES ',
            '{}'.format(working('cloudless.tif'))
        ]))
        # compress imagery
        os.system(''.join([
            'gdalwarp ',
            '{} '.format(working('cloudless.tif')),
            '-multi ',
            '-co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS ',
            '-oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS ',
            '-co COMPRESS=DEFLATE -co PREDICTOR=2 ',
            '-co TILED=YES -co SPARSE_OK=YES -co BIGTIFF=YES ',
            '{}'.format(cloudless_tif)
        ]))
        # delete scratch imagery
        os.system('rm {}'.format(working('cloudless.tif')))

    # Upload
    os.system('aws s3 cp {} {}'.format(cloudless_tif, output_s3_uri))


if __name__ == '__main__':
    import argparse

    def cli_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument('--input-path', required=True, type=str)
        parser.add_argument('--name', required=True, type=str)
        parser.add_argument('--output-path', required=True, type=str)
        return parser

    args = cli_parser().parse_args()

    merge(args.name, args.input_path, args.output_path)
