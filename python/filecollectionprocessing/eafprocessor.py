#!/usr/bin/python

"""
Abstract class that can be used to process EAF files
"""

from __future__ import print_function

import sys
import os
from pympi.Elan import Eaf
from urllib.parse import urlparse
from filecollectionprocessing.fileprocessor import FileProcessor


class EafProcessor(FileProcessor):
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