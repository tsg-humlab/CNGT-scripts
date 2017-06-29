#!/usr/bin/python

"""
Abstract class that can be used to process EAF files
"""

from __future__ import print_function

import sys
import getopt
import os
from pympi.Elan import Eaf
from urllib.parse import urlparse


class EafProcessor:
    def __init__(self, eaf_files, output_dir=None, **kwargs):
        self.settings = kwargs

        if output_dir:
            self.output_dir = output_dir.rstrip(os.sep)
            if not os.path.isdir(self.output_dir):
                if os.path.exists(self.output_dir):
                    print("The desired output directory '%s' refers to an existing file." % self.output_dir,
                          file=sys.stderr)
                    exit()
                else:
                    os.mkdir(self.output_dir, 0o750)

        # Find all files recursively and add to a list
        self.all_files = []
        for f in eaf_files:
            self.add_file(f)

    def add_file(self, fname):
        """
        Adds a file name to the list of files to process. Checks if the file
        is a EAF file. If the file name refer to a directory, the directory
        is walked through recursively.

        :param fname: the file name to add to the list of files to process
        :return:
        """
        if os.path.isfile(fname):
            if fname.endswith(".eaf"):
                self.all_files.append(fname)
        elif os.path.isdir(fname):
            files_in_dir = os.listdir(fname)
            for f in files_in_dir:
                self.add_file(fname + os.sep + f)
        else:
            print("No such file of directory: " + fname, file=sys.stderr)

    def run(self):
        """
        For each file in the list of files, processing is started.

        :return:
        """
        if len(self.all_files) > 0:
            for f in self.all_files:
                self.process_file(f)
        else:
            print("No EAF files to process.", file=sys.stderr)

    def process_file(self, file_name):
        """
        Processes one file.

        :param file_name:
        :return:
        """
        try:
            eaf = Eaf(file_name)
            self.process_eaf(eaf, file_name)
            eaf.to_file(self.output_dir + os.sep + os.path.basename(urlparse(file_name).path), pretty=True)
        except IOError:
            print("The EAF %s could not be processed." % file_name, file=sys.stderr)
            print(sys.exc_info()[0])

    def process_eaf(self, eaf, file_name):
        pass
