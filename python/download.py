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

import rasterio as rio
import numpy as np


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--geojson', required=True, type=str)
    parser.add_argument('--mindate', required=True, type=str)
    parser.add_argument('--maxdate', required=True, type=str)
    parser.add_argument('--maxclouds', required=True, type=int)
    parser.add_argument('--images', required=True, type=int)
    parser.add_argument('--output-dir', required=True, type=str)
    parser.add_argument('--refresh-token', required=True, type=str)
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
        '> /dev/null'
    ])

    if os.WEXITSTATUS(os.system(command)) != 0:
        raise Exception()

    with open('/tmp/filtered.json', 'r') as f:
        data = json.load(f)
    data['selections'] = data['selections'][0:args.images]

    os.system('mkdir -p {}'.format(args.output_dir))

    i = 0
    for (selection, index) in zip(data['selections'], range(0, len(data))):
        selection['index'] = index

        command = ''.join([
            'aws s3 sync ',
            's3://sentinel-s2-l1c/{}/ '.format(
                selection.get('sceneMetadata').get('path')),
            '/tmp/ ',
            '--exclude="*" --include="B*.jp2" ',
            '--request-payer requester'
        ])

        if os.WEXITSTATUS(os.system(command)) != 0:
            raise Exception()

        with rio.open('/tmp/B04.jp2', 'r') as ds:
            profile = copy.copy(ds.profile)
            width = ds.width
            height = ds.height
        profile.update(count=13, compress='deflate',
                       bigtiff='yes', driver='GTiff')

        bands = np.zeros((13, width, height), dtype=np.uint16)

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
        with rio.open('{}/{}.tif'.format(args.output_dir, index), 'w', **profile) as ds:
            ds.write(bands)

    with open('{}/info.json'.format(args.output_dir), 'w') as f:
        json.dump(data, f, sort_keys=True,
                  indent=4, separators=(',', ': '))
