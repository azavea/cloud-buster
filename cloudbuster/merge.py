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


def merge(name,
          input_s3_uri,
          output_s3_uri,
          local_working_dir='/tmp'):
    def working(filename):
        return os.path.join(local_working_dir, filename)

    cloudless_tif = working('{}-cloudless.tif'.format(name))
    cloudy_tif = working('{}-cloudy.tif'.format(name))

    # Download
    os.system('aws s3 sync {} {}'.format(input_s3_uri, local_working_dir))
    backstops = int(os.popen('ls {} | wc -l'.format(working('backstop*.tif')).read())

    # Produce final images
    if backstops > 0:
        os.system('gdalwarp $(ls {} | grep backstop | sort -r) -multi -co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS -oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS -co TILED=YES -co BIGTIFF=YES {}'.format(working('*.tif'), working('cloudy.tif')))
        os.system('gdalwarp {} -multi -co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS -oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES -co BIGTIFF=YES {}'.format(working('cloudy.tif'), cloudy_tif))
        os.system('rm {}'.format(working('cloudy.tif')))
        os.system('aws s3 cp {} {}'.format(cloudy_tif, output_s3_uri))
        os.system('gdalwarp {} $(ls {} | grep -v backstop | grep -v cloudy | sort -r) -multi -co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS -oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS -co TILED=YES -co BIGTIFF=YES {}'.format(cloudy_tif, working('*.tif'), working('cloudless.tif')))
        os.system('gdalwarp {} -multi -co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS -oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES -co BIGTIFF=YES {}'.format(working('cloudless.tif'), cloudless_tif))
        os.system('rm {}'.format(working('cloudless.tif')))
    else:
        os.system('gdalwarp $(ls {} | grep -v backstop | grep -v cloudy | sort -r) -multi -co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS -oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS -co TILED=YES -co BIGTIFF=YES {}'.format(working('*.tif'), working('cloudless.tif')))
        os.system('gdalwarp {} -multi -co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS -oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES -co BIGTIFF=YES {}'.format(working('cloudless.tif'), cloudless_tif))
        os.system('rm {}'.format(working('cloudless.tif')))

    # Upload
    os.system('aws s3 cp {} {}'.format(cloudless_tif, output_s3_uri))
