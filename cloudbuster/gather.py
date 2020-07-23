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

import codecs
import copy
import json
import math
import os
from urllib.parse import urlparse
from typing import Optional, List

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


def gather(sentinel_path: str,
           output_s3_uri: str,
           index: int,
           name: str,
           backstop: bool,
           working_dir: str = '/tmp',
           bounds: Optional[List[float]] = None,
           delete: bool = True,
           architecture: Optional[str] = None,
           weights: Optional[str] = None,
           s2cloudless: bool = False,
           kind: str = 'L1C',
           donate_mask: bool = False,
           donor_mask: Optional[str] = None,
           donor_mask_name: Optional[str] = None):
    codes = []

    assert output_s3_uri.endswith('/')
    assert not working_dir.endswith('/')
    assert (len(bounds) == 4 if bounds is not None else True)
    assert (weights.endswith('.pth') if weights is not None else True)
    assert (kind in ['L1C', 'L2A'])
    if donor_mask is not None:
        assert donor_mask.endswith('/') or donor_mask.endswith('.tif')
        if donor_mask.endswith('/'):
            assert donor_mask_name is not None

    def working(filename):
        return os.path.join(working_dir, filename)

    if not backstop and donor_mask is None:
        command = ''.join([
            'aws s3 sync ',
            's3://sentinel-s2-l2a/{}/qi/ '.format(sentinel_path),
            '{} '.format(working_dir),
            '--exclude="*" --include="CLD_20m.jp2" ',
            '--request-payer requester'
        ])
        os.system(command)

    if kind == 'L2A':
        sentinel_bucket = 'sentinel-s2-l2a'
        sentinel_10m = 'R10m/'
        sentinel_20m = 'R20m/'
        sentinel_60m = 'R60m/'
        num_bands = 13
    elif kind == 'L1C':
        sentinel_bucket = 'sentinel-s2-l1c'
        sentinel_10m = sentinel_20m = sentinel_60m = ''
        num_bands = 14
    else:
        raise Exception()

    # 10m
    command = ''.join([
        'aws s3 sync s3://{}/{}/{} '.format(sentinel_bucket,
                                            sentinel_path, sentinel_10m),
        '{} '.format(working_dir),
        '--exclude="*" --include="B0[2348].jp2" ',
        '--request-payer requester'
    ])
    os.system(command)

    # 20m
    command = ''.join([
        'aws s3 sync s3://{}/{}/{} '.format(sentinel_bucket,
                                            sentinel_path, sentinel_20m),
        '{} '.format(working_dir),
        '--exclude="*" '
        '--include="B0[567].jp2" --include="B8A.jp2" --include="B1[12].jp2" ',
        '--request-payer requester'
    ])
    os.system(command)

    # 60m
    command = ''.join([
        'aws s3 sync s3://{}/{}/{} '.format(sentinel_bucket,
                                            sentinel_path, sentinel_60m),
        '{} '.format(working_dir),
        '--exclude="*" '
        '--include="B0[19].jp2" --include="B10.jp2" ',
        '--request-payer requester'
    ])
    os.system(command)

    # Determine resolution, size, and filename
    info = json.loads(
        os.popen('gdalinfo -json -proj4 {}'.format(working('B04.jp2'))).read())
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
    name_pattern = '{}-{:02d}'.format(name, index)
    if not backstop:
        filename = working('{}.tif'.format(name_pattern))
        mask_filename = working('mask-{}.tif'.format(name_pattern))
    else:
        filename = working('backstop-{}.tif'.format(name_pattern))
    out_shape = (1, width, height)

    # Build image
    data = np.zeros((num_bands, width, height), dtype=np.uint16)
    with rio.open(working('B01.jp2')) as ds:
        data[0] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B02.jp2')) as ds:
        data[1] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B03.jp2')) as ds:
        data[2] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B04.jp2')) as ds:
        data[3] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
        geoTransform = copy.deepcopy(ds.transform)
        crs = copy.deepcopy(ds.crs)
        profile = copy.deepcopy(ds.profile)
        profile.update(count=num_bands, driver='GTiff',
                       bigtiff='yes', sparse_ok=True, tiled=True)
    with rio.open(working('B05.jp2')) as ds:
        data[4] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B06.jp2')) as ds:
        data[5] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B07.jp2')) as ds:
        data[6] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B08.jp2')) as ds:
        data[7] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B8A.jp2')) as ds:
        data[8] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    with rio.open(working('B09.jp2')) as ds:
        data[9] = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)[0]
    if kind == 'L2A':
        with rio.open(working('B11.jp2')) as ds:
            data[10] = ds.read(out_shape=out_shape,
                               resampling=rasterio.enums.Resampling.nearest)[0]
        with rio.open(working('B12.jp2')) as ds:
            data[11] = ds.read(out_shape=out_shape,
                               resampling=rasterio.enums.Resampling.nearest)[0]
    elif kind == 'L1C':
        with rio.open(working('B10.jp2')) as ds:
            data[10] = ds.read(out_shape=out_shape,
                               resampling=rasterio.enums.Resampling.nearest)[0]
        with rio.open(working('B11.jp2')) as ds:
            data[11] = ds.read(out_shape=out_shape,
                               resampling=rasterio.enums.Resampling.nearest)[0]
        with rio.open(working('B12.jp2')) as ds:
            data[12] = ds.read(out_shape=out_shape,
                               resampling=rasterio.enums.Resampling.nearest)[0]
    else:
        raise Exception()
    if delete:
        os.system('rm -f {}'.format(working('B*.jp2')))

    cloud_mask = np.zeros(out_shape, dtype=np.uint16)

    # Get the stock cloud mask
    if not backstop and os.path.isfile(working('CLD_20m.jp2')) and donor_mask is None:
        with rio.open(working('CLD_20m.jp2')) as ds:
            tmp = ds.read(out_shape=out_shape,
                          resampling=rasterio.enums.Resampling.nearest)
            cloud_mask = cloud_mask + (tmp > 40).astype(np.uint16)
            del tmp
        if delete:
            os.system('rm -f {}'.format(working('CLD_20m.jp2')))

    # Get s2cloudless cloud mask.  This is always on L1C imagery.
    if not backstop and s2cloudless is not False and kind == 'L1C' and donor_mask is None:
        from s2cloudless import S2PixelCloudDetector

        width_16 = width//16
        height_16 = height//16

        small_data = np.zeros((13, width_16, height_16), dtype=np.uint16)
        rasterio.warp.reproject(
            data[0:13], small_data,
            src_transform=geoTransform,
            src_crs=crs,
            dst_transform=geoTransform *
            rasterio.transform.Affine.scale(16, 16),
            dst_crs=crs,
            resampling=rasterio.enums.Resampling.nearest)
        small_data = np.transpose(small_data, axes=(1, 2, 0))
        small_data = small_data.reshape(1, width_16, height_16, 13) / 1e5
        cloud_detector = S2PixelCloudDetector(
            threshold=0.4, average_over=4, dilation_size=1, all_bands=True)
        small_tmp = cloud_detector.get_cloud_probability_maps(small_data)
        try:
            quantile = np.quantile(
                np.extract(small_tmp > np.min(small_tmp), small_tmp), 0.20)
        except:
            quantile = 0.0033
        cutoff = max(0.0033, quantile)
        small_tmp = (small_tmp > cutoff).astype(np.uint16)

        tmp = np.zeros((1, width, height), dtype=np.uint16)
        rasterio.warp.reproject(
            small_tmp, tmp,
            src_transform=geoTransform *
            rasterio.transform.Affine.scale(16, 16),
            src_crs=crs,
            dst_transform=geoTransform,
            dst_crs=crs,
            resampling=rasterio.enums.Resampling.nearest)

        cloud_mask = cloud_mask + tmp

        del tmp
        del small_tmp
        del small_data

    # Get model cloud mask
    if not backstop and architecture is not None and weights is not None and donor_mask is None:
        model_window_size = 512
        load_architecture(architecture)
        if torch.cuda.is_available():
            device = torch.device('cuda')
        else:
            device = torch.device('cpu')
        if not os.path.exists(working('weights.pth')):
            os.system('aws s3 cp {} {}'.format(
                weights, working('weights.pth')))
        model = make_model(num_bands-1, input_stride=1,
                           class_count=1, divisor=1, pretrained=False).to(device)
        model.load_state_dict(torch.load(
            working('weights.pth'), map_location=device))
        model = model.eval()

        with torch.no_grad():
            tmp = np.zeros((1, width, height), dtype=np.float32)
            for xoffset in range(0, width, model_window_size):
                if xoffset + model_window_size > width:
                    xoffset = width - model_window_size - 1
                print('{:02.3f}%'.format(100 * (xoffset / width)))
                for yoffset in range(0, height, model_window_size):
                    if yoffset + model_window_size > height:
                        yoffset = height - model_window_size - 1
                    window = data[0:(num_bands-1), xoffset:(xoffset+model_window_size), yoffset:(
                        yoffset+model_window_size)].reshape(1, num_bands-1, model_window_size, model_window_size).astype(np.float32)
                    tensor = torch.from_numpy(window).to(device)
                    out = model(tensor).get('2seg').cpu().numpy()
                    tmp[0, xoffset:(xoffset+model_window_size),
                        yoffset:(yoffset+model_window_size)] = out

        tmp = (tmp > 0.0).astype(np.uint16)
        cloud_mask = cloud_mask + tmp

        del tmp

    # Dilate mask
    if donor_mask is None:
        element = np.ones((11, 11))
        cloud_mask[0] = scipy.ndimage.binary_dilation(
            cloud_mask[0], structure=element)

    # If donating mask, save and upload
    if donate_mask and not backstop:
        mask_profile = copy.deepcopy(profile)
        mask_profile.update(count=1, compress='deflate', predictor=2)
        with rio.open(mask_filename, 'w', **mask_profile) as ds:
            ds.write(cloud_mask)
        code = os.system('aws s3 cp {} {}'.format(
            mask_filename, output_s3_uri))
        codes.append(code)

    # If using donor mask, download and load
    if donor_mask is not None and not backstop:

        if not donor_mask.endswith('.tif'):
            donor_name_pattern = '{}-{:02d}'.format(donor_mask_name, index)
            donor_mask_filename = 'mask-{}.tif'.format(donor_name_pattern)
            donor_mask += donor_mask_filename

        code = os.system(
            'aws s3 cp {} {}'.format(donor_mask, working(donor_mask_filename)))
        codes.append(code)
        with rio.open(working(donor_mask_filename), 'r') as ds:
            cloud_mask = ds.read()[0]
        if delete:
            os.system('rm -f {}'.format(working(donor_mask_filename)))

    # Write scratch file
    data[num_bands-1] = ((cloud_mask < 1) * (data[0] != 0)).astype(np.uint16)
    for i in range(0, num_bands-1):
        data[i] = data[i] * data[num_bands-1]
    data[num_bands-1] = data[num_bands-1] * index
    with rio.open(working('scratch.tif'), 'w', **profile) as ds:
        ds.write(data)

    # Warp and compress to create final file
    if bounds is None or len(bounds) != 4:
        te = ''
    else:
        [xmin, ymin, xmax, ymax] = bounds
        te = '-te {} {} {} {}'.format(xmin, ymin, xmax, ymax)
    command = ''.join([
        'gdalwarp {} '.format(working('scratch.tif')),
        '-tr {} {} '.format(xres, yres),
        '-srcnodata 0 -dstnodata 0 ',
        '-t_srs epsg:4326 ',
        '-multi ',
        '-co NUM_THREADS=ALL_CPUS -wo NUM_THREADS=ALL_CPUS ',
        '-oo NUM_THREADS=ALL_CPUS -doo NUM_THREADS=ALL_CPUS ',
        '-co BIGTIFF=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co SPARSE_OK=YES ',
        '{} '.format(te),
        '{}'.format(filename)
    ])
    code = os.system(command)
    codes.append(code)
    if delete:
        os.system('rm -f {}'.format(working('scratch.tif')))

    # Upload final file
    code = os.system('aws s3 cp {} {}'.format(filename, output_s3_uri))
    codes.append(code)

    codes = list(map(lambda c: os.WEXITSTATUS(c) != 0, codes))
    return codes


