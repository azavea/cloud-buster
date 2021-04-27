FROM quay.io/jmcclain/raster-vision-pytorch:Thu_Dec_10_05_00_51_UTC_2020
LABEL author="James McClain <jmcclain@azavea.com>"
LABEL description="Download Sentinel-2 L1C and L2A Imagery"

RUN pip3 --use-feature=2020-resolver install sat-search==0.3.0

ADD python/query_rf.py /workspace/
ADD python/filter.py /workspace/
ADD python/utilities/download.py /workspace/

ENTRYPOINT [ "/workspace/download.py" ]
