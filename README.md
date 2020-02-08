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