if __name__ == '__main__':
    import argparse
    import ast
    import sys

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
        parser.add_argument('--s2cloudless', required=False,
                            default=False, type=ast.literal_eval)
        parser.add_argument('--kind', required=False,
                            choices=['L2A', 'L1C'], default='L1C')
        parser.add_argument('--donate-mask', required=False,
                            default=False, type=ast.literal_eval)
        parser.add_argument('--donor-mask', required=False,
                            default=None, type=str)
        parser.add_argument('--donor-mask-name', required=False,
                            default=None, type=str)
        parser.add_argument('--tmp', required=False, type=str, default='/tmp')
        return parser

    args = cli_parser().parse_args()

    if args.donor_mask == 'None':
        args.donor_mask = None
    if args.donor_mask_name == 'None':
        args.donor_mask_name = None

    codes = gather(
        args.sentinel_path,
        args.output_path,
        args.index,
        args.name,
        args.backstop,
        working_dir=args.tmp,
        delete=args.delete,
        architecture=args.architecture,
        weights=args.weights,
        bounds=args.bounds,
        s2cloudless=args.s2cloudless,
        kind=args.kind,
        donate_mask=args.donate_mask,
        donor_mask=args.donor_mask,
        donor_mask_name=args.donor_mask_name
    )

    if any(codes):
        sys.exit(-1)
