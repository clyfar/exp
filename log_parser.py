#!/usr/bin/env python
# Author: Geoffrey Golliher (brokenway@gmail.com)

"""This module will parse a given logfile and output statsd compatible messages.

There are a couple of files that are used to make sure we can parse a log every n seconds:

  1. There is an offset file used to track the number of bytes read into the logfile
     at the last interval. The offset is used to start reading the log again at the
     last offset.
  2. There is a ctime file which keeps track of the logfile's creation time. The use
     of this file allows the program to continue reading the canonical log even if it
     is rotated.

  sys level errors returned are:
      1 - a locking error when the file didn't exist at the start of the function.
      2 - a locking error when an exclusive lock already exists on the lock file.
"""

import fcntl
import optparse
import os.path
import re
import sys

return_code_map = {}
route_map = {}

time = '^.*\[([0-9]+/[a-zA-Z]{3}/[0-9]{4}:[0-9]{2}:[0-9]{2}:[0-9]{2}..[0-9]{4})\].+'
route = '(GET|POST|DELETE|HEAD).(.+)'
status = 'HTTP/1.[0-1]..([0-9]{3})'
reg = re.compile(time+route+status)

offset_file = 'offset'
ctime_file = 'ctime_file'
log_path = 'sample.log'
lock_file = 'log_parser_lock'

ranges = {'20x': range(200, 300),
          '30x': range(300, 400),
          '40x': range(400, 500),
          '50x': range(500, 600)}

def get_lock():
    """Will grab and lock a file. The file is used to ensure this program will not runover itself.

    Returns:
        File handle.
    """
    if not os.path.exists(lock_file):
        fl = open(lock_file, 'a+')
        try:
            fcntl.lockf(fl, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as e:
            if e.errno not in (errno.EACCES, errno.EAGAIN):
                # Something else started. This is not likely.
                raise(IOError, 'already locked')
                sys.exit(1)
    else:
        fl = open(lock_file, 'r+')
        try:
            fcntl.lockf(fl, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as e:
            # File is lready locked.
            raise(IOError, 'already locked')
            sys.exit(2)
    return fl

def release_lock(fl):
    """Will release the lock on the lock_file.

    Args:
        fl: File handle for the lock_file.

    Returns:
        None.
    """
    try:
        fcntl.lockf(fl, fcntl.LOCK_UN)
    except IOError as e:
        sys.exit(3)

def check_range(num):
    """Checks if the number range.

    Args:
        num: int.

    Returns:
        int: The key of the dict if the num is within the range of the value.
    """
    for i in ranges.keys():
        if num in ranges[i]:
            return i

def get_offset():
    """Retrives the offset from the offest file.

    Returns:
        int: offest.
    """
    try:
        offset = open(offset_file, 'r+')
    except IOError as e:
        offset = open(offset_file, 'a+')
    o = offset.readline()
    if len(o) == 0 or o == "\n":
        o = 0
    return o
    offset.close()

def set_offset(f, reset=False):
    """Sets the new offset.

    Args:
        f: file handle.

    Returns:
        None.
    """
    offset = open(offset_file, 'w')
    if reset:
        new_offset = '0'
    else:
        new_offset = str(f.tell())
    offset.write(new_offset)
    offset.close()

def get_ctime(nctime):
    """Gets the previous ctime if there is one.
    If there is no ctime file, this function will create one.

    Args:
        nctime: float of the current logfile's ctime.

    Returns:
        float: previous ctime.
    """
    try:
        octime = open(ctime_file, 'r+')
    except IOError as e:
        octime = open(ctime_file, 'a+')
        octime.write(str(nctime))
    ctime = octime.readline()
    octime.close()
    return ctime

def set_ctime():
    """Sets the new ctime based on current logfile ctime > previous ctime.

    Returns:
        None.
    """
    nctime = os.path.getctime(log_path)
    ctime = get_ctime(nctime)
    if not ctime:
        ctime = nctime
    if float(nctime) > float(ctime):
        set_offset(None, True)
        octime = open(ctime_file, 'w')
        octime.write(str(nctime))
        octime.close()

def get_log():
    """Gets the logfile using the module level path set with log_path.

    Returns:
        file handle: The handle returned will have been seeked to the offset from get_offset.
    """
    set_ctime()
    f = open(log_path, 'r')
    o = get_offset()
    f.seek(int(o))
    return f

def process_log(f):
    """Reads each line of the logfile and matches against the regular expression.
    If there is a match, the tokens are added to the appropriate map.

    Args:
        f: file handle.

    Returns:
        None.
    """
    data = f.readlines()

    for line in data:
        m = re.match(reg, line)
        if m:
            route = m.groups()[2].strip()
            ret_val = m.groups()[3]
            if route not in route_map.keys():
                route_map[route] = 0
            route_map[route] = route_map[route] + 1
            code = check_range(int(ret_val))
            if code not in return_code_map.keys():
                return_code_map[code] = 0
            return_code_map[code] = return_code_map[code] + 1

    set_offset(f)
    f.close()

def print_statsd_messages():
    """Prints the statsd compatible messages to stdout.

    Returns
        None.
    """
    for k, v in return_code_map.items():
        print '{}:{}|s'.format(k, v)
    for k, v in route_map.items():
        print '{}:{}|s'.format(k, v)

if __name__ == '__main__':
    fl = get_lock()

    parser = optparse.OptionParser(
    """Usage: %prog [options]

       Example:
       %prog -l sample.log -o /tmp/offset -c /tmp/ctime
    """, version="%prog .01")

    parser.add_option("-l", "--logfile", dest="logfile", help="Specify logfile.",
            default='sample.log')
    parser.add_option("-o", "--offset_file", dest="offset_file", help="Specify offset file.",
            default='offset')
    parser.add_option("-c", "--ctime_file", dest="ctime_file", help="Specify ctime file.",
            default='ctime')
    parser.add_option("-r", "--reset", dest="reset", action='store_true',
            help="Reset and remove ctime_file and offset_file.", default=False)
    (options, args) = parser.parse_args()

    if options.logfile:
        log_path = options.logfile

    if options.offset_file:
        offset_file = options.offset_file

    if options.ctime_file:
        ctime_file = options.ctime_file

    if options.reset:
        os.remove(ctime_file)
        os.remove(offset_file)
        os.remove(lock_file)

    f = get_log()
    process_log(f)
    release_lock(fl)
    print_statsd_messages()

