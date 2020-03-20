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
import gzip
import json

import shapely.geometry
import shapely.ops


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tile-list', required=True, type=str)
    parser.add_argument('--report-directory', required=True, type=str)
    parser.add_argument('--prediction-directory', required=True, type=str)
    parser.add_argument('--output-directory', required=True, type=str)
    return parser


def shape_to_json(f):
    return {
        'type': 'Features',
        'geometry': shapely.geometry.mapping(f),
    }


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with gzip.open(args.tile_list, 'r') as f:
        tile_list = f.read().decode()
        tile_list = json.loads(tile_list)

    dataset_name = args.tile_list.split('/')[-1].split('.')[0]

    report = None
    prediction = None
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

    prediction_features = shapely.ops.cascaded_union(
        prediction.get('features'))
    prediction_features = list(prediction_features)
    simplified_prediction_features = list(
        map(lambda s: s.simplify(0.001), prediction_features))
    prediction_features = list(map(shape_to_json, prediction_features))
    simplified_prediction_features = list(
        map(shape_to_json, simplified_prediction_features))

    # Write reports
    report_filename = '{}/source-{}.geojson.gz'.format(
        args.output_directory, dataset_name)
    with gzip.open(report_filename, 'w') as f:
        f.write(json.dumps(report, sort_keys=True,
                           indent=4, separators=(',', ': ')).encode())

    # Write predictions
    prediction_filename = '{}/prediction-{}.geojson.gz'.format(
        args.output_directory, dataset_name)
    prediction['features'] = prediction_features
    with gzip.open(prediction_filename, 'w') as f:
        f.write(json.dumps(prediction, sort_keys=True,
                           indent=4, separators=(',', ': ')).encode())

    # Write simplified predictions
    simplified_prediction_filename = '{}/simplified-prediction-{}.geojson.gz'.format(
        args.output_directory, dataset_name)
    prediction['features'] = simplified_prediction_features
    with gzip.open(simplified_prediction_filename, 'w') as f:
        f.write(json.dumps(prediction, sort_keys=True,
                           indent=4, separators=(',', ': ')).encode())
