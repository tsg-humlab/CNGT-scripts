#!/usr/bin/python

"""
Script to extract annotations from an EAF
and turn it into a webvtt.
"""


import sys, getopt, os
from webvtt import WebVTT, Caption
from filecollectionprocessing.filecollectionprocessor import FileCollectionProcessor
from filecollectionprocessing.eafprocessor import EafProcessor


class EafToWebVttTransformer(EafProcessor):
    def __init__(self, tier_base_name, fallback_tier_base_name, subjects=['S1', 'S2'], hands=['']):
        self.tier_base_name = tier_base_name
        self.fallback_tier_base_name = fallback_tier_base_name
        self.subjects = subjects
        self.hands = hands

        import itertools
        if hands:
            tier_names = ['{}{}'.format(tier_base_name, hand) for hand in hands]
        else:
            tier_names = [tier_base_name]

        tier_names = ['{} {}'.format(name[0], name[1]) for name in itertools.product(tier_names, subjects)]
        print(tier_names)
        self.tier_names = tier_names

    def process_eaf(self, eaf, file_name):
        print(file_name)
        file_basename = os.path.splitext(os.path.basename(file_name))[0]
        if file_basename.startswith('CNGT'):
            file_basename = file_basename[4:]



        for subject_id in self.subjects:

            # Put the annotations of the left and right hand in one list
            annotations = []
            participant = None
            for hand in self.hands:
                tier_id = self.tier_base_name + hand + ' ' + str(subject_id)
                tier = eaf.tiers[tier_id]
                if not tier[0].values() and self.fallback_tier_base_name:
                    print("Using fallback tier {}".format(self.fallback_tier_base_name))
                    tier_id = self.fallback_tier_base_name + hand + ' ' + str(subject_id)
                    tier = eaf.tiers[tier_id]

                if len(tier) >= 3 and 'PARTICIPANT' in tier[2]:
                    participant = tier[2]['PARTICIPANT']
                    annotations.extend(
                        self.transform_annotation_tuples(
                            eaf, list(tier[0].values()), hand
                        )
                    )

            if participant:
                # Sort the list by begin time
                annotations.sort(key=lambda tup: tup[0])

                print("Subject: {} ({})".format(subject_id, len(annotations)))
                # for annotation in annotations_per_subject[subject_id]:
                #     print("BT: %d | ET: %d | Value: %s" % annotation)
                webvtt = self.annotations_to_webvtt(annotations)
                webvtt.save(self.output_dir + os.sep + file_basename + "_" + participant + ".vtt")


    def annotations_to_webvtt(self, annotations):
        webvtt = WebVTT()

        last_index = len(annotations) - 1
        index = 0
        while index <= last_index:
            focus_annotation = annotations[index]
            # print("Focus:: BT: %d | ET: %d | Value: %s" % focus_annotation[:3])
            if index == last_index:
                caption = Caption(
                    self.time_to_webvtt_time(focus_annotation[0]),
                    self.time_to_webvtt_time(focus_annotation[1]),
                    [focus_annotation[2]]
                )
                # print("%s %s %s" % (caption.start, caption.end, caption.text))
                webvtt.captions.append(caption)
                index += 1
            else:
                for index_next in range(index+1, last_index+1):
                    index = index_next
                    next_annotation = annotations[index_next]
                    # print("Next :: BT: %d | ET: %d | Value: %s" % next_annotation[:3])
                    overlap = self.check_overlap(focus_annotation, next_annotation)
                    if overlap:
                        # print("#%s#%s#" % (focus_annotation[2], next_annotation[2]))
                        if not(focus_annotation[2] == next_annotation[2]):
                            caption = Caption(
                                self.time_to_webvtt_time(focus_annotation[0]),
                                self.time_to_webvtt_time(next_annotation[0]),
                                [focus_annotation[2]]
                            )
                            # print("%s %s %s" % (caption.start, caption.end, caption.text))
                            webvtt.captions.append(caption)
                            break
                    else:
                        caption = Caption(
                            self.time_to_webvtt_time(focus_annotation[0]),
                            self.time_to_webvtt_time(min(focus_annotation[1], next_annotation[0])),
                            [focus_annotation[2]]
                        )
                        # print("%s %s %s" % (caption.start, caption.end, caption.text))
                        webvtt.captions.append(caption)
                        break
        return webvtt

    def time_to_webvtt_time(self, milliseconds_original):
        (seconds, milliseconds) = divmod(milliseconds_original, 1000)
        (minutes, seconds) = divmod(seconds, 60)
        (hours, minutes) = divmod(minutes, 60)
        webvtt_time = "%02d:%02d:%02d.%03d" % (hours, minutes, seconds, milliseconds)
        # print(webvtt_time)
        return webvtt_time

    def check_overlap(self, annotation_1, annotation_2):
        # Begin time 1 is between begin time 2 and end time 2
        if annotation_2[0] <= annotation_1[0] < annotation_2[1]:
            return True
        elif annotation_1[0] <= annotation_2[0] < annotation_1[1]:
            return True
        return False

    def transform_annotation_tuples(self, eaf, annotations_original, hand):
        """
        Transforms the tuples with format (begin_ts, end_ts, value, svg_ref)
        to (begin_time, end_time, value)
        :param eaf: 
        :param annotations_original: 
        :return: 
        """
        annotations_new = []
        for annotation in annotations_original:
            if annotation[2]:
                annotations_new.append((
                    eaf.timeslots[annotation[0]],
                    eaf.timeslots[annotation[1]],
                    annotation[2],
                    hand
                ))
        return annotations_new

if __name__ == "__main__":
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            " -o <output directory>" \
            " -t <tier base name>" \
            " -f <fallback tier base name>" \
            " -h <hand [LR]>"

    # Set default values
    output_dir = None
    tier_base_name = None
    fallback_tier_base_name = None

    # Register command line arguments
    opt_list, file_list = getopt.getopt(sys.argv[1:], 'o:t:f:h:')
    hands = []
    for opt in opt_list:
        if opt[0] == '-o':
            output_dir = opt[1]
        if opt[0] == '-t':
            tier_base_name = opt[1]
        if opt[0] == '-f':
            fallback_tier_base_name = opt[1]
        if opt[0] == '-h':
            hands.append(opt[1])

    # Check for errors and report
    errors = []
    if file_list is None or len(file_list) == 0:
        errors.append("No files or directories given.")
    if tier_base_name is None:
        errors.append("No tier base name given")

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
    args = {}
    if tier_base_name:
        args['tier_base_name'] = tier_base_name
    if fallback_tier_base_name:
        args['fallback_tier_base_name'] = fallback_tier_base_name
    if hands:
        args['hands'] = hands
    eafToWebVttTransformer = EafToWebVttTransformer(**args)
    file_collection_processor.add_file_processor(eafToWebVttTransformer)
    file_collection_processor.run()
