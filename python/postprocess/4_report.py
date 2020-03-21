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
import gzip
import json
import math
import os

import shapely.geometry
import shapely.ops

# Given a tile list, a directory containing source reports, and a
# directory containing vectorized predictions, preduce three gzipped
# files: a union of the source reports, a union (in either sense as
# controlled by a toggle), and another of the same except with simplified geometry.


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tile-list', required=True, type=str,
                        help='The file that contains the tile list')
    parser.add_argument('--report-directory', required=True, type=str,
                        help='The directory that contains the source reports')
    parser.add_argument('--prediction-directory', required=True, type=str,
                        help='The directory that contains the vectorized predictions')
    parser.add_argument('--output-directory', required=True, type=str,
                        help='The directory where the output should be written')
    parser.add_argument('--easy-mode', required=False,
                        type=ast.literal_eval, default=False, help='Whether to eschew finding the geometric union of the predictions')
    return parser


def shape_to_json(f):
    return {
        'type': 'Features',
        'geometry': shapely.geometry.mapping(f),
    }


# https://www.geeksforgeeks.org/break-list-chunks-size-n-python/
def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


if __name__ == '__main__':
    args = cli_parser().parse_args()

    dataset_name0 = args.tile_list.split('/')[-1].split('.')[0]

    with gzip.open(args.tile_list, 'r') as f:
        tile_list0 = f.read().decode()
        tile_list0 = json.loads(tile_list0)

    n = 13
    tile_list0 = sorted(tile_list0)
    split_num = math.ceil(len(tile_list0) / float(n))
    print('{} needs {} splits'.format(dataset_name0, split_num))
    tile_list0 = list(divide_chunks(tile_list0, n))

    for (index, tile_list) in zip(range(0, split_num), tile_list0):

        report = None
        prediction = None
        dataset_name = format('{}_split{}'.format(dataset_name0, index))
        print(dataset_name)

        for tile in tile_list:
            report_filename = '{}/{}.geojson.gz'.format(
                args.report_directory, tile)
            prediction_filename = '{}/{}.geojson.gz'.format(
                args.prediction_directory, tile)

            # Try to read report
            try:
                with gzip.open(report_filename, 'r') as f:
                    tmp = json.loads(f.read().decode())
                    if report is None:
                        report = tmp
                    else:
                        report['features'] += tmp.get('features')
            except:
                print('Failed to read {}'.format(report_filename))

            # Try to read predictions
            try:
                with gzip.open(prediction_filename, 'r') as f:
                    tmp = json.loads(f.read().decode())
                    tmp['features'] = list(map(lambda f: shapely.geometry.shape(
                        f.get('geometry')), tmp.get('features')))
                    if prediction is None:
                        prediction = tmp
                    else:
                        prediction['features'] += tmp.get('features')
            except:
                print('Failed to read {}'.format(prediction_filename))
        print('{} loaded'.format(dataset_name))

        try:
            if args.easy_mode:
                prediction_features = prediction.get('features')
            else:
                prediction_features = list(
                    shapely.ops.cascaded_union(prediction.get('features')))
            simplified_prediction_features = list(
                map(lambda s: s.simplify(0.001), prediction_features))
            prediction_features = list(map(shape_to_json, prediction_features))
            simplified_prediction_features = list(
                map(shape_to_json, simplified_prediction_features))
        except:
            prediction_features = None
            simplified_prediction_features = None
        print('{} digested'.format(dataset_name))

        # Write reports
        report_filename = '{}/source-{}.geojson.gz'.format(
            args.output_directory, dataset_name)
        with gzip.open(report_filename, 'w', compresslevel=1) as f:
            f.write(json.dumps(report, sort_keys=True,
                                indent=4, separators=(',', ': ')).encode())
        print('{} report written'.format(dataset_name))
        del report

        # Write predictions
        if prediction_features is not None:
            prediction['features'] = prediction_features
            prediction_filename = '{}/prediction-{}.geojson.gz'.format(
                args.output_directory, dataset_name)
            with gzip.open(prediction_filename, 'w', compresslevel=1) as f:
                f.write(json.dumps(prediction, sort_keys=True,
                                    indent=4, separators=(',', ': ')).encode())
        print('{} unsimplified predictions written'.format(dataset_name))
        del prediction_features

        # Write simplified predictions
        if simplified_prediction_features is not None:
            simplified_prediction_filename = '{}/simplified-prediction-{}.geojson.gz'.format(
                args.output_directory, dataset_name)
            prediction['features'] = simplified_prediction_features
            with gzip.open(simplified_prediction_filename, 'w', compresslevel=1) as f:
                f.write(json.dumps(prediction, sort_keys=True,
                                    indent=4, separators=(',', ': ')).encode())
        print('{} simplified predictions written'.format(dataset_name))
        del simplified_prediction_features
        del prediction

        print('{} split {} of {} complete'.format(
            dataset_name0, index+1, split_num))
