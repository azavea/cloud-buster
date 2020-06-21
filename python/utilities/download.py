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

import rasterio as rio
import numpy as np


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--geojson', required=True, type=str)
    parser.add_argument('--mindate', required=True, type=str)
    parser.add_argument('--maxdate', required=True, type=str)
    parser.add_argument('--maxclouds', required=True, type=int)
    parser.add_argument('--minclouds', required=False, default=0.0, type=int)
    parser.add_argument('--images', required=True, type=int)
    parser.add_argument('--output-dir', required=True, type=str)
    parser.add_argument('--refresh-token', required=True, type=str)
    parser.add_argument('--kind', required=False,
                        choices=['L2A', 'L1C'], nargs='+', default=['L1C'])
    parser.add_argument('--max-uncovered', required=False,
                        type=float, default=1e-8)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    command = ''.join([
        'python3 /workspace/query_rf.py ',
        '--geojson {} '.format(args.geojson),
        '--limit {} '.format(max(64, args.images)),
        '--refresh-token {} '.format(args.refresh_token),
        '--response /tmp/raw.json ',
        '--maxclouds {} '.format(args.maxclouds),
        '--mindate {} '.format(args.mindate),
        '--maxdate {} '.format(args.maxdate),
        '> /dev/null'
    ])

    if os.WEXITSTATUS(os.system(command)) != 0:
        raise Exception()

    command = ''.join([
        'python3 /workspace/filter.py ',
        '--backstop False ',
        '--coverage-count {} '.format(args.images),
        '--max-selections {} '.format(args.images),
        '--input /tmp/raw.json ',
        '--output /tmp/filtered.json ',
        '--max-uncovered {} '.format(args.max_uncovered),
        '--minclouds {} '.format(args.minclouds),
        '> /dev/null'
    ])

    if os.WEXITSTATUS(os.system(command)) != 0:
        raise Exception('Filter command failed')

    try:
        with open('/tmp/filtered.json', 'r') as f:
            data = json.load(f)
    except:
        raise Exception('Polygon not covered.  Try increasing --max-uncovered')
    data['selections'] = data['selections'][0:args.images]

    os.system('mkdir -p {}'.format(args.output_dir))

    for kind in args.kind:
        print(kind)

        if kind == 'L2A':
            sentinel_bucket = 'sentinel-s2-l2a'
            sentinel_10m = 'R10m/'
            sentinel_20m = 'R20m/'
            sentinel_60m = 'R60m/'
        elif kind == 'L1C':
            sentinel_bucket = 'sentinel-s2-l1c'
            sentinel_10m = sentinel_20m = sentinel_60m = ''

        for (selection, index) in zip(data['selections'], range(0, len(data))):
            selection['index'] = index

            print('10m')
            command = ''.join([
                'aws s3 sync ',
                's3://{}/{}/{} '.format(sentinel_bucket,
                                        selection.get(
                                            'sceneMetadata').get('path'),
                                        sentinel_10m),
                '/tmp/ ',
                '--exclude="*" --include="B0[2348].jp2" ',
                '--request-payer requester'
            ])
            if os.WEXITSTATUS(os.system(command)) != 0:
                raise Exception()

            print('20m')
            command = ''.join([
                'aws s3 sync ',
                's3://{}/{}/{} '.format(sentinel_bucket,
                                        selection.get(
                                            'sceneMetadata').get('path'),
                                        sentinel_20m),
                '/tmp/ ',
                '--exclude="*" --include="B0[567].jp2" --include="B8A.jp2" --include="B1[12].jp2" ',
                '--request-payer requester'
            ])
            if os.WEXITSTATUS(os.system(command)) != 0:
                raise Exception()

            print('60m')
            command = ''.join([
                'aws s3 sync ',
                's3://{}/{}/{} '.format(sentinel_bucket,
                                        selection.get(
                                            'sceneMetadata').get('path'),
                                        sentinel_60m),
                '/tmp/ ',
                '--exclude="*" --include="B0[19].jp2" --include="B10.jp2" ',
                '--request-payer requester'
            ])
            if os.WEXITSTATUS(os.system(command)) != 0:
                raise Exception()

            with rio.open('/tmp/B04.jp2', 'r') as ds:
                profile = copy.copy(ds.profile)
                width = ds.width
                height = ds.height
            if kind == 'L2A':
                profile.update(count=12, compress='deflate',
                               bigtiff='yes', driver='GTiff')
                bands = np.zeros((12, width, height), dtype=np.uint16)
            elif kind == 'L1C':
                profile.update(count=13, compress='deflate',
                               bigtiff='yes', driver='GTiff')
                bands = np.zeros((13, width, height), dtype=np.uint16)

            if kind == 'L2A':
                filenames = ['B01.jp2', 'B02.jp2',
                             'B03.jp2', 'B04.jp2',
                             'B05.jp2', 'B06.jp2',
                             'B07.jp2', 'B08.jp2',
                             'B8A.jp2', 'B09.jp2',
                             'B11.jp2', 'B12.jp2']
            elif kind == 'L1C':
                filenames = ['B01.jp2', 'B02.jp2',
                             'B03.jp2', 'B04.jp2',
                             'B05.jp2', 'B06.jp2',
                             'B07.jp2', 'B08.jp2',
                             'B8A.jp2', 'B09.jp2',
                             'B10.jp2', 'B11.jp2',
                             'B12.jp2']

            print('reading')
            for (filename, band) in zip(filenames, range(0, len(bands))):
                print('.')
                with rio.open('/tmp/{}'.format(filename), 'r') as ds:
                    bands[band] = ds.read(out_shape=(1, width, height))

            print('writing')
            with rio.open('{}/{}-{}.tif'.format(args.output_dir, kind.upper(), index), 'w', **profile) as ds:
                ds.write(bands)

    with open('{}/info.json'.format(args.output_dir), 'w') as f:
        json.dump(data, f, sort_keys=True,
                  indent=4, separators=(',', ': '))
