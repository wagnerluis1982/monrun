Description
===========

MonRun (Monitor and Run) is as simple Python script to monitor a file for
changes and execute a command each time the file is changed.

How to use
==========

The single way to use is executing

    $ python monrun.py -c <COMMAND> <FILE>

if you want that the command is once executed before start monitoring, use the
`-b` switch as followed.

    $ python monrun.py -b -c <COMMAND> <FILE>

A `-a` switch is also available to override a previous -b or vice versa.

To do
=====

- Add a `-t` switch to pass time between checks (currently the time is hardcoded
  in 1 second).
