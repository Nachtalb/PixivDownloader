from pathlib import Path
from setuptools import setup, find_packages

version = '0.1.0'
maintainer = 'Nachtalb'

setup(name='pixivdownloader',
      version=version,
      description='Download posts from pixiv.net via CLI, CLI UI or programmatically.',
      long_description='%s\n\n%s' % (Path('README.rst').read_text(),
                                     Path('docs/HISTORY.txt').read_text()),

      # Get more strings from
      # http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3.7',
          'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
      ],

      keywords='pixiv downloader',
      author='Nachtalb',
      maintainer=maintainer,
      url='https://github.com/Nachtalb/PixivDownloader',
      license='GPL3',

      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['pixiv', ],
      include_package_data=True,
      zip_safe=False,

      install_requires=[
          'PixivPy',
          'PyInquirer',
          'requests-toolbelt',
          'opencv-python',
      ],

      entry_points={
          'console_scripts': [
              'pixiv = pixiv.downloader.cli:main'
          ]
      })
