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

    def is_modified(self):
        # Check firstly for differences in modification time
        prev_stat = self.stat
        curr_stat = get_file_stat(self.infile)
        if curr_stat.st_mtime == prev_stat.st_mtime:
            return False

        if self.onlytime:
            self.stat = curr_stat
            return True

        # If modification time is not equal, compare size
        if curr_stat.st_size != prev_stat.st_size:
            self.stat = curr_stat
            return True

        # If no differences seen, so check for differences in checksum
        self.infile.seek(0)
        curr_checksum = get_file_checksum(self.infile)
        if curr_checksum != self.checksum:
            self.checksum = curr_checksum
            return True

        # Non modified file
        return False


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


class MRTemplate(string.Template):
    _delext = True

    delimiter = '@'
    idpattern = r'[_a-z][-_a-z0-9]*'

    def delext(self, mapping, key):
        todel = False
        if key.endswith("-ext"):
            key = key[:-4]
            todel = True

        # We use this idiom instead of str() because the latter
        # will fail if val is a Unicode containing non-ASCII
        val = '%s' % (mapping[key],)

        if todel:
            return os.path.splitext(val)[0]
        else:
            return val

    def safe_substitute(self, *args, **kws):
        if len(args) > 1:
            raise TypeError('Too many positional arguments')
        if not args:
            mapping = kws
        elif kws:
            mapping = _multimap(kws, args[0])
        else:
            mapping = args[0]
        # Helper function for .sub()
        def convert(mo):
            named = mo.group('named')
            if named is not None:
                try:
                    return self.delext(mapping, named)
                except KeyError:
                    return self.delimiter + named
            braced = mo.group('braced')
            if braced is not None:
                try:
                    return self.delext(mapping, braced)
                except KeyError:
                    return self.delimiter + '{' + braced + '}'
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                return self.delimiter
            raise ValueError('Unrecognized named group in pattern',
                             self.pattern)
        return self.pattern.sub(convert, self.template)


ERROR_GETOPT = 1
ERROR_NOARG = 2
ERROR_NOTFILE = 3
ERROR_COMMAND = 4

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                # short options
                "batc:f:",
                ["change-workdir", "no-change-workdir", "only-time"])
    except getopt.GetoptError, err:
        print err
        sys.exit(ERROR_GETOPT)

    before = False
    command = None
    chworkdir = True
    onlytime = False
    files = []
    for option, arg in opts:
        if option == "-c":
            command = arg
        elif option == "-b":
            before = True
        elif option == "-a":
            before = False
        elif option == "-f":
            if not os.path.isfile(arg):
                print "'%s' doesn't exist or is not a valid file" % arg
                sys.exit(ERROR_NOTFILE)
            files.append(arg)
        elif option == "--no-change-workdir":
            chworkdir = False
        elif option == "--change-workdir":
            chworkdir = True
        elif option in ("-t", "--only-time"):
            onlytime = True

    if args:
        files.insert(0, args[0])
        if not os.path.isfile(files[0]):
            print "'%s' doesn't exist or is not a valid file" % files[0]
            sys.exit(ERROR_NOTFILE)
    elif not files:
        print "Program needs at least a file to monitor"
        sys.exit(ERROR_NOARG)

    if not command:
        print "No command passed. You can pass via -c switch"
        sys.exit(ERROR_COMMAND)

    # substitute any @{file} from command string by the monitoring file path
    command = MRTemplate(command).safe_substitute({"file": files[0]})

    # set the working dir, if asked
    if chworkdir:
        dirname = os.path.dirname(files[0])
        if dirname != "":
            os.chdir(dirname)

    # execute the command once before
    if before:
        os.system(command)

    try:
        s = 's' if len(files) > 1 else ''
        print "[MONRUN] Using '%s' as working dir" % os.getcwd()
        print "[MONRUN] Monitoring file%s for modifications" % s
        if not onlytime:
            print "[MONRUN] Calculating checksum%s for the first time" % s

        fileinfos = [FileInfo(file(f), onlytime) for f in files]
        while True:
            # Verifying files
            time.sleep(1)
            for i in range(len(fileinfos)):
                finfo = fileinfos[i]
                if finfo.is_modified():
                    os.system(command)
                    break
    except KeyboardInterrupt:
        print "Execution interrupted"


if __name__ == "__main__":
    main()
