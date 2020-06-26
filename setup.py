from setuptools import setup

setup(name='cloudbuster',
      version='0.1',
      description='Sentinel 2 L1C Imagery with Fewer Clouds ',
      url='http://github.com/jamesmcclain/cloud-buster',
      author='James McClain',
      author_email='[email protected]',
      license='MIT',
      packages=['cloudbuster'],
      scripts=['cloudbuster/query_rf.py', 'cloudbuster/filter.py', 'cloudbuster/gather.py', 'cloudbuster/merge.py', 'python/meta-gather.py', 'python/meta-merge.py'],
      zip_safe=False)
