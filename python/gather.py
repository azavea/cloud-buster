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
import codecs
import copy
import json
import math
import os
import subprocess
import sys
from urllib.parse import urlparse

import boto3
import numpy as np
import rasterio as rio
import rasterio.enums
import rasterio.transform
import rasterio.warp
import requests
import scipy.ndimage
import torch
import torchvision
from s2cloudless import S2PixelCloudDetector


def read_text(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme.startswith('http'):
        return requests.get(uri).text
    elif parsed.scheme.startswith('s3'):
        parsed2 = urlparse(uri, allow_fragments=False)
        bucket = parsed2.netloc
        prefix = parsed2.path.lstrip('/')
        s3 = boto3.resource('s3')
        obj = s3.Object(bucket, prefix)
        return obj.get()['Body'].read().decode('utf-8')
    else:
        with codecs.open(uri, encoding='utf-8', mode='r') as f:
            return f.read()


def load_architecture(uri: str) -> None:
    arch_str = read_text(uri)
    arch_code = compile(arch_str, uri, 'exec')
    exec(arch_code, globals())


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--backstop', required=True, type=ast.literal_eval)
    parser.add_argument('--bounds', required=False, nargs='+', type=float)
    parser.add_argument('--delete', required=False,
                        default=True, type=ast.literal_eval)
    parser.add_argument('--index', required=True, type=int)
    parser.add_argument('--name', required=True, type=str)
    parser.add_argument('--output-path', required=True, type=str)
    parser.add_argument('--sentinel-path', required=True, type=str)
    parser.add_argument('--architecture', required=False, type=str)
    parser.add_argument('--weights', required=False, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    codes = []

    # Download data
    command = 'aws s3 sync s3://sentinel-s2-l1c/{}/ /tmp --exclude="*" --include="B*.jp2" --request-payer requester'.format(
        args.sentinel_path)
    os.system(command)
    if not args.backstop:
        command = 'aws s3 sync s3://sentinel-s2-l2a/{}/qi/ /tmp --exclude="*" --include="CLD_20m.jp2" --request-payer requester'.format(
            args.sentinel_path)
        os.system(command)

    # Determine resolution, size, and filename
    info = json.loads(os.popen('gdalinfo -json -proj4 /tmp/B04.jp2').read())
    [width, height] = info.get('size')
    [urx, ury] = info.get('cornerCoordinates').get('upperRight')
    [lrx, lry] = info.get('cornerCoordinates').get('lowerRight')
    crs = info.get('coordinateSystem').get('proj4')
    [y1, y2] = rasterio.warp.transform(
        crs, 'epsg:4326', [urx, lrx], [ury, lry])[1]
    y1 = math.cos(math.radians(y1))
    y2 = math.cos(math.radians(y2))
    geoTransform = info.get('geoTransform')
    xres = (1.0/min(y1, y2)) * (1.0/110000) * geoTransform[1]
    yres = (1.0/110000) * geoTransform[5]
    if not args.backstop:
        filename = '/tmp/{}-{:02d}.tif'.format(args.name, args.index)
    else:
        filename = '/tmp/backstop-{}-{:02d}.tif'.format(args.name, args.index)
    out_shape = (1, width, height)

    # Build image
    data = np.zeros((14, width, height), dtype=np.uint16)
    with rio.open('/tmp/B01.jp2') as ds:
        data[0] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B02.jp2') as ds:
        data[1] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B03.jp2') as ds:
        data[2] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B04.jp2') as ds:
        data[3] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
        geoTransform = copy.copy(ds.transform)
        crs = copy.copy(ds.crs)
        profile = copy.copy(ds.profile)
        profile.update(count=14, driver='GTiff', bigtiff='yes')
    with rio.open('/tmp/B05.jp2') as ds:
        data[4] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B06.jp2') as ds:
        data[5] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B07.jp2') as ds:
        data[6] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B08.jp2') as ds:
        data[7] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B8A.jp2') as ds:
        data[8] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B09.jp2') as ds:
        data[9] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B10.jp2') as ds:
        data[10] = ds.read(out_shape=out_shape,
                           resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B11.jp2') as ds:
        data[11] = ds.read(out_shape=out_shape,
                           resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open('/tmp/B12.jp2') as ds:
        data[12] = ds.read(out_shape=out_shape,
                           resampling=rasterio.enums.Resampling.nearest)[0]
    if args.delete:
        os.system('rm -f /tmp/B*.jp2')

    cloud_mask = np.zeros(out_shape, dtype=np.float32)

    # Get the stock cloud mask
    if os.path.isfile('/tmp/CLD_20m.jp2'):
        with rio.open('/tmp/CLD_20m.jp2') as ds:
            tmp = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)
            cloud_mask = cloud_mask + (tmp / 100.0)
            del tmp
        if args.delete:
            os.system('rm -f /tmp/CLD_20m.jp2')

    # Get s2cloudless cloud mask
    small_data = np.zeros((13, width//16, height//16), dtype=np.uint16)
    rasterio.warp.reproject(
        data[0:13], small_data,
        src_transform=geoTransform,
        src_crs=crs,
        dst_transform=geoTransform * rasterio.transform.Affine.scale(16, 16),
        dst_crs=crs,
        resampling=rasterio.enums.Resampling.nearest)
    small_data = np.transpose(small_data, axes=(1, 2, 0))
    small_data = small_data.reshape(1, width//16, height//16, 13) / 1e5
    cloud_detector = S2PixelCloudDetector(
        threshold=0.4, average_over=4, dilation_size=1, all_bands=True)
    cloud_probs = cloud_detector.get_cloud_probability_maps(small_data)
    cloud_probs = cloud_probs.astype(np.float32)
    quantile = np.quantile(np.extract(
        cloud_probs > np.min(cloud_probs), cloud_probs), 0.20)
    element = np.ones((7, 7))
    small_tmp = (cloud_probs > quantile).astype(np.uint8)
    small_tmp[0] = scipy.ndimage.binary_erosion(
        small_tmp[0], structure=element)
    tmp = np.zeros((1, width, height), dtype=np.float32)
    rasterio.warp.reproject(
        small_tmp, tmp,
        src_transform=geoTransform * rasterio.transform.Affine.scale(16, 16),
        src_crs=crs,
        dst_transform=geoTransform,
        dst_crs=crs,
        resampling=rasterio.enums.Resampling.nearest)
    cloud_mask = cloud_mask + tmp
    if not args.delete:
        profile.update(count=1, dtype=np.float32)
        with rio.open('/tmp/s2cloudless.tif', 'w', **profile) as ds:
            ds.write(tmp)
        profile.update(count=14, dtype=np.uint16)
    del tmp
    del small_tmp
    del small_data

    # Get model cloud mask
    if args.architecture is not None and args.weights is not None:
        tmp = np.zeros((1, width, height), dtype=np.float32)
        load_architecture(args.architecture)
        device = torch.device('cpu')
        if not os.path.exists('/tmp/weights.pth'):
            os.system('aws s3 cp {} /tmp/weights.pth'.format(args.weights))
        model = make_model(13, input_stride=1, class_count=1,
                           divisor=1, pretrained=False).to(device)
        model.load_state_dict(torch.load(
            '/tmp/weights.pth', map_location=device))
        with torch.no_grad():
            for xoffset in range(0, width, 120):
                if xoffset + 120 > width:
                    xoffset = width - 120 - 1
                print('{:02.3f}%'.format(100 * (xoffset / width)))
                for yoffset in range(0, height, 120):
                    if yoffset + 120 > height:
                        yoffset = height - 120 - 1
                    window = data[0:13,
                                  xoffset:(xoffset+120),
                                  yoffset:(yoffset+120)].reshape(1, 13, 120, 120).astype(np.float32)
                    tensor = torch.from_numpy(window).to(device)
                    out = model(tensor).get('reg').item()
                    tmp[0, xoffset:(xoffset+120), yoffset:(yoffset+120)] = out
        cloud_mask = cloud_mask + (tmp / 0.4)
        if not args.delete:
            profile.update(count=1, dtype=np.float32)
            with rio.open('/tmp/inference.tif', 'w', **profile) as ds:
                ds.write(tmp)
            profile.update(count=14, dtype=np.uint16)
        del tmp

    # Write scratch file
    MASK_INDEX = 14-1
    data[MASK_INDEX] = (cloud_mask <= 1.0).astype(np.uint16)
    for i in range(0, MASK_INDEX):
        data[i] = data[i] * data[MASK_INDEX]
    data[MASK_INDEX] = data[MASK_INDEX] * args.index
    with rio.open('/tmp/scratch.tif', 'w', **profile) as ds:
        ds.write(data)

    # Warp and compress to create final file
    if args.bounds is None or len(args.bounds) != 4:
        te = ''
    else:
        [xmin, ymin, xmax, ymax] = args.bounds
        te = '-te {} {} {} {}'.format(xmin, ymin, xmax, ymax)
    command = 'gdalwarp /tmp/scratch.tif -tr {} {} -srcnodata 0 -dstnodata 0 -t_srs epsg:4326 -co BIGTIFF=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES {} {}'.format(
        xres, yres, te, filename)
    code = os.system(command)
    codes.append(code)
    if args.delete:
        os.system('rm -f /tmp/scratch.tif')

    # Upload final file
    code = os.system('aws s3 cp {} {}'.format(filename, args.output_path))
    codes.append(code)

    codes = list(map(lambda c: os.WEXITSTATUS(c) != 0, codes))
    if any(codes):
        sys.exit(-1)
