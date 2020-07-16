#!/usr/bin/python

"""
Script to calculate metadata from CNGT EAFs.
"""

import sys
import os
import getopt
import json
import numpy
import math
from CNGT_scripts.python.filecollectionprocessing.eafprocessor import EafProcessor
from CNGT_scripts.python.filecollectionprocessing.filecollectionprocessor import FileCollectionProcessor


class EafMetadataCalculator(EafProcessor):
    """
    
    """

    def __init__(self, metadata_file=None):
        self.metadata_file = metadata_file
        self.metadata = {}
        self.annotations_per_signer_per_file = {}
        self.annotation_frequencies = {}
        self.ranges = {
            'speed': {'min': 0, 'max': 0},
            'differentSigns': {'min': 0, 'max': 0},
            'classifiers': {'min': 0, 'max': 0},
            'sentenceLength': {'min': 0, 'max': 0},
            'fingerspelling': {'min': 0, 'max': 0},
            'interaction': {'min': 0, 'max': 0},
            'dominanceReversal': {'min': 0, 'max': 0},
            'lowFreqSigns': {'min': 0, 'max': 0},
        }

        self.value_lists = {
            'speed': [],                # float
            'differentSigns': [],       # int
            'classifiers': [],          # float
            'sentenceLength': [],       # float
            'fingerspelling': [],       # int
            'interaction': [],          # int
            'dominanceReversal': [],    # int
            'lowFreqSigns': [],         # int
        }
        
    def update_range(self, key, value):
        if self.ranges[key]['min'] is None or value < self.ranges[key]['min']:
            self.ranges[key]['min'] = value
        elif self.ranges[key]['max'] is None or value > self.ranges[key]['max']:
            self.ranges[key]['max'] = value
        self.value_lists[key].append(value)

    def get_annotations_from_longest_tier(self, eaf, subject=None):
        # Get the annotations from the tier containing the most annotations
        annotations = []

        if subject in [1, 2]:
            subject_ids = [subject]
        else:
            subject_ids = [1, 2]

        for subject_id in subject_ids:

            for hand in ['L', 'R']:
                tier_id = 'Gloss' + hand + ' S' + str(subject_id)
                tier = eaf.tiers[tier_id]
                current_annotations = transform_tier_data(eaf, tier)
                if len(current_annotations) > len(annotations):
                    annotations = current_annotations
                    subject = subject_id

        # Sort the list by begin time
        annotations.sort(key=lambda ann: ann['begin'])

        return (subject, annotations)

    def process_eaf(self, eaf, file_name):
        print(file_name, file=sys.stdout)
        self.count_signs(eaf, file_name)

        file_name = os.path.basename(file_name)
        self.metadata[file_name] = {}

        self.metadata[file_name]['participants'] = get_participants(eaf)

        self.metadata[file_name]['speed'] = round(self.get_speed(eaf), 1)
        self.update_range('speed', self.metadata[file_name]['speed'])

        self.metadata[file_name]['differentSigns'] = self.get_different_signs(eaf)
        self.update_range('differentSigns', self.metadata[file_name]['differentSigns'])

        self.metadata[file_name]['classifiers'] = round(self.get_classifiers(eaf), 1)
        self.update_range('classifiers', self.metadata[file_name]['classifiers'])

        sentence_length = self.get_sentence_length(eaf)
        if sentence_length:
            self.metadata[file_name]['sentenceLength'] = round(sentence_length, 1)
            self.update_range('sentenceLength', self.metadata[file_name]['sentenceLength'])

        self.metadata[file_name]['fingerspelling'] = self.get_fingerspelling(eaf)
        self.update_range('fingerspelling', self.metadata[file_name]['fingerspelling'])

        self.metadata[file_name]['interaction'] = self.get_interaction(eaf)
        self.update_range('interaction', self.metadata[file_name]['interaction'])

        self.metadata[file_name]['dominanceReversal'] = self.get_dominance_reversal(eaf)
        self.update_range('dominanceReversal', self.metadata[file_name]['dominanceReversal'])

    def calculate_ranges(self):
        ranges = {}

        for float_value in ['speed',  'classifiers', 'sentenceLength']:
            mean = numpy.mean(self.value_lists[float_value])
            std2 = numpy.std(self.value_lists[float_value]) * 2
            ranges[float_value] = {}
            std_min = round(mean - std2, 2)
            range_min = self.ranges[float_value]['min']
            ranges[float_value]['min'] = std_min if std_min > range_min else range_min
            std_max = round(mean + std2, 2)
            range_max = self.ranges[float_value]['max']
            ranges[float_value]['max'] = std_max if std_max < range_max else range_max

        for int_value in ['differentSigns',  'fingerspelling', 'interaction', 'dominanceReversal', 'lowFreqSigns']:
            mean = numpy.mean(self.value_lists[int_value])
            std2 = numpy.std(self.value_lists[int_value]) * 2
            ranges[int_value] = {}
            std_min = math.floor(mean - std2)
            range_min = self.ranges[int_value]['min']
            ranges[int_value]['min'] = std_min if std_min > range_min else range_min
            std_max = math.ceil(mean + std2)
            range_max = self.ranges[int_value]['max']
            ranges[int_value]['max'] = std_max if std_max < range_max else range_max

        return ranges

    def get_result(self):
        self.get_low_frequency_signs()
        ranges = self.calculate_ranges()
        output_data = {'ranges': ranges, 'sessions': self.metadata}
        if self.metadata_file:
            with open(self.metadata_file, 'w') as metadata_file:
                json.dump(output_data, metadata_file, sort_keys=True, indent=4)
        else:
            print(json.dumps(output_data, sort_keys=True, indent=4))

    def get_speed(self, eaf):
        """
        Average number of annotations per minute for the gloss tier (one of four) containing the largest number of 
        annotations, excluding gaps of more than two seconds without any annotations.
        :param eaf: 
        :return: 
        """
        (subject, annotations) = self.get_annotations_from_longest_tier(eaf)
        if annotations:

            intervals = []
            current_begin = annotations[0]['begin']  # begin time of first annotation
            current_end = annotations[0]['end']  # end time of the first annotation
            current_number_of_annotations = 1
            ann_index = 1
            while ann_index < len(annotations):
                if annotations[ann_index]['begin'] - current_end >= 2.0:
                    intervals.append({'length': current_end - current_begin,
                                      'number_of_annotations': current_number_of_annotations})
                    current_begin = annotations[ann_index]['begin']
                    current_end = annotations[ann_index]['end']
                    current_number_of_annotations = 1
                else:
                    current_end = annotations[ann_index]['end']
                    current_number_of_annotations += 1
                ann_index += 1

            total_length = 0
            total_number_of_annotations = 0
            for interval in intervals:
                total_length += interval['length']
                total_number_of_annotations += interval['number_of_annotations']

            speed = (total_number_of_annotations / (total_length / 1000.0 / 60)) if total_length else 0
            print("Annotations per minute: %f" % speed, file=sys.stderr)  # Number of annotations per minute
            return speed
        else:
            print("No annotations found", file=sys.stderr)
            return 0

    def get_different_signs(self, eaf):
        """
        Number of different annotations for all four gloss tiers combined.
        :param eaf: 
        :return: 
        """
        annotation_set = set()
        for subject_id in [1, 2]:
            for hand in ['L', 'R']:
                tier_id = 'Gloss' + hand + ' S' + str(subject_id)
                tier = eaf.tiers[tier_id]
                for annotation in tier[0].values():
                    annotation_set.add(annotation[2])
        print("Number of different annotations: " + str(len(annotation_set)), file=sys.stderr)
        return len(annotation_set)

    def get_classifiers(self, eaf):
        """
        Average number of annotations per minute with one or more underscores on all four gloss tiers combined
        :param eaf: 
        :return: 
        """
        annotations = []
        for subject_id in [1, 2]:
            for hand in ['L', 'R']:
                tier_id = 'Gloss' + hand + ' S' + str(subject_id)
                tier = eaf.tiers[tier_id]
                current_annotations = transform_tier_data(eaf, tier)
                annotations += current_annotations
        if annotations:
            annotations.sort(key=lambda ann: ann['begin'])
            begin = annotations[0]['begin']
            annotations.sort(key=lambda ann: ann['end'])
            end = annotations[-1]['end']
            classifier_annotations = [ann for ann in annotations if '_' in ann['value']]
            classifiers = len(classifier_annotations) / ((end - begin) / 1000.0 / 60)
            print("Classifiers: %f (%d, %d, %d)" % (classifiers,
                                                    len(classifier_annotations), begin, end), file=sys.stderr)
            return classifiers
        else:
            print("No classifiers found", file=sys.stderr)
            return 0


    def get_sentence_length(self, eaf):
        """
        Average number of annotations per sentence for the gloss tier (one of four) containing the largest number of 
        annotations
        :param eaf: 
        :return: 
        """
        (subject, annotations) = self.get_annotations_from_longest_tier(eaf)
        if subject and annotations:
            tier_id = 'TranslationFree S' + str(subject)
            tier = eaf.tiers[tier_id]
            translation_annotations = transform_tier_data(eaf, tier)
            if not translation_annotations:
                tier_id = 'TranslationNarrow S' + str(subject)
                tier = eaf.tiers[tier_id]
                translation_annotations = transform_tier_data(eaf, tier)
            translation_annotations.sort(key=lambda ann: ann['begin'])

            if translation_annotations:
                number_of_annotations_per_sentence = []
                for transl_ann in translation_annotations:
                    overlapping_annotations = [
                        ann for ann in annotations
                        if has_overlap((ann['begin'], ann['end']), (transl_ann['begin'], transl_ann['end']))
                    ]
                    number_of_annotations_per_sentence.append(len(overlapping_annotations))

                sentence_length = sum(number_of_annotations_per_sentence) / float(len(number_of_annotations_per_sentence))
                print("Sentence length: %f" % sentence_length, file=sys.stderr)
                if sentence_length >= 2.0:
                    return sentence_length
                else:
                    return None
            else:
                print("No (translation) annotations found", file=sys.stderr)
                return None
        else:
            print("No annotations found", file=sys.stderr)
            return None

    def count_signs(self, eaf, file_name):
        """
        Total number of gloss annotations that fall within the 80% tail of the gloss frequency distribution across the 
        whole corpus. Frequencies are to be calculated on the basis of the tier per signer that contains most 
        annotations, so as to cover both left-handers and right-handers and so as not to count two-handed signs twice. 
        The annotations for the two signers should add up to one value.
        :param eaf: 
        :return: 
        """

        self.annotations_per_signer_per_file[file_name] = {}
        for subject_id in [1, 2]:
            (subject, annotations) = self.get_annotations_from_longest_tier(eaf, subject_id)

            self.annotations_per_signer_per_file[file_name][subject_id] = annotations

            for annotation in annotations:
                value = annotation['value']
                if value in self.annotation_frequencies:
                    self.annotation_frequencies[value] += 1
                else:
                    self.annotation_frequencies[value] = 1

    def get_low_frequency_signs(self):
        annotation_frequencies = list(self.annotation_frequencies.items())
        index_80pct = int(len(annotation_frequencies)*0.8)
        annotation_frequencies.sort(key=lambda ann: ann[1])
        included_frequencies = set([ann[1] for ann in annotation_frequencies[:index_80pct]])

        annotation_frequencies_80pct = set([ann[0] for ann in annotation_frequencies if ann[1] in included_frequencies])

        for file_path in self.annotations_per_signer_per_file:
            file_name = os.path.basename(file_path)
            low_frequency_total = 0
            for subject_id in [1, 2]:
                annotations = [ann['value'] for ann in self.annotations_per_signer_per_file[file_path][subject_id]]
                number_of_low_frequency_signs = 0
                for annotation in annotations:
                    if annotation in annotation_frequencies_80pct:
                        number_of_low_frequency_signs += 1
                low_frequency_total += number_of_low_frequency_signs
            self.metadata[file_name]['lowFreqSigns'] = low_frequency_total
            self.update_range('lowFreqSigns', self.metadata[file_name]['lowFreqSigns'])


    def get_fingerspelling(self, eaf):
        """
        Total number of annotations for all four gloss tiers combined that contain the symbol '#' and a total of more 
        than two characters (so excluding e.g. '#M').
        :param eaf: 
        :return: 
        """
        annotations = []
        for subject_id in [1, 2]:
            for hand in ['L', 'R']:
                tier_id = 'Gloss' + hand + ' S' + str(subject_id)
                tier = eaf.tiers[tier_id]
                current_annotations = transform_tier_data(eaf, tier, filter=lambda a: '#' in a and len(a) > 2)
                annotations += current_annotations
        print("Number of fingerspellings: %d" % len(annotations), file=sys.stderr)
        return len(annotations)

    def get_interaction(self, eaf):
        """
        Total number of TL and TR annotations on the two tiers 'DomRev Point S1' and 'DomRev Point S2'
        :param eaf: 
        :return: 
        """
        total = self.get_ooh_domrev_point_counts(eaf, ['TL', 'TR']) - 1
        if total is not None and total >= 0:
            print("Number of interactions: %d" % total, file=sys.stderr)
            return total
        else:
            return 0

    def get_dominance_reversal(self, eaf):
        """
        Total number of RL and LR annotations on the two tiers 'DomRev Point S1' and 'DomRev Point S2'
        :param eaf: 
        :return: 
        """
        total = self.get_ooh_domrev_point_counts(eaf, ['RL', 'LR'])
        if total is not None:
            print("Number of dominance reversals: %d" % total, file=sys.stderr)
            return total
        else:
            return 0

    def get_ooh_domrev_point_counts(self, eaf, value_set):
        total = 0
        try:
            for subject_id in [1, 2]:
                tier_id = 'DomRev Point S' + str(subject_id)
                tier = eaf.tiers[tier_id]
                current_annotations = transform_tier_data(eaf, tier, lambda a: a in value_set)
                total += len(current_annotations)
            return total
        except KeyError as ke:
            print("No such tier: %s" % str(ke), file=sys.stderr)
            return None


