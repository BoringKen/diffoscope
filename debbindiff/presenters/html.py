# -*- coding: utf-8 -*-
#
# debbindiff: highlight differences between two builds of Debian packages
#
# Copyright © 2014 Jérémy Bobbio <lunar@debian.org>
#
# debdindiff is free software: you can redistribute it and/or modify
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

from __future__ import print_function
import os.path
import re
import subprocess
import sys
from tempfile import NamedTemporaryFile
from xml.sax.saxutils import escape
from debbindiff import logger, VERSION
from debbindiff.comparators.utils import make_temp_directory

HEADER = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="generator" content="pandoc">
  <title>%(title)s</title>
  <style>
    body {
      background: white;
      color: black;
    }
    .footer {
      font-size: small;
    }
    .difference {
      border: outset #888 1px;
      background-color:rgba(0,0,0,.1);
      padding: 0.5em;
      margin: 0.5em 0;
    }
    .difference table {
      table-layout: fixed;
      width: 100%%;
    }
    .difference th,
    .difference td {
      width: 50%%;
    }
    .difference td div {
      overflow: auto;
    }
    .comment {
      font-style: italic;
    }
    .source {
      font-weight: bold;
    }
    .error {
      border: solid black 1px;
      background: red;
      color: white;
      padding: 0.2em;
    }
    .lnr {
      background-color: #ccc;
      color: #666;
    }
    .DiffChange {
      background-color: #ff8888;
      font-weight: bold;
    }
    .DiffText {
      color: white;
      background-color: #ff4444;
      font-weight: bold;
    }
  </style>
  %(css_link)s
