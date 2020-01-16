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
    parser.add_argument('--bounds-clip', required=False,
                        default=True, type=ast.literal_eval)
    parser.add_argument('--bucket-name', required=True, type=str)
    parser.add_argument('--name', required=True, type=str)
    parser.add_argument('--output-path', required=True, type=str)
    parser.add_argument('--response', required=True, type=str)
    parser.add_argument('--jobqueue', required=True, type=str)
    parser.add_argument('--jobdef', required=True, type=str)
    return parser


if __name__ == '__main__':
    args = cli_parser().parse_args()

    with open(args.response, 'r') as f:
        response = json.load(f)
    [xmin, ymin, xmax, ymax] = response.get('bounds')
    results = response.get('selections')

    idxs = range(1, len(results)+1)
    for (i, result) in zip(idxs, results):
        path = result.get('sceneMetadata').get('path')
        backstop = '--backstop,{}'.format(result.get('backstop', False))
        jobname = '{}-{}'.format(args.name, i)
        if args.bounds_clip:
            bounds = '--bounds,{},{},{},{}'.format(xmin, ymin, xmax, ymax)
        else:
            bounds = ''
        submission = 'aws batch submit-job --job-name {} --job-queue {} --job-definition {} --container-overrides command=./download_run.sh,s3://{}/CODE/gather.py,--name,{},--index,{},--output-path,{},--sentinel-path,{},{},{}'.format(
            jobname, args.jobqueue, args.jobdef, args.bucket_name, args.name, i, args.output_path, path, backstop, bounds)
        if submission[-1] == ',':
            submission = submission[0:-1]
        # print(submission)
        os.system(submission)
