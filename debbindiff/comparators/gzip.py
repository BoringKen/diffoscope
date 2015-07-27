# -*- coding: utf-8 -*-
#
# debbindiff: highlight differences between two builds of Debian packages
#
# Copyright © 2014-2015 Jérémy Bobbio <lunar@debian.org>
#
# debbindiff is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# debbindiff is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with debbindiff.  If not, see <http://www.gnu.org/licenses/>.

from contextlib import contextmanager
import re
import subprocess
import os.path
import debbindiff.comparators
from debbindiff import tool_required
from debbindiff.comparators.binary import File, needs_content
from debbindiff.comparators.utils import Archive, get_compressed_content_name
from debbindiff.difference import Difference
from debbindiff import logger, tool_required


class GzipContainer(Archive):
    @property
    def path(self):
        return self._path

    def open_archive(self, path):
        self._path = path
        return self

    def close_archive(self):
        self._path = None

    def get_member_names(self):
        return [get_compressed_content_name(self.path, '.gz')]

    @tool_required('gzip')
    def extract(self, member_name, dest_dir):
        dest_path = os.path.join(dest_dir, member_name)
        logger.debug('gzip extracting to %s' % dest_path)
        with open(dest_path, 'wb') as fp:
            subprocess.check_call(
                ["gzip", "--decompress", "--stdout", self.path],
                shell=False, stdout=fp, stderr=None)
        return dest_path


class GzipFile(object):
    RE_FILE_TYPE = re.compile(r'^gzip compressed data\b')

    @staticmethod
    def recognizes(file):
        return GzipFile.RE_FILE_TYPE.match(file.magic_file_type)

    @needs_content
    def compare_details(self, other, source=None):
        differences = []
        differences.append(Difference.from_unicode(
                               self.magic_file_type, other.magic_file_type, self, other, source='metadata'))
        with GzipContainer(self).open() as my_container, \
             GzipContainer(other).open() as other_container:
            differences.extend(my_container.compare(other_container, source))
        return differences
