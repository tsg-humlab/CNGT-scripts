#!/usr/bin/python

"""
ASL EAF transformation

Uses pympi (https://github.com/dopefishh/pympi) for the EAF specific processing.
"""

from __future__ import print_function

import getopt
import os
import sys
import re
from urlparse import urlparse
from pympi.Elan import Eaf


class AslEafTransformer:
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

        gloss_append_lingtype = "gloss-append"

        try:
            eaf = Eaf(file_name)
            eaf.add_linguistic_type(gloss_append_lingtype, constraints="Symbolic_Association")
            gloss_tiers = self.find_gloss_tiers(eaf)
            self.add_gloss_tier_children(eaf, gloss_tiers, gloss_append_lingtype)
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

    def add_gloss_tier_children(self, eaf, gloss_tiers, gloss_append_lingtype):
        for tier in gloss_tiers:
            child_tier = tier.replace("left hand", "LH").replace("right hand", "RH") + " append"
            eaf.add_tier(child_tier, parent=tier, ling=gloss_append_lingtype)

            # Extract annotation appendices and put them on the child tier
            #annotations = eaf.get_annotation_data_for_tier(tier)
            annotations = eaf.tiers[tier][0]
            for annotation_id, annotation in annotations.iteritems():
                # take the middle time as described in
                # http://dopefishh.github.io/pympi/Elan.html#pympi.Elan.Eaf.add_ref_annotation
                time = (eaf.timeslots[annotation[1]] + eaf.timeslots[annotation[0]])/2

                value = annotation[2]
                (new_value, appendix) = self.get_annotation_appendix(value)

                if appendix:
                    # Change annotation value on parent tier
                    eaf.tiers[tier][0][annotation_id] = (annotation[0], annotation[1], new_value, annotation[3])
                    # Add a new annotation on the child tier
                    eaf.add_ref_annotation(child_tier, tier, time, appendix)

    def get_annotation_appendix(self, value):
        # Handle the non splitting cases first
        match_object = re.match(r'(IX|POSS|HONORIFIC)\(self\)', value)
        if match_object is not None:
            new_value = value.replace('(self)', '_1')
            return value, None

        # Handle the splitting cases

        # All possible appendices
        regexes = [
            r'(.*?)(\/{1,2})',  # / or //
            r'(.*?)(\[\/{1,3}\])',  # [/] or [//] or [///]
            r'(.*?)(\[[_\+\?]\])',  # [_] or [+] or [?]
            r'(.*?)(\.{3})',  # ...
            r'(.*?)(#)',  # #
            r'(.*?)(\[=\?.*?\])',  # [=?ALTERNATIVE] note that 'ALTERNATIVE' is replaced by some gloss;
                                   # whatever is included in the square brackets should all go on the
                                   # relevant append tier

            r'(FS|NS|IX|POSS|HONORIFIC|IXtracing)(\(.*?\))',  # fingerspelling, depicting signs, etc

            # The DS stuff (a shorter regex would mess up the match group indexes below)
            r'(DS_1|DS_2|DS_3|DS_4|DS_5|DS_a|DS_b|DS_b2|DS_b5|DS_bl|DS_bo|DS_c|DS_cx|DS_e)(\(.*?\))',
            r'(DS_f5|DS_fc|DS_fo|DS_g|DS_h|DS_i|DS_L|DS_of|DS_oh|DS_s|DS_t|DS_x|DS_y|DS\(ca\))(\(.*?\))',
        ]

        first_part = value
        second_part = ""
        for regex in regexes:
            match_object = re.match(regex, first_part)
            if match_object is not None:
                if len(match_object.groups()) == 2:
                    # Move suffix to second part
                    first_part = match_object.groups()[0]
                    second_part = match_object.groups()[1] + second_part

        return first_part, second_part

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
    aslEafTransformer = AslEafTransformer(file_list, output_dir)
    aslEafTransformer.run()
