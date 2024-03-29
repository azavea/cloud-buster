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
import json
import os


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--architecture', required=False, type=str)
    parser.add_argument('--bounds-clip', required=False,
                        default=True, type=ast.literal_eval)
    parser.add_argument('--dryrun', required=False,
                        default=False, type=ast.literal_eval)
    parser.add_argument('--gather', required=True, type=str)
    parser.add_argument('--jobdef', required=True, type=str)
    parser.add_argument('--jobqueue', required=True, type=str)
    parser.add_argument('--name', required=True, type=str)
    parser.add_argument('--output-path', required=True, type=str)
    parser.add_argument('--response', required=True, type=str)
    parser.add_argument('--weights', required=False, type=str)
    parser.add_argument('--index-start', required=False, default=1, type=int)
    parser.add_argument('--kind', required=False,
                        choices=['L2A', 'L1C'], default='L1C')
    parser.add_argument('--donate-mask', required=False,
                        default=False, type=ast.literal_eval)
    parser.add_argument('--donor-mask', required=False,
                        default=None, type=str)
    parser.add_argument('--donor-mask-name', required=False,
                        default=None, type=str)
    parser.set_defaults(s2cloudless=False)
    parser.add_argument('--tmp', required=False, type=str, default='/tmp')
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with open(args.response, 'r') as f:
        response = json.load(f)
    [xmin, ymin, xmax, ymax] = response.get('bounds')
    results = response.get('selections')

    idxs = range(args.index_start, len(results)+args.index_start)
    for (i, result) in zip(idxs, results):
        submission = ''.join([
            'aws batch submit-job ',
            '--job-name {} '.format('{}-{}'.format(args.name, i)),
            '--job-queue {} '.format(args.jobqueue),
            '--job-definition {} '.format(args.jobdef),
            '--container-overrides vcpus=2,memory=15000,',
            'command=./download_run.sh,{},'.format(args.gather),
            '--name,{},'.format(args.name),
            '--index,{},'.format(i),
            '--output-path,{},'.format(args.output_path),
            '--sentinel-path,{},'.format(
                result.get('sceneMetadata').get('path')),
            '--architecture,{},'.format(
                args.architecture) if args.architecture is not None else '',
            '--weights,{},'.format(args.weights) if args.weights is not None else '',
            '--bounds,{},{},{},{},'.format(xmin, ymin,
                                           xmax, ymax) if args.bounds_clip else '',
            '--kind,{},'.format(args.kind),
            '--donor-mask,{},'.format(args.donor_mask),
            '--donor-mask-name,{},'.format(args.donor_mask_name),
            '--donate-mask,{},'.format(args.donate_mask),
            '--tmp,{},'.format(args.tmp),
            '--backstop,{}'.format(result.get('backstop', False)),
        ])
        if args.dryrun:
            print(submission)
        else:
            os.system(submission)
