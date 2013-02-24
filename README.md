Description
===========

monrun (Monitor and Run) is as simple Python script to monitor a file for
changes and execute a command each time the file is changed.

How to use
==========

The single way to use is executing

    $ python monrun.py -c <COMMAND> <FILE>

if you want that the command is once executed before start monitoring, use the
`-b` switch as followed.

    $ python monrun.py -b -c <COMMAND> <FILE>

A `-a` switch is also available to override a previous `-b` or vice versa.

Why
===

Well, I couldn't find a program that do exactly what monrun do and I decided to
write my own. Could be that this program exists and I was not able to find.

Normally all similar utilities only monitor for file modification time, while
monrun do in the following way:

1. Checks for difference in the modification time (mtime).
2. If mtime is not equals, checks for difference in the file size.
3. If file size is equals, is not a guarantee that the file is really modified,
   so monrun checks for difference calculating it checksum via md5.

To do
=====

- Add a `-t` switch to pass time between checks (currently the time is hardcoded
  in 1 second).
