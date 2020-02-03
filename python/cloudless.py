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
import subprocess
import sys

import numpy as np
import rasterio as rio

try:
    from s2cloudless import S2PixelCloudDetector
except:
    # https://stackoverflow.com/a/50255019
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 's2cloudless'])
    from s2cloudless import S2PixelCloudDetector


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with rio.open(args.input, 'r') as ds:
        data = ds.read()
        profile = copy.copy(ds.profile)
    profile.update(count=1, dtype=np.float32)
    data = data[0:13, :, :]
    data = np.transpose(data, axes=(1, 2, 0))
    (x, y, c) = data.shape
    data = data.reshape(1, x, y, c) / 1e-5

    cloud_detector = S2PixelCloudDetector(
        threshold=0.4, average_over=4, dilation_size=2, all_bands=True)
    cloud_probs = cloud_detector.get_cloud_probability_maps(data)
    cloud_probs = cloud_probs.astype(np.float32)

    with rio.open(args.output, 'w', **profile) as ds:
        data.write(cloud_probs)
