#!/usr/bin/python
#
# This is a rewrite of the perl script
# signCounter.pl

from __future__ import print_function

import getopt
import json
import os
import re
import sys
from lxml import etree
from collections import defaultdict


class SignCounter:
    def __init__(self, metadata_file, maximum_overlap, files):
        self.maximum_overlap = int(maximum_overlap)
        self.all_files = []
        self.metadata = {}
        self.time_slots = {}

        self.freqs = defaultdict(lambda: 0)
        self.freqsPerPerson = defaultdict(lambda: defaultdict(int))
        self.freqsPerRegion = defaultdict(lambda: defaultdict(int))

        for f in files:
            self.add_file(f)

        self.load_metadata(metadata_file)

    def add_file(self, fname):
        if fname.endswith(".eaf"):
            if os.path.isfile(fname):
                self.all_files.append(fname)
            elif os.path.isdir(fname):
                files_in_dir = os.listdir(fname)
                for f in files_in_dir:
                    self.add_file(f)
            else:
                print("No such file of directory: " + fname, file=sys.stderr)

    def load_metadata(self, metadata_file):
        with open(metadata_file) as meta:
            meta.readline()  # Skip first row (header)
            for line in meta.readlines():
                fields = line.split("\t")
                self.metadata[fields[0]] = fields[1]

    def run(self):
        """ """
        if len(self.all_files) > 0:
            for f in self.all_files:
                self.process_file(f)
                self.output_result()
        else:
            print("No EAF files to process.", file=sys.stderr)

    def process_file(self, fname):
        with open(fname) as eaf:
            xml = etree.parse(eaf)
            self.extract_time_slots(xml)
            (list_of_glosses, tier_id_prefix) = self.extract_glosses(xml)
            (list_of_gloss_units) = self.to_units(list_of_glosses, tier_id_prefix)
            self.restructure(list_of_gloss_units)

    def extract_time_slots(self, xml):
        for time_slot in xml.findall("//TIME_SLOT"):
            time_slot_id = time_slot.attrib['TIME_SLOT_ID']
            self.time_slots[time_slot_id] = time_slot.attrib['TIME_VALUE']

    def extract_glosses(self, xml):
        list_of_glosses = {}  # Structure: { $tierID: { "participant":  "...", "annotations": [ { "begin": ..., "end": ..., "id": ..., "participant": ... }, { ... } ] } }
        tier_id_prefix = "Gloss"
        for tier in xml.findall("//TIER"):
            tier_id = tier.attrib['TIER_ID']
            list_of_glosses[tier_id] = {}

            match = re.match(r'^(Gloss?)([LR]) S[12]$', tier_id)
            if match and ('PARENT_REF' not in tier.attrib or tier.attrib['PARENT_REF'] == ''):
                tier_id_prefix = match.group(1)
                hand = match.group(2)
                participant = tier.attrib['PARTICIPANT']
                list_of_glosses[tier_id]["participant"] = participant
                list_of_glosses[tier_id]["annotations"] = []

                for annotation in tier.findall("ANNOTATION/ALIGNABLE_ANNOTATION"):
                    annotation_id = annotation.attrib['ANNOTATION_ID']
                    annotation_data = {
                        "begin": int(self.time_slots[annotation.attrib['TIME_SLOT_REF1']]),
                        "end": int(self.time_slots[annotation.attrib['TIME_SLOT_REF2']]),
                        "id": annotation_id,
                        "value": annotation.find("ANNOTATION_VALUE").text,
                        "participant": participant,
                        "hand": hand
                    }
                    list_of_glosses[tier_id]["annotations"].append(annotation_data)

        return list_of_glosses, tier_id_prefix

    def to_units(self, list_of_glosses, tier_id_start):
        """Turns the list of glosses into a list of units of overlapping glosses.
        :rtype: list of gloss units
        """
        list_of_gloss_units = []  # Structure: [ [ { "begin": ..., "end": ..., "id": ..., "participant": ... } ], [ ] ]
        for signer_id in (1, 2):
            unit = []  # Overlapping glosses are put in a unit.
            last_end_on = ''  # The hand (L or R) of the last seen gloss
            last_end = None  # The end timeSlot of the last seen gloss

            right_tier_id = tier_id_start + "R S" + str(signer_id)
            left_tier_id = tier_id_start + "L S" + str(signer_id)
            if right_tier_id in list_of_glosses and left_tier_id in list_of_glosses:
                right_hand_data = list_of_glosses[right_tier_id]
                left_hand_data = list_of_glosses[left_tier_id]

                if "annotations" in right_hand_data and "annotations" in left_hand_data:
                    right_hand_annotations = right_hand_data['annotations']
                    left_hand_annotations = left_hand_data['annotations']
                    while len(right_hand_annotations) > 0 or len(left_hand_annotations) > 0:
                        if len(right_hand_annotations) > 0 and len(left_hand_annotations) > 0:
                            if right_hand_annotations[0]['begin'] <= left_hand_annotations[0]['begin']:
                                last_end_on = 'R'
                            else:
                                last_end_on = 'L'
                        elif len(right_hand_data['annotations']) > 0:
                            last_end_on = 'R'
                        else:
                            last_end_on = 'L'

                        current_hand_data = list_of_glosses[tier_id_start + last_end_on + " S" + str(signer_id)]
                        current_hand_begin = current_hand_data['annotations'][0]['begin']
                        if last_end is not None and current_hand_begin > (last_end - self.maximum_overlap):
                            # Begin new unit
                            list_of_gloss_units.append(unit)
                            unit = []

                        unit.append(current_hand_data['annotations'][0])

                        current_hand_end = current_hand_data['annotations'][0]['end']
                        if last_end is None or current_hand_end > last_end:
                            last_end = current_hand_end

                        current_hand_data['annotations'].pop(0)

            list_of_gloss_units.append(unit)

        return list_of_gloss_units

    def restructure(self, list_of_glosses):
        for unit in list_of_glosses:
            tmp = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
            for annotation in unit:
                gloss = annotation['value']
                re.sub(r'\n', '', gloss)
                re.sub(r'\t', '', gloss)
                re.sub(r'\s\s+', ' ', gloss)
                re.sub(r'^\s+', '', gloss)
                re.sub(r'\s+$', '', gloss)
                if not gloss == '':
                    tmp[gloss]['participants'][annotation['participant']] += 1

            for gloss in tmp:
                self.freqs[gloss] += 1

                for person in tmp[gloss]['participants']:
                    self.freqsPerPerson[person][gloss] += 1

                    region = self.metadata[person]
                    self.freqsPerRegion[region][gloss] += 1

    def output_result(self):
        number_of_tokens = 0
        number_of_types = 0
        number_of_singletons = 0

        data4json = {}

        # print("Gloss\tFrequency\tFrequency per region")

        for gloss in sorted(self.freqs.keys()):
            # print(gloss + "\t" + str(self.freqs[gloss]), end='')
            number_of_types += 1
            number_of_tokens += self.freqs[gloss]
            if self.freqs[gloss] == 1:
                number_of_singletons += 1

            # Person frequencies
            person_columns = ''
            number_of_signers = 0;
            for person in sorted(self.freqsPerPerson.keys()):
                if gloss in self.freqsPerPerson[person]:
                    person_columns += "\t" + person
                    person_columns += "\t" + str(self.freqsPerPerson[person][gloss])
                    number_of_signers += 1

            # print(person_columns, end='')

            # Region frequencies
            region_columns = ''
            region_frequencies = []
            for region in sorted(self.freqsPerRegion.keys()):
                if gloss in self.freqsPerRegion[region]:
                    region_columns += "\t" + region
                    region_columns += "\t" + str(self.freqsPerRegion[region][gloss])
                    region_frequencies.append({region: self.freqsPerRegion[region][gloss]})

            # print(region_columns)

            data4json[gloss] = {'frequency': self.freqs[gloss], 'numberOfSigners': number_of_signers,
                                    'frequenciesPerRegion': region_frequencies}

        print(json.dumps(data4json, sort_keys=True, indent=4))
        print("#tokens: " + str(number_of_tokens), file=sys.stderr)
        print("#types: " + str(number_of_types), file=sys.stderr)
        print("#singletons: " + str(number_of_singletons), file=sys.stderr)


if __name__ == "__main__":
    usage = "Usage: \n" + sys.argv[0] + "-m <metadata file> -o <maximum overlap> <file|directory ...>"
    errors = []
    optlist, file_list = getopt.getopt(sys.argv[1:], 'm:o:')
    metadata_fname = ''
    for opt in optlist:
        if opt[0] == '-m':
            metadata_fname = opt[1]
        if opt[0] == '-o':
            max_overlap = opt[1]

    if metadata_fname is None or metadata_fname == '':
        errors.append("No metadata file given.")

    if max_overlap is None or max_overlap == '':
        errors.append("No maximum overlap file given.")

    if file_list is None or len(file_list) == 0:
        errors.append("No files or directories given.")

    if len(errors) != 0:
        print("Errors:")
        print("\n".join(errors))
        print(usage)

    signCounter = SignCounter(metadata_fname, max_overlap, file_list)
    signCounter.run()
