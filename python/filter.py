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

import shapely.affinity  # type: ignore
import shapely.geometry  # type: ignore
import shapely.ops  # type: ignore


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--coverage-count',
                        required=False, default=3, type=int)
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with open(args.input, 'r') as f:
        response = json.load(f)

    results = response.get('results')
    for result in results:
        result['dataShape'] = shapely.geometry.shape(
            result.get('dataFootprint'))

    shape = shapely.geometry.shape(response.get('aoi'))
    shapes = []
    for i in range(args.coverage_count):
        shapes.append(copy.copy(shape))
    backstop = copy.copy(shape)

    selections = []

    def not_covered():
        areas = list(map(lambda s: s.area, shapes))
        print(areas)
        return sum(areas) > 0

    def not_backstopped():
        area = backstop.area
        print(area)
        return area

    while not_covered():
        i_best = -1
        j_best = -1
        area_best = 0.0
        for i in range(len(results)):
            for j in range(len(shapes)):
                raw_area = results[i].get(
                    'dataShape').intersection(shapes[j]).area
                non_cloudy_pct = 1.0 - \
                    float(results[i].get('sceneMetadata').get(
                        'cloudyPixelPercentage'))/100.0
                area = raw_area * non_cloudy_pct
                if area > area_best:
                    j_best = j
                    i_best = i
                    area_best = area
        shapes[j_best] = shapes[j_best].difference(
            results[i_best].get('dataShape'))
        selections.append(results[i_best])
        results = results[0:i_best] + results[i_best+1:]

    while not_backstopped():
        i_best = -1
        area_best = 0.0
        for i in range(len(results)):
            raw_area = results[i].get('dataShape').intersection(backstop).area
            non_cloudy_pct = 1.0 - \
                float(results[i].get('sceneMetadata').get(
                    'cloudyPixelPercentage'))/100.0
            area = raw_area * non_cloudy_pct
            if area > area_best:
                i_best = i
                area_best = area
        backstop = backstop.difference(results[i_best].get('dataShape'))
        results[i_best]['backstop'] = True
        selections.append(results[i_best])
        results = results[0:i_best] + results[i_best+1:]

    print(len(selections))
    for selection in selections:
        del selection['dataShape']
    selections = {
        'bounds': shape.bounds,
        'selections': selections
    }

    with open(args.output, 'w') as f:
        json.dump(selections, f, sort_keys=True,
                  indent=4, separators=(',', ': '))
