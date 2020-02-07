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

import numpy as np
import rasterio as rio
import rasterio.enums
import rasterio.transform
import rasterio.windows


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mosaic-list', required=True, type=str)
    parser.add_argument('--entire-list', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--band', required=True, type=int)
    parser.add_argument('--upload', required=False, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    if 'AWS_REQUEST_PAYER' not in os.environ:
        os.environ['AWS_REQUEST_PAYER'] = 'requester'
    if 'CURL_CA_BUNDLE' not in os.environ:
        os.environ['CURL_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'

    if args.mosaic_list[0:5] == 's3://':
        command = 'aws s3 cp {mosaic} /tmp/'.format(mosaic=args.mosaic_list)
        os.system(command)
        args.mosaic_list = '/tmp/' + args.mosaic_list.split('/')[-1]
    if args.entire_list[0:5] == 's3://':
        command = 'aws s3 cp {entire} /tmp/'.format(entire=args.entire_list)
        os.system(command)
        args.entire_list = '/tmp/' + args.entire_list.split('/')[-1]

    # List of selected patches
    with open(args.mosaic_list, 'r') as f:
        mosaic_list = [line.strip() for line in f.readlines()]

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

    root_patches = math.ceil(math.sqrt(len(mosaic_list)))
    width = root_patches * 120
    height = root_patches * 120

    profile = {
        'dtype': np.uint16,
        'count': 1,
        'compress': None,
        'driver': 'GTiff',
        'width': width,
        'height': height,
        'nodata': 0,
        'tiled': True,
        'transform': rasterio.transform.from_bounds(31.132830, 29.978150, 31.135448, 29.980260, width, height),
        'crs': 'epsg:4326'
    }

    band_to_band = {
        1: 'B01', 2: 'B02', 3: 'B03',
        4: 'B04', 5: 'B05', 6: 'B06',
        7: 'B07', 8: 'B08', 9: 'B8A',
        10: 'B09', 11: 'B10', 12: 'B11',
        13: 'B12',
    }

    band_to_resolution = {
        2: 120, 3: 120, 4: 120, 8: 120,
        5: 60, 6: 60, 7: 60, 9: 60, 12: 60, 13: 60,
        1: 20, 10: 20, 11: 20,
    }

    with rio.open(args.output, 'w', **profile) as out_ds:
        i = 0
        for cloud in sorted(mosaic_list):
            read_xwindow, read_ywindow = list(map(int, cloud.split('_')[-2:]))
            write_xwindow = i % root_patches
            write_ywindow = i // root_patches

            res = band_to_resolution.get(args.band)
            read_window = rasterio.windows.Window(
                read_xwindow * res, read_ywindow * res, res, res)
            window_10m = rasterio.windows.Window(
                write_xwindow * 120, write_ywindow * 120, 120, 120)

            tile_path = entire_list[cloud]
            band_path = '/vsis3/sentinel-s2-l1c/{tile_path}/{band}.jp2'.format(
                tile_path=tile_path,
                band=band_to_band.get(args.band))

            try:
                with rio.open(band_path, 'r') as ds:
                    data = ds.read(
                        window=read_window,
                        out_shape=(1, 120, 120),
                        resampling=rasterio.enums.Resampling.bilinear)
                    assert(data.shape == (1, 120, 120))
                    out_ds.write(data, (1,), window=window_10m)
            except:
                pass

            i = i + 1
            pct = 100 * float(i) / len(mosaic_list)
            print('Band {band}: {pct}%'.format(band=args.band, pct=pct))

    if args.upload:
        command = 'aws s3 cp {output} {upload}'.format(
            output=args.output, upload=args.upload)
        os.system(command)
