# cloud-buster

![Cloud Buster](https://user-images.githubusercontent.com/11281373/72922457-f7a3d080-3d44-11ea-9032-fc80166a5389.jpg)

Cloud-Buster is a Python library and command-line utility suite for generating cloud-free mosaics from Sentinel-2 imagery.  This package makes use of [RasterFoundry](https://rasterfoundry.azavea.com/) and [GDAL](https://gdal.org) to gather the imagery and assemble the mosaics.  Cloud detection is provided through one of the following mechanisms:
1. Built-in Sentinel-2 cloud masks.  Results from this method are poor; not recommended.
2. The [`s2cloudless`](https://github.com/sentinel-hub/sentinel2-cloud-detector) Python package.
3. [PyTorch](https://pytorch.org/) models.  Best results, requires availability of cloud detection architecture and weights files.

## Installation

This package is `pip`-installable.  From the project root, issue
```
pip install .
```
This will install the `cloudbuster` package into your site packages and install several python scripts to provide command-line access to Cloud-Buster functions.

One may also `import cloudbuster` direct access to the features.

## Command-Line Utilities

### Query

```
usage: query_rf.py [-h] [--aoi-name AOI_NAME] --geojson GEOJSON
                   [--limit LIMIT] [--name-property NAME_PROPERTY]
                   --refresh-token REFRESH_TOKEN [--response RESPONSE]
                   [--maxclouds MAXCLOUDS] [--mindate MINDATE [MINDATE ...]]
                   [--maxdate MAXDATE [MAXDATE ...]] [--scale SCALE]
                   [--original-shape ORIGINAL_SHAPE]
```

Pulls candidate imagery from RasterFoundry (RF); requires an RF refresh token.

Users can specify the basic parameters for matching imagery such as date ranges (`--mindate` and `--maxdate`), maximum allowable cloud coverage as defined by the Sentinel-2 metadata (`--maxclouds`), or a maximum number of candidate images (`--limit`).

The query footprint will be taken from a GeoJSON file (`--geojson`). Input features may be uniformly scaled about their bounding box centers (`--scale`), or taken as is (`--original-shape True`; will override `--scale`).

Output will be saved to either a specified file (`--response`), to a file named according to an area name (`--area-name aoi` outputs to `aoi.json`), or pulls the base of the `.json` filename from a named property of the first feature of the query geometry (`--name-property`).  Note: `--response` overrides other options, `--aoi-name` overrides `--name-property`.

Basic sample usage:
```
query_rf.py --geojson geometry.geojson \
            --refresh-token abcxyz \
            --response raw-response.json
```

### Filter

```
usage: filter.py [-h] [--backstop BACKSTOP] [--coverage-count COVERAGE_COUNT]
                 [--max-selections MAX_SELECTIONS] --input INPUT --output
                 OUTPUT [--date-regexp DATE_REGEXP]
                 [--name-regexp NAME_REGEXP] [--minclouds MINCLOUDS]
                 [--max-uncovered MAX_UNCOVERED]
```

Attempts to cover the queried geometry using a selection of imagery from a `query_rf` call.  The algorithm will attempt to cover the target area multiple times (`--coverage-count`) to help ensure the final mosaic will be cloud free after masking and merging.  Some small area of the target geometry may be left uncovered (`--max-uncovered`), which may be needed to guarantee the desired coverage.  The number of total images selected may be bounded (`--max-selections`) if, for instance, processing time and/or computational resources are limited.

Unless `--backstop False` is set, a fallback image will be selected to ensure that no holes will be left in the final mosaic, subject to the `--max-selections` constraint.  Any selections that serve as a backstop will have a `backstop` field in the output JSON file set to `True`.

Results of the `query_rf` operation may be prefiltered according to a set of criteria:
1. input imagery may be restricted to have a minimum cloud coverage percentage (`--minclouds`),
2. the `name` property of each result may be filtered to match some regular expression (`--name-regexp`), and/or
3. the `createdAt` property may be filtered according to a regular expression (`--date-regexp`).

Basic sample usage:
```
filter.py --input raw-response.json \
          --output filtered-response.json
```

### Gather

```
usage: meta-gather.py [-h] [--architecture ARCHITECTURE]
                      [--bounds-clip BOUNDS_CLIP] [--dryrun DRYRUN] --gather
                      GATHER --jobdef JOBDEF --jobqueue JOBQUEUE --name NAME
                      --output-path OUTPUT_PATH --response RESPONSE
                      [--weights WEIGHTS] [--index-start INDEX_START]
                      [--kind {L2A,L1C}] [--donate-mask DONATE_MASK]
                      [--donor-mask DONOR_MASK]
                      [--donor-mask-name DONOR_MASK_NAME] [--tmp TMP]
```

Uses AWS Batch jobs to process, in parallel, selected Sentinel-2 imagery to remove clouded areas.  Requires `cloudbuster/gather.py` to be uploaded to S3, and this location provided to the `meta-gather` process (`--gather`).  The Batch job will run in the defined queue (`--jobqueue`) using the specified job definition (`--jobdef`).  One may opt to see the batch job submission command without running it using `--dryrun`.

The response from `filter.py` must be provided (`--response`), as well as a name to serve as the base of the filenames (`--name`) that will be saved to a specified S3 location (`--output-path`).  The process will either be based on `L1C` or `L2A` Sentinel-2 tiles (`--kind`), which can be restricted to a desired bounding box (`--bounds-clip`).  That imagery will be downloaded to a local cache, which can be set using the `--tmp` option (defaults to `/tmp`).

Cloud removal takes one of several paths paths:
1. A pytorch model can be specified if `--architecture` and `--weights` are set, respectively, with the URI of an architecture and weight file.  (In order to use this method, the container referenced by the job definition must provide `pytorch`.)
2. The `--s2cloudless` switch will use the [package](https://github.com/sentinel-hub/sentinel2-cloud-detector) of the same name for cloud detection.  (In order to use this method, the container referenced by the job definition must provide `s2cloudless`.)
3. Masks are donated from another process.  See below.
4. If no additional arguments are provided, the Sentinel-2-provided cloud mask will be used.

The masked images will be saved to the S3 location given by `--output-path` with filenames of the form `{name}-{index}.tif` possibly with a prefix of `backstop-` or `mask-`.  The range of indices can be set to start from an index other than 1 (`--index-start`).

On the topic of donating masks: It is possible that you may have a cloud removal model for Sentinel-2 L1C products, but wish to cloud mask L2A imagery.  In this case, one may wish to generate a donor mask from the former and apply it to the latter.  To donate a mask, set `--donate-mask True`.  This will upload a file with the prefix `mask-` to the output S3 location.  On a subsequent run, set `--donor-mask` to point to the S3 location of the mask `.tif` file, or to the S3 bucket/prefix containing the mask file.  In the latter case, one must also set the `--donor-mask-name` to the name of the file (useful if the filename does not end with `.tif`).

Basic sample usage:
```
/meta-gather.py --gather s3://path/to/gather.py \
                --jobqueue my-queue \
                --jobdef my-jobdef:33 \
                --name good-name \
                --output-path s3://my-bucket/path/ \
                --response filtered-response.json
```

### Merge

```
usage: meta-merge.py [-h] [--dryrun DRYRUN] --input-path INPUT_PATH --jobdef
                     JOBDEF --jobqueue JOBQUEUE --merge MERGE --name NAME
                     --output-path OUTPUT_PATH [--tmp TMP]
```

To join all the gathered imagery into a single mosaic, we may use an AWS Batch task to do the work.  This benefits from the fast transfer speeds from S3 to EC2 instances.  The job queue (`--jobqueue`) and job definition (`--jobdef`) must be given, as must the input S3 location (`--input-path`), output S3 location (`--output-path`), and scene name (`--name`).  The `merge.py` script must be uploaded to S3, and that location provided via the `--merge` argument.  Note that the input path must contain only images that pertain to the current mosaic, or the resulting image will be very large—in some cases so large that the job will fail.  Intermediate files are stored in the local directory specified by `--tmp` (defaults to `/tmp`).

Upon completion, a file named `{NAME}-cloudless.tif` will exist in the output S3 bucket, as will a file named `{NAME}-cloudy.tif`.  The latter gives the combined backstop for the target region.

Basic sample usage:
```
meta-merge.py --merge s3://path/to/merge.py \
              --input-path s3://my-bucket/input-path/ \
              --output-path s3://my-bucket/output-path/ \
              --name good-name \
              --jobqueue my-queue \
              --jobdef my-jobdef:33
```

# Notes #

If you intend to use this on AWS Batch, it is recommended that you create a custom AMI with additional storage space and/or use instances with a lot of RAM and make use of `/dev/shm`;  the default amount of storage given to Batch instances is frequently too small.

One method for creating a suitable AMI is to start with the default AMI used on CPU-based Batch jobs (e.g. `Amazon Linux AMI amzn-ami-2018.03.20200205 x86_64 ECS HVM GP2`), create a virtual machine with only one large volume (no volume on `/dev/xvdcz`) to ensure that there is room for docker images and temporary storage in docker containers, and create an image from that virtual machine.
