FROM jamesmcclain/aws-batch-ml:9
LABEL author="James McClain <jmcclain@azavea.com>"
LABEL description="Download Sentinel-2 L1C and L2A Imagery"

ADD python/query_rf.py /workspace/
ADD python/filter.py /workspace/
ADD python/utilities/download.py /workspace/

ENTRYPOINT [ "/workspace/download.py" ]
