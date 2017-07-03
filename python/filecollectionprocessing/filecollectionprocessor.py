#!/usr/bin/python

"""
Abstract class that can be used to process a collection of files
"""

from __future__ import print_function

import sys
import os

from filecollectionprocessing.fileprocessor import FileProcessor


class FileCollectionProcessor:
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

        self.file_processors = {}

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

    def add_file_processor(self, file_processor, extension):
        """
        Adds a file processor to the collection of file processors
        :param file_processor: 
        :param extension: 
        :return: 
        """
        if not isinstance(file_processor, FileProcessor):
            raise TypeError("file_processor must have type FileProcessor")
        if not isinstance(extension, str):
            raise TypeError("file_processor must have type str")

        file_processor.set_output_dir(self.output_dir)

        if extension not in self.file_processors:
            self.file_processors[extension] = [file_processor]
        else:
            self.file_processors[extension].append(file_processor)


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
        extension = os.path.splitext(os.path.basename(file_name))[1][1:]
        if extension in self.file_processors:
            for file_processor in self.file_processors[extension]:
                file_processor.process_file(file_name)