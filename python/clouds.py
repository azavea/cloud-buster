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

import numpy as np
import rasterio as rio


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output-mag', required=False, type=str)
    parser.add_argument('--output-dir', required=False, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with rio.open(args.input, 'r') as ds:
        data = ds.read()
        profile = copy.copy(ds.profile)
    profile.update(count=1, dtype=np.float32)

    (c, x, y) = data.shape
    shape = (1, x, y)

    # Compute magnitudes
    magnitudes = np.zeros(shape)
    for i in range(0, len(data)):
        magnitudes = magnitudes + np.square(data[i])
    magnitudes = np.sqrt(magnitudes).astype(np.float32)

    if args.output_mag:
        with rio.open(args.output_mag, 'w', **profile) as ds:
            ds.write(magnitudes)

    # Compute directions
    if args.output_dir:
        cloud_vector = np.array([4201, 3694, 3684, 4113, 4552, 5808, 6409, 6031, 6815, 2867, 81, 4043, 2429])
        cloud_vector = cloud_vector / np.sqrt(np.sum(np.square(cloud_vector)))
        data = np.transpose(data, axes=(1,2,0))
        directions = np.dot(data, cloud_vector)
        directions = directions.reshape(1, x, y).astype(np.float32)

        with rio.open(args.output_dir, 'w', **profile) as ds:
            ds.write(directions)
