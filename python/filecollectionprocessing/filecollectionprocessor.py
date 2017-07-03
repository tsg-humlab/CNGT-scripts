#!/usr/bin/python

"""
Abstract class that can be used to process a collection of files
"""

from __future__ import print_function

import sys
import os

from filecollectionprocessing.fileprocessor import FileProcessor


class FileCollectionProcessor:
    def __init__(self, file_names, output_dir=None, extensions_to_process=[], **kwargs):
        self.settings = kwargs

        if output_dir is not None:
            self.output_dir = output_dir.rstrip(os.sep)
            if not os.path.isdir(self.output_dir):
                if os.path.exists(self.output_dir):
                    print("The desired output directory '%s' refers to an existing file." % self.output_dir,
                          file=sys.stderr)
                    exit()
                else:
                    os.mkdir(self.output_dir, 0o750)

        self.extensions_to_process = extensions_to_process

        # Find all files recursively and add to a list
        self.all_files = []
        for file_name in file_names:
            self.add_file(file_name)

        self.file_processors = {}

    def add_file(self, file_name):
        """
        Adds a file name to the list of files to process. Checks if the file
        is of a type to process (checked using the extension. If the file name 
        refer to a directory, the directory is walked through recursively.

        :param file_name: the file name to add to the list of files to process
        :return:
        """
        if os.path.isfile(file_name):
            extension = os.path.splitext(os.path.basename(file_name))[1][1:]
            if len(self.check_file_extensions([extension])) > 0:
                self.all_files.append(file_name)
        elif os.path.isdir(file_name):
            files_in_dir = os.listdir(file_name)
            for f in files_in_dir:
                self.add_file(file_name + os.sep + f)
        else:
            print("No such file of directory: " + file_name, file=sys.stderr)

    def check_file_extensions(self, extensions):
        """
        Checks whether the file extension is among the ones to process.
        If there are no extensions to process, this is always true.
        :param extensions: 
        :return: 
        """
        if len(self.extensions_to_process) == 0:
            return extensions

        return list(filter(lambda elem: elem in self.extensions_to_process, extensions))

    def add_file_processor(self, file_processor):
        """
        Adds a file processor to the collection of file processors
        :param file_processor: 
        :return: 
        """
        if not isinstance(file_processor, FileProcessor):
            raise TypeError("file_processor must have type FileProcessor")

        extensions = file_processor.get_extensions()
        if not (isinstance(extensions, list) and all(isinstance(elem, str) for elem in extensions)):
            raise TypeError("extensions must be a list of strings")

        extension_to_register = self.check_file_extensions(extensions)
        if len(extension_to_register) == 0:
            raise Exception("extension(s) '%s' are not among the extensions to process" % ", ".join(extensions))

        file_processor.set_output_dir(self.output_dir)

        for extension in extension_to_register:
            if extension not in self.file_processors:
                self.file_processors[extension] = [file_processor]
            else:
                self.file_processors[extension].append(file_processor)


    def run(self):
        """
        For each file in the list of files, processing is started.

        :return:
        """
        if len(self.file_processors) == 0:
            print("No file processors registered.", file=sys.stderr)
        elif len(self.all_files) == 0:
            print("No files to process.", file=sys.stderr)
        else:
            for f in self.all_files:
                self.process_file(f)

    def process_file(self, file_name):
        extension = os.path.splitext(os.path.basename(file_name))[1][1:]
        if extension in self.file_processors:
            for file_processor in self.file_processors[extension]:
                file_processor.process_file(file_name)
