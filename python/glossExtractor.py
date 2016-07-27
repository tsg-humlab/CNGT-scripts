#!/usr/bin/python

"""
This script extracts video fragments for signs from CNGT EAFs.

Per signer signs are annotated on two tiers: one for the left hand and on for the right hand.
A sign can be two handed which means there are overlapping annotations with the same value (gloss)
on the two hand tiers. Consecutively overlapping annotations with the same value are counted as one
sign if the overlap is at least a minimal overlap interval.

Per sign the corresponding fragment is extracted from the corresponding video, including some extra
time at the beginning and at the end.
"""

from __future__ import print_function

import getopt
import json
import os
import re
import sys
from lxml import etree
from urlparse import urlparse
from subprocess import call, Popen, PIPE


__author__ = "Micha Hulsbosch"
__date__ = "July 2016"


class GlossExtractor:
    """
    Extracts video fragments for glosses from CNGT EAFs.
    """

    def __init__(self, files, video_directory, gloss_directory, min_overlap=0, extra_time=0, ffmpeg_cmd='ffmpeg'):
        """
        :param files: list of EAF files / directories containing EAF files
        :param min_overlap: minimal overlap for two handed signs
        :param extra_time: extra time at the beginning and end of the video fragment
        :param video_directory: directory containing the videos
        :param gloss_directory: directory for the video fragments of each gloss
        :param ffmpeg_cmd: the command to use instead of 'ffmpeg', e.g. on Ubuntu it is 'avconv'
        :return:
        """
        self.extra_time = extra_time/1000.0  # ms to s
        self.min_overlap = min_overlap

        self.video_directory = video_directory
        if self.video_directory.endswith(os.sep):
            self.video_directory = self.video_directory[:-len(os.sep)]

        self.gloss_directory = gloss_directory
        if self.gloss_directory.endswith(os.sep):
            self.gloss_directory = self.gloss_directory[:-len(os.sep)]

        self.ffmpeg_cmd = ffmpeg_cmd

        self.all_files = []
        for f in files:
            self.add_file(f)

        self.time_slots = {}

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
        Processes one file. Gloss extraction is called and video extraction is called.

        :param file_name:
        :return:
        """
        with open(file_name) as eaf:
            xml = etree.parse(eaf)
            videos = self.extract_video_files(xml)
            self.extract_time_slots(xml)
            (list_of_glosses, tier_id_prefix) = self.extract_glosses(xml)

            self.extract_glosses_from_videos(file_name, list_of_glosses, videos)

    def extract_video_files(self, xml):
        """
        Extracts video file url from the EAF XML.

        :param xml: the EAF XML
        :return: videos dictionary (key: participant code, value: video url)
        """
        videos = {}
        for media_descriptor in xml.findall("//MEDIA_DESCRIPTOR"):
            media_url = media_descriptor.attrib["MEDIA_URL"]
            url = urlparse(media_url)
            video_file = os.path.basename(url.path)
            match = re.match(r'^CNGT\d{4}_(S\d{3})_b.mpg$', video_file)
            if match:
                videos[match.group(1)] = video_file

        return videos

    def extract_time_slots(self, xml):
        """
        Extracts time slots from the EAF XML.

        :param xml: the EAF XML
        :return:
        """
        for time_slot in xml.findall("//TIME_SLOT"):
            time_slot_id = time_slot.attrib['TIME_SLOT_ID']
            self.time_slots[time_slot_id] = time_slot.attrib['TIME_VALUE']

    def extract_glosses(self, xml):
        """
        Extracts glosses from the EAF XML.

        :param xml: the EAF XML
        :return: a tuple: list of glosses, tier id prefix
        """
        list_of_glosses = {}
        tier_id_prefix = "Gloss"
        for tier in xml.findall("//TIER"):
            tier_id = tier.attrib['TIER_ID']
            list_of_glosses[tier_id] = {}

            match = re.match(r'^(Gloss?)([LR]) S([12])$', tier_id)
            if match and ('PARENT_REF' not in tier.attrib or tier.attrib['PARENT_REF'] == '')\
                    and ('PARTICIPANT' in tier.attrib):
                tier_id_prefix = match.group(1)
                hand = match.group(2)
                subject = match.group(3)
                participant = tier.attrib['PARTICIPANT']
                if not list_of_glosses.has_key(participant):
                    list_of_glosses[participant] = []

                for annotation in tier.findall("ANNOTATION/ALIGNABLE_ANNOTATION"):
                    annotation_id = annotation.attrib['ANNOTATION_ID']
                    annotation_data = {
                        "begin": int(self.time_slots[annotation.attrib['TIME_SLOT_REF1']]),
                        "end": int(self.time_slots[annotation.attrib['TIME_SLOT_REF2']]),
                        "id": annotation_id,
                        "value": annotation.find("ANNOTATION_VALUE").text,
                        "participant": participant,
                        "hand": hand,
                        "subject": subject,
                        "tier_id": tier_id
                    }
                    list_of_glosses[participant].append(annotation_data)

        return list_of_glosses, tier_id_prefix

    def extract_glosses_from_videos(self, fname, list_of_glosses, videos):
        """
        Finds overlapping annotations with identical values. These annotation units are used to construct
        ffmpeg commands to extract fragments from videos based on the interval of these units.

        :param fname: the EAF file name
        :param list_of_glosses: the list of glosses
        :param videos: the videos for this EAF
        :return:
        """
        for participant in videos.keys():
            current_gloss = {
                "value": "",
                "begin": -1,
                "end": -1
            }
            #print("#Glosses " + participant + ": " + str(len(list_of_glosses[participant])), file=sys.stderr)
            for annotation in sorted(list_of_glosses[participant], key=lambda gloss: gloss["begin"]):
                overlap_with_current = has_overlap((annotation["begin"], annotation["end"]),
                                                   (current_gloss["begin"], current_gloss["end"]),
                                                   self.min_overlap)
                if not overlap_with_current:
                    self.extract_video_fragment(fname, participant, current_gloss, videos[participant])
                    current_gloss = {
                        "value": annotation["value"],
                        "begin": annotation["begin"],
                        "end": annotation["end"]
                    }
                elif annotation["value"] == current_gloss["value"]:  # overlap AND same gloss value
                    current_gloss["end"] = max(annotation["end"], current_gloss["end"]) # extend the current gloss
                else:  # overlap but NOT same gloss value
                    if annotation["end"] <= current_gloss["end"]:  # annotation is within current gloss
                        self.extract_video_fragment(fname, participant, annotation, videos[participant])
                    else:  # annotation extends outside current gloss
                        self.extract_video_fragment(fname, participant, current_gloss, videos[participant])
                        current_gloss = {
                            "value": annotation["value"],
                            "begin": annotation["begin"],
                            "end": annotation["end"]
                        }

            self.extract_video_fragment(fname, participant, current_gloss, videos[participant])

    def extract_video_fragment(self, fname, participant, gloss, video):
        """
        Creates and runs the ffmpeg command to extract a fragment from a video.

        :param fname: the EAF file name
        :param participant: the participant code
        :param gloss: the annotation value of the gloss
        :param video: the file name of the video
        :return:
        """
        if gloss["value"] is None or gloss["value"] == "":
            return
        # start: milliseconds to seconds; shift left by extra_time
        start = str((gloss["begin"] / 1000.0) - self.extra_time)

        # duration: milliseconds to second; shift end right by 2 * extra_time, 1 time at the front, 1 time at the back
        duration = str(((gloss["end"] - gloss["begin"]) / 1000.0) + (2 * self.extra_time))

        value = re.sub(r'[/\?<>\\:\*\|]', '__', gloss["value"])
        f = re.sub(r'\.eaf$', '', os.path.basename(urlparse(fname).path))

        new_video_file = "_".join([f, participant, str(gloss["begin"]), str(gloss["end"]) + ".mpg"])

        output_dir = self.gloss_directory + os.sep + value
        if not os.path.exists(output_dir):
            #print("mkdir -p " + output_dir)
            os.makedirs(output_dir)

        cmd = [self.ffmpeg_cmd,
               "-i", self.video_directory + os.sep + video,
               "-ss", start,
               "-t", duration,
               "-c",  "copy",
               output_dir + os.sep + new_video_file]
        print(" ".join(cmd))
        Popen(cmd)


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


if __name__ == "__main__":
    usage = "Usage: \n" + sys.argv[0] + \
            " -c <ffmpeg command if not 'ffmpeg'> -o <minimal overlap> -t <extra time at beginning and end> " \
            "-v <video directory> -g <gloss output directory> <file|directory ...>"
    errors = []
    # -o Minimal overlap in ms; optional
    # -t Extra time at beginning and end of fragment, in ms; optional
    # -v Directory containing video files
    opt_list, file_list = getopt.getopt(sys.argv[1:], 'c:g:o:t:v:')

    ffmpeg_command = "ffmpeg"
    gloss_dir = None
    minimal_overlap = 0 # default 0
    time_begin_end = 0 # default 0
    video_dir = None

    for opt in opt_list:
        if opt[0] == '-c':
            ffmpeg_command = opt[1]
        if opt[0] == '-g':
            gloss_dir = opt[1]
        if opt[0] == '-o':
            minimal_overlap = int(opt[1])
        if opt[0] == '-t':
            time_begin_end = int(opt[1])
        if opt[0] == '-v':
            video_dir = opt[1]

    if gloss_dir is None or len(gloss_dir) == 0:
        errors.append("No gloss output directory given")

    if video_dir is None or len(video_dir) == 0:
        errors.append("No video directory given")

    if file_list is None or len(file_list) == 0:
        errors.append("No files or directories given.")

    if len(errors) != 0:
        print("Errors:")
        print("\n".join(errors))
        print(usage)
        exit(1)

    print("OPTIONS")
    print("Files: " + ", ".join(file_list), file=sys.stderr)
    print("Minimal overlap: " + str(minimal_overlap))
    print("Extra time at beginning and end: " + str(time_begin_end), file=sys.stderr)
    print("Video directory: " + video_dir, file=sys.stderr)
    print("Gloss output directory: " + gloss_dir, file=sys.stderr)
    print("ffmpeg command: " + ffmpeg_command, file=sys.stderr)

    gloss_extractor = GlossExtractor(file_list, video_dir, gloss_dir, minimal_overlap, time_begin_end, ffmpeg_command)
    gloss_extractor.run()
