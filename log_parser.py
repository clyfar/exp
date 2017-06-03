#!/usr/local/bin/python
# Author: Geoffrey Golliher (brokenway@gmail.com)

##
# This module will parse a given logfile and output statsd compatible messages.
##

import optparse
import os.path
import re

return_code_map = {}
route_map = {}

time = '^.*\[([0-9]+/[a-zA-Z]{3}/[0-9]{4}:[0-9]{2}:[0-9]{2}:[0-9]{2}..[0-9]{4})\].+'
route = '(GET|POST|DELETE|HEAD).(.+)'
status = 'HTTP/1.[0-1]..([0-9]{3})'
reg = re.compile(time+route+status)

offset_path = 'offset'
ctime_path = 'ctime_file'
log_path = 'sample.log'

ranges = {'20x': range(200, 300),
          '30x': range(300, 400),
          '40x': range(400, 500),
          '50x': range(500, 600)}

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
        offset = open(offset_path, 'r+')
    except IOError as e:
        offset = open(offset_path, 'a+')
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
    offset = open(offset_path, 'w')
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
        octime = open(ctime_path, 'r+')
    except IOError as e:
        octime = open(ctime_path, 'a+')
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
        octime = open(ctime_path, 'w')
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
    parser = optparse.OptionParser(
    """Usage: %prog [options]

       Example:
       %prog -l sample.log
    """, version="%prog .01")

    parser.add_option("-l", "--logfile", dest="log_path", help="Specify logfile.",
            default='sample.log')
    (options, args) = parser.parse_args()

    if options.log_path:
        log_path = options.log_path

    f = get_log()
    process_log(f)
    print_statsd_messages()

