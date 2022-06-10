#!/usr/bin/python

"""
Script to search and replace strings in CNGT EAFs.
"""

import sys
import getopt
from CNGT_scripts.python.filecollectionprocessing.filecollectionprocessor import FileCollectionProcessor
from CNGT_scripts.python.filecollectionprocessing.eafprocessor import EafProcessor


class UnusedLingtypeRemover(EafProcessor):
    """

    """

    def process_eaf(self, eaf, file_name):
        print("EAF file: " + file_name)
        to_remove = []
        for lingtype_name in eaf.linguistic_types:
            if len(eaf.get_tier_ids_for_linguistic_type(lingtype_name)) == 0:
                to_remove.append(lingtype_name)
        for lingtype_to_remove in to_remove:
            print(lingtype_to_remove)
            del eaf.linguistic_types[lingtype_to_remove]


if __name__ == "__main__":
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            " -o <output directory>"

    # Set default values
    output_dir = None
    excel_with_changes = None
    first_data_row = None

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
    file_collection_processor = FileCollectionProcessor(file_list, output_dir=output_dir, extensions_to_process=["eaf"])
    remover = UnusedLingtypeRemover()
    file_collection_processor.add_file_processor(remover)
    file_collection_processor.run()
