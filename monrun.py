#!/usr/bin/env python

# Copyright 2013 Wagner Macedo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import getopt
import hashlib
import os
import string
import sys
import time


class FileInfo:
    def __init__(self, infile, onlytime=False):
        self.infile = infile
        self.onlytime = onlytime
        self.stat = get_file_stat(infile)
        self.checksum = None if onlytime else get_file_checksum(infile)


def get_file_checksum(infile, block_size=2**10):
    md5 = hashlib.md5()
    while True:
        data = infile.read(block_size)
        if not data:
            break

        md5.update(data)

    return md5.digest()


def get_file_stat(infile):
    return os.fstat(infile.fileno())


def is_modified(finfo):
    # Check firstly for differences in modification time
    prev_stat = finfo.stat
    curr_stat = get_file_stat(finfo.infile)
    if curr_stat.st_mtime == prev_stat.st_mtime:
        return False

    if finfo.onlytime:
        finfo.stat = curr_stat
        return True

    # If modification time is not equal, compare size
    if curr_stat.st_size != prev_stat.st_size:
        finfo.stat = curr_stat
        return True

    # If no differences seen, so check for differences in checksum
    finfo.infile.seek(0)
    curr_checksum = get_file_checksum(finfo.infile)
    if curr_checksum != finfo.checksum:
        finfo.checksum = curr_checksum
        return True

    # Non modified file
    return False


ERROR_GETOPT = 1
ERROR_NOARG = 2
ERROR_NOTFILE = 3
ERROR_COMMAND = 4

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                # short options
                "batc:",
                ["change-workdir", "no-change-workdir", "only-time"])
    except getopt.GetoptError, err:
        print err
        sys.exit(ERROR_GETOPT)

    if not args:
        print "Program needs a file to monitor"
        sys.exit(ERROR_NOARG)

    FILE_PATH = args[0]
    if not os.path.isfile(FILE_PATH):
        print "Argument passed is not a file"
        sys.exit(ERROR_NOTFILE)

    before = False
    command = None
    chworkdir = True
    onlytime = False
    for option, arg in opts:
        if option == "-c":
            command = arg
        elif option == "-b":
            before = True
        elif option == "-a":
            before = False
        elif option == "--no-change-workdir":
            chworkdir = False
        elif option == "--change-workdir":
            chworkdir = True
        elif option in ("-t", "--only-time"):
            onlytime = True

    if not command:
        print "No command passed. You can pass via -c switch"
        sys.exit(ERROR_COMMAND)

    # substitute any ${file} from command string by the monitoring file path
    command = string.Template(command).safe_substitute({"file": FILE_PATH})

    # set the working dir, if asked
    if chworkdir:
        dirname = os.path.dirname(FILE_PATH)
        if dirname != "":
            os.chdir(dirname)

    if before:
        os.system(command)

    try:
        print "[MONRUN] Using '%s' as working dir" % os.getcwd()
        with open(FILE_PATH) as f:
            print "[MONRUN] Monitoring file for modifications"
            if not onlytime:
                print "[MONRUN] Calculating checksum for the first time"

            file_info = FileInfo(f, onlytime)
            while True:
                time.sleep(1)
                if is_modified(file_info):
                    os.system(command)
    except KeyboardInterrupt:
        print "Execution interrupted"


if __name__ == "__main__":
    main()
