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

import pyproj
import rasterio as rio
import shapely.affinity  # type: ignore
import shapely.geometry  # type: ignore
import shapely.ops  # type: ignore


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--n', required=False, type=int, default=64)
    parser.add_argument('--transform-before',
                        required=True, type=ast.literal_eval)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    info = json.loads(
        os.popen('gdalinfo -json -proj4 {}'.format(args.input)).read())

    in_crs = pyproj.CRS.from_proj4(info.get('coordinateSystem').get('proj4'))
    out_crs = pyproj.CRS.from_proj4(
        '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs ')
    transformer = pyproj.Transformer.from_crs(in_crs, out_crs, always_xy=True)

    [width, height] = list(map(int, info.get('size')))
    xsteps = math.floor(float(width) / args.n)
    ysteps = math.floor(float(height) / args.n)

    [ulx, uly] = list(
        map(float, info.get('cornerCoordinates').get('upperLeft')))
    [lrx, lry] = list(
        map(float, info.get('cornerCoordinates').get('lowerRight')))

    feature = {
        'type': 'Feature',
        'properties': {},
        'geometry': None
    }
    feature_collection = {
        'type': 'FeatureCollection',
        'features': []
    }

    if args.transform_before:
        ulx, uly = transformer.transform(ulx, uly)
        lrx, lry = transformer.transform(lrx, lry)
        minx = min(ulx, lrx)
        maxx = max(ulx, lrx)
        miny = min(uly, lry)
        maxy = max(uly, lry)
        print('bounding box: ({}, {}) ({}, {})'.format(minx, miny, maxx, maxy))
        xstepsize = (maxx - minx) / xsteps
        ystepsize = (maxy - miny) / ysteps
        for i in range(0, math.ceil(xsteps)):
            for j in range(0, math.ceil(ysteps)):
                x0 = minx + xstepsize * i
                x1 = x0 + xstepsize
                y0 = miny + ystepsize * j
                y1 = y0 + ystepsize
                box = shapely.geometry.Polygon(
                    [(x0, y0), (x0, y1), (x1, y1), (x1, y0)])
                f = copy.copy(feature)
                f['geometry'] = shapely.geometry.mapping(box)
                feature_collection['features'].append(f)
    elif not args.transform_before:
        minx = min(ulx, lrx)
        maxx = max(ulx, lrx)
        miny = min(uly, lry)
        maxy = max(uly, lry)
        print('bounding box: {} {}'.format(transformer.transform(
            minx, miny), transformer.transform(maxx, maxy)))
        xstepsize = (maxx - minx) / xsteps
        ystepsize = (maxy - miny) / ysteps
        for i in range(0, math.ceil(xsteps)):
            for j in range(0, math.ceil(ysteps)):
                x0 = minx + xstepsize * i
                x1 = x0 + xstepsize
                y0 = miny + ystepsize * j
                y1 = y0 + ystepsize
                x0, y0 = transformer.transform(x0, y0)
                x1, y1 = transformer.transform(x1, y1)
                box = shapely.geometry.Polygon(
                    [(x0, y0), (x0, y1), (x1, y1), (x1, y0)])
                f = copy.copy(feature)
                f['geometry'] = shapely.geometry.mapping(box)
                feature_collection['features'].append(f)

    with open(args.output, 'w') as f:
        json.dump(feature_collection, f, sort_keys=True,
                  indent=4, separators=(',', ': '))
