from setuptools import setup

setup(name='cloudbuster',
      version='0.1',
      description='Sentinel 2 L1C Imagery with Fewer Clouds ',
      url='http://github.com/jamesmcclain/cloud-buster',
      author='James McClain',
      author_email='[email protected]',
      license='MIT',
      packages=['cloudbuster'],
      scripts=['bin/query_rf', 'bin/filter_rf', 'bin/gather', 'bin/meta-gather', 'bin/merge', 'bin/meta-merge'],
      zip_safe=False)
