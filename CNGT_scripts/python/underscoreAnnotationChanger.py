#!/usr/bin/python

"""
Script to add Signbank as a lexicon to the CNGT EAFs.
"""

import sys
import getopt
from CNGT_scripts.python.filecollectionprocessing.filecollectionprocessor import FileCollectionProcessor
from CNGT_scripts.python.filecollectionprocessing.eafprocessor import EafProcessor

# Settings
gloss_substrings_to_change = set(['_EC_', '_HC_', '_CL_'])

class UnderscoreAnnotationChanger(EafProcessor):
    """
    
    """

    def __init__(self):
        pass

    def process_eaf(self, eaf, file_name):
        print("EAF file: " + file_name)
        for subject_id in [1, 2]:
            for hand in ['L', 'R']:
                # Get Gloss tier
                gloss_tier_id = 'Gloss' + hand + ' S' + str(subject_id)
                gloss_tier = eaf.tiers[gloss_tier_id]
                participant = eaf.get_parameters_for_tier(gloss_tier_id).get('PARTICIPANT', '')

                # Get ClassType tier
                classtype_tier_id = 'ClassType' + hand + ' S' + str(subject_id)
                if not classtype_tier_id in eaf.tiers:
                    eaf.add_tier(classtype_tier_id, gloss_tier_id, parent=gloss_tier_id, part=participant)
                # classtype_tier = eaf.tiers[classtype_tier_id]

                for gloss_ann_id, gloss_ann_contents in gloss_tier[0].items():
                    annotation_value = gloss_ann_contents[2]

                    # Find which annotations to change are found in the gloss
                    substrings_found = [substring for substring in gloss_substrings_to_change
                                        if substring in annotation_value]


                    if len(substrings_found) == 1:
                        substring = substrings_found[0]
                        annotation_characters = substring.replace('_', '')

                        new_value = annotation_value.replace(substring, '+')
                        new_annotation_contents = (gloss_ann_contents[0], gloss_ann_contents[1], new_value,
                                                   gloss_ann_contents[3], gloss_ann_contents[4])
                        gloss_tier[0][gloss_ann_id] = new_annotation_contents

                        # Add new annotation on ClassType tier
                        eaf.add_ref_annotation(classtype_tier_id, gloss_tier_id, eaf.timeslots[gloss_ann_contents[0]],
                                               annotation_characters)
                    else:
                        # Either zero (nothing to do) or more than (unsure what to do)
                        pass


if __name__ == "__main__":
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            " -o <output directory>" + \
            " -s <substrings, comma separated, no spaces>"

    # Set default values
    output_dir = None
    substrings = None

    # Register command line arguments
    opt_list, file_list = getopt.getopt(sys.argv[1:], 'o:s:')
    for opt in opt_list:
        if opt[0] == '-o':
            output_dir = opt[1]
        if opt[0] == '-s':
            substrings = opt[1]

    # Check for errors and report
    errors = []
    if file_list is None or len(file_list) == 0:
        errors.append("No files or directories given.")

    if len(errors) != 0:
        print("Errors:")
        print("\n".join(errors))
        print(usage)
        exit(1)

    if substrings:
        gloss_substrings_to_change = substrings.split(',')

    # Report registered options
    print("OPTIONS", file=sys.stderr)
    print("Files: " + ", ".join(file_list), file=sys.stderr)
    print("Annotations to change: " + str(gloss_substrings_to_change), file=sys.stderr)

    # Build and run
    file_collection_processor = FileCollectionProcessor(file_list, output_dir=output_dir, extensions_to_process=["eaf"])
    glossChanger = UnderscoreAnnotationChanger()
    file_collection_processor.add_file_processor(glossChanger)
    file_collection_processor.run()
