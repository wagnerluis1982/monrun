#!/usr/bin/env python3

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

from __future__ import print_function

from functools import reduce

import getopt
import hashlib
import os
import string
import sys
import time


# error codes
ERROR_GETOPT = 1
ERROR_NOARG = 2
ERROR_NOTFILE = 3
ERROR_COMMAND = 4
ERROR_BADARG = 5

# flags
CHECK_TIME = 0b001
CHECK_SIZE = 0b010
CHECK_SUM = 0b100

# mapping of names to flag
map_of_flags = {"time": CHECK_TIME, "size": CHECK_SIZE, "checksum": CHECK_SUM}


class FileInfo:
    def __init__(self, filename, flags):
        self.filename = filename
        self.flags = flags

        if self.has_flags(CHECK_TIME, CHECK_SIZE):
            self.stat = self.get_stat()
        if self.has_flags(CHECK_SUM):
            self.checksum = self.get_checksum()

    def __str__(self):
        return self.filename

    def has_flags(self, *args):
        return all([self.flags & a == a for a in args])

    def is_modified(self):
        if self.has_flags(CHECK_TIME, CHECK_SIZE):
            # Get stats
            prev_stat = self.stat
            curr_stat = self.get_stat()

            if self.has_flags(CHECK_TIME):
                # Check for differences in modification time
                if curr_stat.st_mtime == prev_stat.st_mtime:
                    return False

                # Finish if set to only time
                if not self.has_flags(CHECK_SIZE | CHECK_SUM):
                    self.stat = curr_stat
                    return True

            # Compare size, returns if different
            if self.has_flags(CHECK_SIZE) and \
                    curr_stat.st_size != prev_stat.st_size:
                self.stat = curr_stat
                return True

        # If no differences seen, so check for differences in checksum
        if self.has_flags(CHECK_SUM):
            curr_checksum = self.get_checksum()
            if curr_checksum != self.checksum:
                self.checksum = curr_checksum
                return True

        # Non modified file
        return False

    def get_checksum(self, block_size=2**10):
        md5 = hashlib.md5()
        infile = open(self.filename, "rb")
        while True:
            data = infile.read(block_size)
            if not data:
                break
            md5.update(data)
        infile.close()

        return md5.digest()

    def get_stat(self):
        return os.stat(self.filename)


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
            # val is enquoted?
            if val[0] == val[-1] == '"':
                return os.path.splitext(val)[0] + '"'
            return os.path.splitext(val)[0]
        else:
            return val

    def safe_substitute(self, *args, **kws):
        # To introduce @file-ext special feature, this method was rewritten.
        # Most of the code is repeated from string.Template, since this class
        # doesn't offer a good support to customize this method.

        if len(args) > 1:
            raise TypeError('Too many positional arguments')
        if not args:
            mapping = kws
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


def enquote(filename):
    return '"%s"' % filename.replace('"', r'\"')


def error(*args, **kwargs):
    print(*args, file=sys.stderr)
    errcode = kwargs.get('code')
    if isinstance(errcode, int):
        sys.exit(errcode)


def get_flags(option, arg):
    # get the list of flags by names passed
    flags = arg.split(',')
    for i, name in enumerate(flags):
        flag = map_of_flags.get(name)
        if flag is None:
            error("invalid arg for %s: '%s'" % (option, name),
                  code=ERROR_BADARG)
        flags[i] = flag

    # flags ready to apply
    return reduce(int.__or__, flags)


def get_files(args):
    files = []
    for arg in args:
        if not os.path.isfile(arg):
            error("'%s' doesn't exist or is not a valid file" % arg,
                  code=ERROR_NOTFILE)
        files.append(arg)
    return files


def monitor_and_run(files, command, flags):
    try:
        s = 's' if len(files) > 1 else ''
        print("[MONRUN] Using '%s' as working dir" % os.getcwd())
        print("[MONRUN] Monitoring file%s for modifications" % s)
        if flags & CHECK_TIME:
            print("[MONRUN] Calculating checksum%s for the first time" % s)

        fileinfos = [FileInfo(f, flags) for f in files]
        while True:
            # Verifying files
            time.sleep(1)
            for i in range(len(fileinfos)):
                finfo = fileinfos[i]
                if finfo.is_modified():
                    print("[MONRUN] '%s' changed in" % finfo,
                          time.strftime("%h %e %X"))
                    os.system(command)
                    break
    except KeyboardInterrupt:
        print("Execution interrupted")


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                # short options
                "batc:",
                # long options
                ["chdir", "no-chdir", "command=", "only=", "skip="])
    except getopt.GetoptError as err:
        error(err, code=ERROR_GETOPT)

    before = False
    command = None
    chworkdir = True
    flags = CHECK_TIME | CHECK_SIZE | CHECK_SUM
    for option, arg in opts:
        if option in ("-c", "--command"):
            command = arg
        elif option == "-b":
            before = True
        elif option == "-a":
            before = False
        elif option == "--chdir":
            chworkdir = True
        elif option == "--no-chdir":
            chworkdir = False
        elif option == "--only":
            # replace flags by passed ones
            flags = get_flags(option, arg)
        elif option == "--skip":
            # remove flags of passed ones
            flags ^= get_flags(option, arg)

    files = get_files(args)
    if not files:
        error("Program needs at least a file to monitor", code=ERROR_NOARG)

    if not command:
        error("No command passed. You can pass it via -c switch",
              code=ERROR_COMMAND)

    # substitute any @{file} from command string by the monitoring file path
    command = MRTemplate(command).safe_substitute({"file": enquote(files[0])})

    # set the working dir, if asked
    if chworkdir:
        dirname = os.path.join('.', os.path.dirname(files[0]))
        os.chdir(dirname)

    # execute the command once before
    if before:
        os.system(command)

    # start monitoring forever
    monitor_and_run(files, command, flags)


if __name__ == "__main__":
    main()
