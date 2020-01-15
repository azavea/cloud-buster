# cloud-buster

![Cloud Buster](https://user-images.githubusercontent.com/11281373/72390088-cc582a80-3721-11ea-9353-1d0671b684da.jpg)


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
python3 python/meta-gather.py --bucket-name my-bucket --name good-name --output-path s3://my-bucket/path/ --response filtered-response.json --jobqueue my-queue --jobdef my-jobdef:33
```

## Merge ##

```
```
