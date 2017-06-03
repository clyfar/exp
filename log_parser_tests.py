#!/usr/bin/env python
# Author: Geoffrey Golliher (brokenway@gmail.com)

import os
import unittest

import log_parser

class TestLogParser(unittest.TestCase):
    def setUp(self):
        self.offset_path = 'test_data/offset'
        self.logfile_path = 'test_data/sample.log'
        self.new_logfile_path = 'test_data/sample.2.log'
        self.ctime_path = 'test_data/ctime_file'
        log_parser.offset_path = self.offset_path
        log_parser.logfile_path = self.logfile_path
        log_parser.ctime_path = self.ctime_path


class TestLogParserFunctions(TestLogParser):

    def test_check_range(self):
        self.assertEqual(log_parser.check_range(202), '20x')
        self.assertFalse(log_parser.check_range(402) == '20x')

    def test_get_offset(self):
        self.assertFalse(os.path.isfile(self.offset_path))
        log_parser.offset_path = self.offset_path
        self.assertEqual(log_parser.get_offset(), 0)
        self.assertTrue(os.path.isfile(self.offset_path))
        os.remove(self.offset_path)

    def test_set_offset(self):
        log_parser.offset_path = self.offset_path
        self.assertEqual(log_parser.get_offset(), 0)
        self.assertTrue(os.path.isfile(self.offset_path))
        f = open(self.logfile_path)
        f.seek(1231234)
        log_parser.set_offset(f)
        self.assertTrue(log_parser.get_offset(), 1231234)
        log_parser.set_offset(f, True)
        self.assertTrue(log_parser.get_offset(), 0)
        os.remove(self.offset_path)

    def test_set_ctime(self):
        self.assertEqual(log_parser.get_offset(), 0)
        self.assertTrue(os.path.isfile(self.offset_path))
        log_parser.set_ctime()
        self.assertTrue(os.path.isfile(self.ctime_path))
        self.assertTrue(log_parser.get_ctime(1231234) > 12341234)
        os.remove(self.offset_path)
        os.remove(self.ctime_path)

    def test_get_log(self):
        f = log_parser.get_log()
        self.assertTrue(log_parser.get_ctime(1231234) > 12341234)
        self.assertEqual(log_parser.get_offset(), 0)
        self.assertEqual(f.tell(), 0)
        f.close()
        os.remove(self.offset_path)
        os.remove(self.ctime_path)

    def test_process_log(self):
        f = log_parser.get_log()
        log_parser.process_log(f)
        self.assertEqual(log_parser.return_code_map['20x'], 3661)
        self.assertEqual(log_parser.return_code_map['30x'], 40)
        self.assertEqual(log_parser.return_code_map['40x'], 155)
        self.assertEqual(log_parser.return_code_map['50x'], 1)
        self.assertEqual(log_parser.route_map['/api/v1/secure/payment_methods'], 48)
        os.remove(self.offset_path)
        os.remove(self.ctime_path)


if __name__ == '__main__':
    unittest.main()
