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

import shapely.geometry  # type: ignore


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output-stem', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with open(args.input, 'r') as f:
        data = json.load(f)

    shape = shapely.geometry.shape(data.get('features')[0].get('geometry'))
    (xmin, ymin, xmax, ymax) = shape.bounds

    for i in range(0, 4):
        x1 = xmin + (i + 0)*((xmax - xmin) / 4)
        x2 = xmin + (i + 1)*((xmax - xmin) / 4)
        for j in range(0, 4):
            y1 = ymin + (j + 0)*((ymax - ymin)/4)
            y2 = ymin + (j + 1)*((ymax - ymin)/4)
            box = shapely.geometry.box(x1, y1, x2, y2)
            data['features'][0]['geometry'] = shapely.geometry.mapping(box)

            with open('{}_{:02d}_{:02d}.geojson'.format(args.output_stem, i, j), 'w') as f:
                json.dump(data, f, sort_keys=True,
                          indent=4, separators=(',', ': '))
