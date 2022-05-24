# Imports
from setuptools import setup, find_packages

# Loading README file
with open("README.md", "r") as fh:
  long_description = fh.read()

setup(
  name = 'kolmov',
  version = '2.0.0',
  license='GPL-3.0',
  description = 'A Framework to perfomance the cross validation for Ringer tunings',
  long_description = long_description,
  long_description_content_type="text/markdown",
  packages=find_packages(),
  author = 'Micael Veríssimo de Araújo, Gabriel Gazola Milan, João Victor da Fonseca Pinto',
  author_email = 'micael.verissimo@lps.ufrj.br, gabriel.milan@lps.ufrj.br, jodafons@lps.ufrj.br',
  url = 'https://github.com/micaelverissimo/kolmov',
  keywords = ['framework', 'validation', 'machine-learning', 'ai', 'plotting', 'data-visualization'],
  install_requires = [
    'tensorflow==2.6.4',
    'numpy<1.19.0,>=1.16.6',
    'six>=1.12.0',
    'scipy==1.4.1',
    'future',
    'sklearn',
    'scikit-learn>=0.22.1',
    'Gaugi>=1.0.0',
    'matplotlib>=3.1.3',
    'seaborn>=0.10.0',
    'onnxruntime',
    'keras2onnx'
  ],
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
  ],
)
