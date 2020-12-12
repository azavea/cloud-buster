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

import json
import copy

from satsearch import Search

import shapely.affinity  # type: ignore
import shapely.geometry  # type: ignore
import shapely.ops  # type: ignore


def query_rf(features,
             refresh_token,
             limit=800,
             minclouds=0.0,
             maxclouds=20.0,
             mindate=['1307-10-13'],
             maxdate=['2038-01-19'],
             scale=None,
             original_shape=False):

    limit = min(limit, 800)

    def convert_and_scale(f):
        tmp = shapely.geometry.shape(f.get('geometry'))
        if scale is not None:
            tmp = shapely.affinity.scale(tmp, scale, scale)
        return tmp

    feature = list(map(convert_and_scale, features.get('features')))
    shape = shapely.ops.cascaded_union(feature)

    if original_shape:
        scale = None
        original_shape = shapely.ops.cascaded_union(
            list(map(convert_and_scale, features.get('features'))))
        aoi_shape = original_shape
    else:
        aoi_shape = shape

    sentinel_scenes = {
        'results': [],
        'aoi': shapely.geometry.mapping(aoi_shape)
    }

    rf_shape = shapely.geometry.mapping(shape)
    for (mindate1, maxdate1) in zip(mindate, maxdate):
        geo_filter = {
            "url": "https://earth-search.aws.element84.com/v0",
            "intersects": copy.copy(rf_shape),
            "query": {
                "eo:cloud_cover": {
                    "lte": maxclouds,
                    "gte": minclouds,
                }
            },
            "datetime": f"{mindate1}/{maxdate1}",
            "sort": [
                {
                    "field": "datetime",
                    "direction": ">",
                },
                # {
                #     "field": "eo:cloud_cover",
                #     "direction": "<",
                # },
            ],
            "collections": ["sentinel-s2-l2a"],
            "limit": limit,
        }
        search = Search(**geo_filter)
        for item in list(search.items(limit=limit))[0:limit]:
            tiles = item.assets.get("B01").get("href")
            tiles = tiles[tiles.find("/tiles") + 1:]  # get "/tiles/..."
            tiles = tiles[:-8]  # remove "/B01.jp2" from the end
            if tiles.endswith("/R60m"):
                tiles = tiles[:-5]
            result = {
                "dataFootprint": item.geometry,
                "createdAt": item.properties.get("datetime"),
                "name": item.properties.get("sentinel:product_id"),
                "sceneMetadata": {
                    "cloudyPixelPercentage":
                    item.properties.get("eo:cloud_cover"),
                    "path": tiles,
                },
            }
            sentinel_scenes['results'].append(result)

    return sentinel_scenes


if __name__ == '__main__':
    import argparse
    import ast

    def cli_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument('--aoi-name', required=False, type=str)
        parser.add_argument('--geojson', required=True, type=str)
        parser.add_argument('--limit', required=False, default=1024, type=int)
        parser.add_argument('--name-property', required=False, type=str)
        parser.add_argument('--refresh-token', required=False, type=str)
        parser.add_argument('--response', required=False, type=str)
        parser.add_argument('--minclouds',
                            required=False,
                            default=0.0,
                            type=float)
        parser.add_argument('--maxclouds',
                            required=False,
                            default=20.0,
                            type=float)
        parser.add_argument('--mindate',
                            required=False,
                            nargs='+',
                            type=str,
                            default=['1307-10-13'])
        parser.add_argument('--maxdate',
                            required=False,
                            nargs='+',
                            type=str,
                            default=['2038-01-19'])
        parser.add_argument('--scale', type=float, required=False)
        parser.add_argument('--original-shape',
                            type=ast.literal_eval,
                            required=False,
                            default=False)
        return parser

    args = cli_parser().parse_args()

    with open(args.geojson, 'r') as f:
        features = json.load(f)

    sentinel_scenes = query_rf(features=features,
                               refresh_token=args.refresh_token,
                               limit=args.limit,
                               minclouds=args.minclouds,
                               maxclouds=args.maxclouds,
                               mindate=args.mindate,
                               maxdate=args.maxdate,
                               scale=args.scale,
                               original_shape=args.original_shape)

    if args.aoi_name is None and args.name_property is not None:
        if 'properties' in features:
            feature = features
        else:
            feature = features.get('features')[0]
        args.aoi_name = feature.get('properties').get(args.name_property)

    if args.response is None and args.aoi_name is not None:
        args.response = './{}.json'.format(args.aoi_name)

    print(len(sentinel_scenes.get('results')))
    if args.response is not None:
        with open(args.response, 'w') as f:
            json.dump(sentinel_scenes,
                      f,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))
        print(args.response)
