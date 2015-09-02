#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# diffoscope: in-depth comparison of files, archives, and directories
#
# Copyright © 2015 Jérémy Bobbio <lunar@debian.org>
#
# diffoscope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# diffoscope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with diffoscope.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import pytest
from diffoscope.comparators import specialize
from diffoscope.comparators.binary import FilesystemFile, NonExistingFile
from diffoscope.comparators.tar import TarFile
from diffoscope.config import Config

TEST_FILE1_PATH = os.path.join(os.path.dirname(__file__), '../data/test1.tar')
TEST_FILE2_PATH = os.path.join(os.path.dirname(__file__), '../data/test2.tar')

@pytest.fixture
def tar1():
    return specialize(FilesystemFile(TEST_FILE1_PATH))

@pytest.fixture
def tar2():
    return specialize(FilesystemFile(TEST_FILE2_PATH))

def test_identification(tar1):
    assert isinstance(tar1, TarFile)

def test_no_differences(tar1):
    difference = tar1.compare(tar1)
    assert difference is None

@pytest.fixture
def differences(tar1, tar2):
    return tar1.compare(tar2).details

def test_listing(differences):
    expected_diff = open(os.path.join(os.path.dirname(__file__), '../data/tar_listing_expected_diff')).read()
    assert differences[0].unified_diff == expected_diff

def test_symlinks(differences):
    assert differences[1].source1 == 'dir/link'
    assert differences[1].source2 == 'dir/link'
    assert differences[1].comment == 'symlink'
    expected_diff = open(os.path.join(os.path.dirname(__file__), '../data/symlink_expected_diff')).read()
    assert differences[1].unified_diff == expected_diff

def test_text_file(differences):
    assert differences[2].source1 == 'dir/text'
    assert differences[2].source2 == 'dir/text'
    expected_diff = open(os.path.join(os.path.dirname(__file__), '../data/text_ascii_expected_diff')).read()
    assert differences[2].unified_diff == expected_diff

def test_compare_non_existing(monkeypatch, tar1):
    monkeypatch.setattr(Config.general, 'new_file', True)
    difference = tar1.compare(NonExistingFile('/nonexisting', tar1))
    assert difference.source2 == '/nonexisting'
    assert difference.details[-1].source2 == '/dev/null'
