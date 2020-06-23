# cloud-buster

![Cloud Buster](https://user-images.githubusercontent.com/11281373/72922457-f7a3d080-3d44-11ea-9032-fc80166a5389.jpg)



## Query ##

```
python3 python/query_rf.py --geojson geometry.geojson --refresh-token abcxyz --response raw-response.json
```

## Filter ##

```
python3 python/filter.py --input raw-response.json --output filtered-response.json
```

## Gather ##

```
python3 python/meta-gather.py --architecture arch.py --weights weights.pth --gather gather.py --name good-name --output-path s3://my-bucket/path/ --response filtered-response.json --jobqueue my-queue --jobdef my-jobdef:33
```

## Merge ##

```
python3 python/meta-merge.py --merge merge.py --input-path s3://my-bucket/input-path/ --output-path s3://my-bucket/output-path/ --name good-name --jobqueue my-queue --jobdef my-jobdef:33
```

# Notes #

If you intend to use this on AWS Batch, it is recommended that you create a custom AMI with additional storage space and/or use an instances with a lot of RAM and make use of `/dev/shm`;  the default amount of storage given to Batch instances is frequently too small.  One way to do this is to start with the default AMI used on CPU-based Batch jobs (e.g. `Amazon Linux AMI amzn-ami-2018.03.20200205 x86_64 ECS HVM GP2`) then create a virtual machine with only one large volume (no volume on `/dev/xvdcz`) to ensure that there is room for docker images and temporary storage in docker containers.
