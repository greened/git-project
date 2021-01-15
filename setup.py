#!/usr/bin/env python3
#
# Copyright 2020 David A. Greene
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
#

from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='git_project',
      version='0.0.11',
      description='Manage projects in a git repository',
      long_description=readme(),
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Programming Language :: Python :: 3.9',
          'Topic :: Software Development :: Version Control :: Git',
      ],
      keywords='git project development',
      url='http://github.com/greened/git-project',
      author='David A. Greene',
      author_email='dag@obbligato.org',
      license='GPLv3+',
      packages=['git_project'],
      install_requires = [
          'pygit2',
      ],
      entry_points = {
          'console_scripts': ['git-project=git_project.main:main'],
      },
      zip_safe=False)
