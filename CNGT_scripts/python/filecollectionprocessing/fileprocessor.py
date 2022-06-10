#!/usr/bin/python

"""
Abstract class that can be used to process a file in an instance of filecollectionprocessing
"""

class FileProcessor:
    def __init__(self):
        self.output_dir = ""

    def process_file(self):
        pass

    def set_output_dir(self, output_dir):
        self.output_dir = output_dir

    def get_extensions(self):
        pass