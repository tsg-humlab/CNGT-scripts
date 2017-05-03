#!/usr/bin/python

"""
Cleans ELAN files (.eaf)

Actions:
* Puts all elements directly under ANNOTATION_DOCUMENT in the correct order
"""

from __future__ import print_function

from lxml import etree
import getopt
import os
import sys


class EafCleaner:
    def __init__(self, eaf_files, output_dir=None):
        if output_dir:
            self.output_dir = output_dir.rstrip(os.sep)

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

        # Parse the xml file
        annotation_document = etree.parse(file_name).getroot()

        # Do the cleaning
        self.correct_element_order(annotation_document)

        # Output the result
        print(etree.tostring(annotation_document, pretty_print=True, encoding="UTF-8", xml_declaration=True))

    def correct_element_order(self, annotation_document):
        """
        Puts the elements under the root in the correct order.
        :param annotation_document:
        :return:
        """
        element_names = ['license', 'header', 'time_order', 'tier', 'linguistic_type', 'locale', 'language',
                         'constraint', 'controlled_vocabulary', 'lexicon_ref', 'external_ref']

        # Use list items of element_names as key in the temporary list
        temp_element_list = {name:[] for name in element_names}

        for child in annotation_document:
            # Delete child from parent
            annotation_document.remove(child)

            # Put in the temporary element list
            tag = child.tag.lower()
            temp_element_list[tag].append(child)

        for name in element_names:
            for element in temp_element_list[name]:
                annotation_document.append(element)


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
    eaf_cleaner = EafCleaner(file_list, output_dir)
    eaf_cleaner.run()