</head>
<body>
"""

FOOTER = """
<div class="footer">Generated by debbindiff %(version)s</div>
</body>
</html>
"""

DEFAULT_MAX_PAGE_SIZE = 2000 * 2 ** 10  # 2000 kB
MAX_DIFF_BLOCK_LINES = 50


class PrintLimitReached(Exception):
    pass


def create_limited_print_func(print_func, max_page_size):
    def limited_print_func(s, force=False):
        if not hasattr(limited_print_func, 'char_count'):
            limited_print_func.char_count = 0
        print_func(s)
        limited_print_func.char_count += len(s)
        if not force and limited_print_func.char_count >= max_page_size:
            raise PrintLimitReached()
    return limited_print_func


def trim_file(path, skip_lines):
    n = 0
    skip = 0
    with file(path, "r") as content:
        tmp_file = None
        try:
            tmp_file = NamedTemporaryFile("w", dir=os.path.dirname(path),
                                          delete=False)
            for line in content:
                n += 1
                if n in skip_lines.keys():
                    skip = skip_lines[n]
                    tmp_file.write("[ %d lines removed ]\n" % skip)

                if skip > 0:
                    if n not in skip_lines.keys():
                        # insert dummy line to preserve correct line numbers
                        tmp_file.write(".\n")
                    skip -= 1
                else:
                    tmp_file.write(line)
            os.rename(tmp_file.name, path)
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except OSError as _:
                    pass # we've done our best


# reduce size of diff blocks by prediffing with diff (which is extremely fast)
# and then trimming the blocks larger than the configured limit
def optimize_files_for_diff(path1, path2):
    cmd = ['diff', '-u0', path1, path2]
    p = subprocess.Popen(cmd, shell=False,
        close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    p.wait()
    if p.returncode != 1:
        raise subprocess.CalledProcessError(cmd, p.returncode, output=stderr)
    skip_lines1 = dict()
    skip_lines2 = dict()
    search = re.compile(r'^@@\s+-(?P<start1>\d+),(?P<len1>\d+)\s+\+(?P<start2>\d+),(?P<len2>\d+)\s+@@$')
    for line in stdout.split('\n'):
        found = search.match(line)
        if found:
            start1 = int(found.group('start1'))
            len1 = int(found.group('len1'))
            start2 = int(found.group('start2'))
            len2 = int(found.group('len2'))
            if len1 > MAX_DIFF_BLOCK_LINES:
                skip_lines1[start1 + MAX_DIFF_BLOCK_LINES] = len1 - MAX_DIFF_BLOCK_LINES
            if len2 > MAX_DIFF_BLOCK_LINES:
                skip_lines2[start2 + MAX_DIFF_BLOCK_LINES] = len2 - MAX_DIFF_BLOCK_LINES
    if len(skip_lines1) > 0:
        trim_file(path1, skip_lines1)
    if len(skip_lines2) > 0:
        trim_file(path2, skip_lines2)


# Huge thanks to Stefaan Himpe for this solution:
# http://technogems.blogspot.com/2011/09/generate-side-by-side-diffs-in-html.html
def create_diff(lines1, lines2):
    with make_temp_directory() as temp_dir:
        path1 = os.path.join(temp_dir, 'content1')
        path2 = os.path.join(temp_dir, 'content2')
        diff_path = os.path.join(temp_dir, 'diff.html')
        with open(path1, 'w') as f:
            f.writelines(map(lambda u: u.encode('utf-8'), lines1))
        with open(path2, 'w') as f:
            f.writelines(map(lambda u: u.encode('utf-8'), lines2))
        optimize_files_for_diff(path1, path2)
        p = subprocess.Popen(
            ['vim', '-n', '-N', '-e', '-i', 'NONE', '-u', 'NORC', '-U', 'NORC',
             '-d', path1, path2,
             '-c', 'colorscheme zellner',
             '-c', 'let g:html_number_lines=1',
             '-c', 'let g:html_use_css=1',
             '-c', 'let g:html_no_progress=1',
             '-c', 'TOhtml',
             '-c', 'w! %s' % (diff_path,),
             '-c', 'qall!',
            ], shell=False, close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        # Consume all output and wait until end of processing
        _, _ = p.communicate()
        p.wait()
        if p.returncode != 0:
            return 'vim exited with error %d' % p.returncode
        output = open(diff_path).read()
        output = re.search(r'(<table.*</table>)', output,
                           flags=re.MULTILINE | re.DOTALL).group(1)
        output = re.sub(r'<th.*</th>', '', output,
                        flags=re.MULTILINE | re.DOTALL)
        return output


def output_difference(difference, print_func):
    logger.debug('html output for %s' % (difference.source1,))
    print_func("<div class='difference'>")
    try:
        if difference.source1 == difference.source2:
            print_func("<div><span class='source'>%s</div>"
                       % escape(difference.source1))
        else:
            print_func("<div><span class='source'>%s</span> vs.</div>"
                       % escape(difference.source1))
            print_func("<div><span class='source'>%s</span></div>"
                       % escape(difference.source2))
        if difference.comment:
            print_func("<div class='comment'>%s</div>"
                       % escape(difference.comment).replace('\n', '<br />'))
        if difference.lines1 and difference.lines2:
            print_func(create_diff(difference.lines1, difference.lines2))
        for detail in difference.details:
            output_difference(detail, print_func)
    except PrintLimitReached:
        logger.debug('print limit reached')
        raise
    finally:
        print_func("</div>", force=True)


def output_header(css_url, print_func):
    if css_url:
        css_link = '<link href="%s" type="text/css" rel="stylesheet" />' % css_url
    else:
        css_link = ''
    print_func(HEADER % {'title': escape(' '.join(sys.argv)),
                         'css_link': css_link,
                        })


def output_html(differences, css_url=None, print_func=None, max_page_size=None):
    if print_func is None:
        print_func = print
    if max_page_size is None:
        max_page_size = DEFAULT_MAX_PAGE_SIZE
    print_func = create_limited_print_func(print_func, max_page_size)
    try:
        output_header(css_url, print_func)
        for difference in differences:
            output_difference(difference, print_func)
    except PrintLimitReached:
        logger.debug('print limit reached')
        print_func("<div class='error'>Max output size reached.</div>",
                   force=True)
    print_func(FOOTER % {'version': VERSION}, force=True)
