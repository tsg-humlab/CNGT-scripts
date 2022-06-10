#!/usr/bin/python

"""
ASL EAF restructuring

Uses pympi (https://github.com/dopefishh/pympi) for the EAF specific processing.
"""

from __future__ import print_function

import getopt
import os
import sys
import re
from urlparse import urlparse
from pympi.Elan import Eaf


class AslEafRestructurer:
    def __init__(self, eaf_files, output_dir=None):
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

        gloss_lingtypes = ["Gloss Child", "Gloss Adult"]
        external_ref = "ecv_ref"
        ecv_name = "ASL Signbank lexicon"

        try:
            eaf = Eaf(file_name)

            # Add linguistic types
            for lingtype in gloss_lingtypes:
                eaf.add_linguistic_type(lingtype, constraints=None)

            # Add linguistic types to tiers
            gloss_tiers = self.find_gloss_tiers(eaf)
            for tier in gloss_tiers:
                if "Adult" in tier:
                    eaf.tiers[tier][2]['LINGUISTIC_TYPE_REF'] = "Gloss Adult"
                elif "Child" in tier:
                    eaf.tiers[tier][2]['LINGUISTIC_TYPE_REF'] = "Gloss Child"

            # Add an ECV external reference
            eaf.add_external_ref(external_ref, "ecv", "http://applejack.science.ru.nl/asl-signbank/static/ecv/asl.ecv")

            # Add a Controlled Vocabulary
            eaf.add_controlled_vocabulary(ecv_name, external_ref)

            # Add the CV to linguistic types
            for lingtype in gloss_lingtypes:
                eaf.linguistic_types[lingtype]['CONTROLLED_VOCABULARY_REF'] = ecv_name

            eaf.to_file(self.output_dir + os.sep + os.path.basename(urlparse(file_name).path), pretty=True)
        except IOError:
            print("The EAF %s could not be processed." % file_name, file=sys.stderr)
            print(sys.exc_info()[0])

    def find_gloss_tiers(self, eaf):
        tier_names = eaf.get_tier_names()
        gloss_tiers = []
        for name in tier_names:
            if name.endswith("left hand") or name.endswith("right hand"):
                gloss_tiers.append(name)
        return gloss_tiers


if __name__ == "__main__":
    # -c ffprobe command if it is not ffprobe (e.g. avprobe on Ubuntu)
    # -v Directory containing video files
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            " -o <output directory>"

    # Set default values
    output_dir = None

    # Register command line arguments
    opt_list, file_list = getopt.getopt(sys.argv[1:], 'c:o:v:m:')
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
    aslEafRestructurer = AslEafRestructurer(file_list, output_dir)
    aslEafRestructurer.run()