def transform_tier_data(eaf, tier, filter=lambda a: True):
    """
    Transforms and filters the tier data into a more workable format
    :param eaf: 
    :param tier: 
    :param filter: 
    :return: 
    """
    return [{
                'begin': eaf.timeslots[ann[0]],
                'end': eaf.timeslots[ann[1]],
                'value': ann[2]
            } for ann in tier[0].values()
                if filter(ann[2])]


def has_overlap(first, second, min_overlap=0):
    """
    Determines if there is overlap between the first and second interval accounting for a minimal overlap.
    If an interval is within the other, there is overlap no matter the amount of overlap.

    :param first: tuple first interval (begin, end)
    :param second: tuple second interval (begin, end)
    :param min_overlap: int minimal overlap integer
    :return:
    """
    if first[0] >= second[1] or second[0] >= first[1]:  # the start of one is after the end of the other
        return False
    overlap_interval = (max(first[0], second[0]), min(first[1], second[1]))
    overlap = overlap_interval[1] - overlap_interval[0]
    if overlap_interval == first or overlap_interval == second:  # one interval is completely within the other
        return True
    elif overlap >= min_overlap:
        return True
    return False  # default


def get_participants(eaf):
    """
    Get the participant of this EAF. Based on the condition the EAF has both GlossL S1 as GlossL S2 tiers.
    :param eaf: 
    :return: a list containing the participant codes
    """
    participants = []
    for subject_id in [1, 2]:
        tier_id = 'GlossL S' + str(subject_id)  # Determine tier id
        tier = eaf.tiers[tier_id]
        attributes = tier[-2]  # Get tier attributes
        if 'PARTICIPANT' in attributes:
            participant = attributes['PARTICIPANT']
            participants.append(participant)
    return participants

