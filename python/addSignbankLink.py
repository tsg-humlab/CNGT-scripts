#!/usr/bin/python

"""
Script to add Signbank as a lexicon to the CNGT EAFs.
"""

from __future__ import print_function

import sys
import getopt
import os
from pympi.Elan import Eaf
from urllib.parse import urlparse

# SETTINGS
# Parameters for the lexicon reference
LEXICON_REF = "signbank-lexicon-ref"
NAME = "NGT-Signbank"
TYPE = "Signbank"
URL = "https://signbank.science.ru.nl/"
LEXICON_ID = "NGT"
LEXICON_NAME = "NGT"
DATCAT_ID = "Annotation Id Gloss: Dutch"
DATCAT_NAME = "Annotation Id Gloss: Dutch"
# Linguistic type id
LINGUISTIC_TYPE_ID = "gloss"


class LexiconLinkAdder:
    def __init__(self, eaf_files, output_dir=None):
        self.output_dir = None
        if output_dir:
            self.output_dir = output_dir.rstrip(os.sep)
            if not os.path.isdir(self.output_dir):
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
            print("File: " + file_name, file=sys.stderr)
            eaf = Eaf(file_name)
            eaf.add_lexicon_ref(LEXICON_REF, NAME, TYPE, URL,
                                LEXICON_ID, LEXICON_NAME, DATCAT_ID, DATCAT_NAME)

            # Remove old referred lexicon
            if LINGUISTIC_TYPE_ID in eaf.linguistic_types:
                if "LEXICON_REF" in eaf.linguistic_types[LINGUISTIC_TYPE_ID]:
                    old_lexicon_ref = eaf.linguistic_types[LINGUISTIC_TYPE_ID]["LEXICON_REF"]
                    del eaf.lexicon_refs[old_lexicon_ref]

            eaf.linguistic_types[LINGUISTIC_TYPE_ID]["LEXICON_REF"] = LEXICON_REF

            if self.output_dir is not None:
                eaf.to_file(self.output_dir + os.sep + os.path.basename(urlparse(file_name).path), pretty=True)
            else:
                eaf.to_file(file_name, pretty=True)
        except Exception:
            print("The EAF %s could not be processed." % file_name, file=sys.stderr)
            print(sys.exc_info()[0])


if __name__ == "__main__":
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            " -o <output directory>"

    # Set default values
    output_dir = None

    # Register command line arguments
    opt_list, file_list = getopt.getopt(sys.argv[1:], 'o:')
    for opt in opt_list:
        if opt[0] == '-o':
            output_dir = opt[1]

    # Check for errors and report
    errors = []
    if file_list is None or len(file_list) == 0:
        errors.append("No files or directories given.")

    if len(errors) != 0:
        print("Errors:")
        print("\n".join(errors))
        print(usage)
        exit(1)

    # Report registered options
    print("OPTIONS", file=sys.stderr)
    print("Files: " + ", ".join(file_list), file=sys.stderr)
    if output_dir is not None:
        print("Output directory: " + output_dir, file=sys.stderr)

    # Build and run
    linkAdder = LexiconLinkAdder(file_list, output_dir)
    linkAdder.run()
