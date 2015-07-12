#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# debbindiff: highlight differences between two builds of Debian packages
#
# Copyright © 2015 Daniel Kahn Gillmor <dkg@fifthhorseman.net>
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

import os.path
import shutil
import pytest
from debbindiff.comparators.pe import compare_pe_files

# these were generated with:

# echo 'public class Test { static public void Main () {} }' > test.cs
# mcs -out:test1.exe test.cs ; sleep 2; mcs -out:test2.exe test.cs

TEST_FILE1_PATH = os.path.join(os.path.dirname(__file__), '../data/test1.exe') 
TEST_FILE2_PATH = os.path.join(os.path.dirname(__file__), '../data/test2.exe') 

def test_no_differences():
    difference = compare_pe_files(TEST_FILE1_PATH, TEST_FILE1_PATH)
    assert difference is None

@pytest.fixture
def differences():
    return compare_pe_files(TEST_FILE1_PATH, TEST_FILE2_PATH).details

def test_diff(differences):
    expected_diff = open(os.path.join(os.path.dirname(__file__), '../data/pe_expected_diff')).read()
    assert differences[0].unified_diff == expected_diff