def get_creation_time(fname):
    import datetime as DT
    from django.utils.timezone import get_current_timezone
    # pip install python-dateutil
    from dateutil.parser import parse
    from lxml import etree
    with open(fname, encoding="utf-8") as eaf:

        try:
            xml = etree.parse(eaf)
            # root node is ANNOTATION_DOCUMENT
            root = xml.getroot()
            creation_date = root.attrib['DATE']
            date_time_obj = parse(creation_date)
        except:
            date_time_obj = DT.datetime.now(tz=get_current_timezone())

        return date_time_obj

if __name__ == "__main__":
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            " -o <output directory>" + \
            " -f <output file>" + \
            " <input files/dirs>"

    # Set default values
    output_dir = None
    output_file = None

    # Register command line arguments
    opt_list, file_list = getopt.getopt(sys.argv[1:], 'o:f:')
    for opt in opt_list:
        if opt[0] == '-o':
            output_dir = opt[1]
        if opt[0] == '-f':
            output_file = opt[1]

    # Build and run
    file_collection_processor = FileCollectionProcessor(file_list, output_dir=output_dir,
                                                        extensions_to_process=["eaf"])
    eafMetadataCalculator = EafMetadataCalculator(metadata_file=output_file)
    file_collection_processor.add_file_processor(eafMetadataCalculator)
    file_collection_processor.run()
    eafMetadataCalculator.get_result()
