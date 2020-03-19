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
    parser.add_argument('--world-geojson', required=True, type=str)
    parser.add_argument('--world-property', required=True, type=str)
    parser.add_argument('--number-geojson', required=True, type=str)
    parser.add_argument('--number-property', required=True, type=str)
    parser.add_argument('--number-min', required=False, type=int, default=1)
    parser.add_argument('--number-max', required=False, type=int, default=5)
    parser.add_argument('--grid-geojson', required=True, type=str)
    parser.add_argument('--grid-property', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with open(args.world_geojson, 'r') as f:
        world = json.load(f)
    with open(args.number_geojson, 'r') as f:
        number = json.load(f)
    with open(args.grid_geojson, 'r') as f:
        grid = json.load(f)

    # World
    world_dict = {}
    for feature in world.get('features'):
        k = feature.get('properties').get(args.world_property)
        v = shapely.geometry.shape(feature.get('geometry')).buffer(0)
        world_dict[k] = v
    del world

    # Numbers
    number_dict = {}
    for feature in number.get('features'):
        feature = shapely.geometry.shape(feature.get('geometry'))
    for i in range(args.number_min, args.number_max+1):
        fs = filter(lambda f: int(f.get('properties').get(
            args.number_property)) == i, number.get('features'))
        fs = map(lambda f: shapely.geometry.shape(f.get('geometry')), fs)
        fs = list(fs)
        number_dict[i] = shapely.ops.cascaded_union(fs).buffer(0)
    del number

    grid_list = []
    for feature in grid.get('features'):
        grid_list.append({
            'name': feature.get('properties').get(args.grid_property),
            'shape': shapely.geometry.shape(feature.get('geometry'))
        })
    del grid

    for (k1, v1) in world_dict.items():
        for (k2, v2) in number_dict.items():
            xsection = v1.intersection(v2)
            this_list = filter(lambda o: xsection.intersects(
                o.get('shape')), grid_list)
            this_list = list(map(lambda o: o.get('name'), this_list))
            filename = '/tmp/{}_{}.json.gz'.format(k1, k2)
            print(filename)
            with gzip.open(filename, 'w') as f:
                this_list = json.dumps(
                    this_list, sort_keys=True, indent=4, separators=(',', ': ')).encode()
                f.write(this_list)
