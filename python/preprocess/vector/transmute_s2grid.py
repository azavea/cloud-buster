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
import json

import shapely.geometry
import shapely.ops


def cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--filter', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with open(args.filter, 'r') as f:
        data = json.load(f)
        filter_geometry = list(map(lambda f: shapely.geometry.shape(
            f.get('geometry')), data.get('features')))
        filter_geometry = shapely.ops.cascaded_union(filter_geometry)

    with open(args.input, 'r') as f:
        data = json.load(f)

    # Read features
    for feature in data.get('features'):
        geometry = shapely.geometry.shape(feature.get('geometry'))
        if isinstance(geometry, shapely.geometry.collection.GeometryCollection):
            geometry = list(filter(lambda g: isinstance(
                g, shapely.geometry.polygon.Polygon), list(geometry)))
            geometry = geometry[0:1]
            geometry = shapely.geometry.MultiPolygon(geometry)
        feature['geometry'] = geometry

    # for feature in data.get('features'):
    #     if not filter_geometry.contains(feature.get('geometry')):
    #         print(feature.get('properties').get('Name'))

    # Filter features
    data['features'] = list(filter(
        lambda f: filter_geometry.intersects(f.get('geometry')), data.get('features')))

    # Convert geometry back to GeoJSON
    for feature in data.get('features'):
        feature['geometry'] = shapely.geometry.mapping(feature.get('geometry'))

    with open(args.output, 'w') as f:
        json.dump(data, f, sort_keys=True, indent=4, separators=(',', ': '))
