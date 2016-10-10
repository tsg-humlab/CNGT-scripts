#!/usr/bin/python

"""
A class to add metadata tiers in an EAF.
"""

from __future__ import print_function

import getopt
import json
import os
import re
import sys
from lxml import etree
from urlparse import urlparse
import subprocess
from collections import defaultdict


class Metadata2tiers:
    def __init__(self, metadata_file, eaf_files, video_dir, output_dir=None, ffprobe_command="ffprobe"):
        self.video_dir = video_dir
        self.output_dir = output_dir
        self.ffprobe_command = ffprobe_command

        self.all_files = []
        for f in eaf_files:
            self.add_file(f)

        self.time_slots = {}

        self.metadata = defaultdict(lambda: defaultdict(list))
        self.load_metadata(metadata_file)

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

    def load_metadata(self, metadata_file):
        with open(metadata_file) as meta:
            header = meta.readline().rstrip()  # Skip first row (header)
            self.metadata["header"] = header.split("\t")[1:5]
            for line in meta.readlines():
                fields = line.rstrip().split("\t")
                self.metadata["rows"][fields[0]] = fields[1:5]

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
            duration = self.find_max_duration(videos)
            self.extract_time_slots(xml)
            annotation_values = self.create_annotation_values(file_name)
            new_xml = self.add_new_annotation(xml, annotation_values, duration)
            print(etree.tostring(new_xml, pretty_print=True))

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
            match = re.match(r'^(CNGT\d{4}_(S\d{3})_b.mpg)$', video_file)
            if match:
                videos[match.group(1)] = video_file

        return videos

    def find_max_duration(self, videos):
        max_duration = 0.0
        for video in videos:
            cmd = [self.ffprobe_command,
                   "-of", "json",
                   "-show_streams",
                   self.video_dir + os.sep + video]
            with open(os.devnull, 'w') as devnull:
                #print(" ".join(cmd))
                pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=devnull)
                out, err = pipe.communicate()
                duration = float(json.loads(out)["streams"][0]["duration"])
                if duration > max_duration:
                    max_duration = duration

        return int(max_duration * 1000)

    def extract_time_slots(self, xml):
        """
        Extracts time slots from the EAF XML.

        :param xml: the EAF XML
        :return:
        """
        self.time_slots = {}
        for time_slot in xml.findall("//TIME_SLOT"):
            time_slot_id = int(time_slot.attrib['TIME_SLOT_ID'][2:])
            self.time_slots[time_slot_id] = time_slot.attrib['TIME_VALUE']

    def create_annotation_values(self, file_name):
        url = urlparse(file_name)
        basename = os.path.basename(url.path)

        metadata = self.metadata["rows"][basename]
        annotation_value = ", ".join(
                                        "[" + x[0] + ": " + x[1] + "]"
                                         for x in zip(self.metadata["header"], metadata)
                                    )
        return annotation_value

    def add_new_annotation(self, xml, annotation_value, duration):
        # Add new time slots:
        # - at 0
        # - at duration
        time_order = xml.findall("//TIME_ORDER")[0]
        if 0 not in self.time_slots:
            self.time_slots[0] = 0
            time_order.insert(0, etree.XML('<TIME_SLOT TIME_SLOT_ID="ts%d" TIME_VALUE="%d"/>' % (0, 0)))

            if duration not in self.time_slots.values():
                new_last_time_slot_id = sorted(self.time_slots.keys())[-1] + 1
                print("LAST TIME SLOT ID: " + str(new_last_time_slot_id), file=sys.stderr)
                self.time_slots[new_last_time_slot_id] = duration
                time_order.insert(new_last_time_slot_id + 1,
                                  etree.XML('<TIME_SLOT TIME_SLOT_ID="ts%d" TIME_VALUE="%d"/>'
                                            % (new_last_time_slot_id, duration)))

                # Add new tiers
                last_tier = xml.findall("//TIER")[-1]
                parent = last_tier.getparent()
                for subject in ("S1", "S2"):
                    new_tier = etree.XML("""
                        <TIER DEFAULT_LOCALE="en" TIER_ID="Metadata %s" LINGUISTIC_TYPE_REF="remarks">
                            <ANNOTATION>
                                <ALIGNABLE_ANNOTATION ANNOTATION_ID="a99999" TIME_SLOT_REF1="ts0" TIME_SLOT_REF2="ts%d">
                                    <ANNOTATION_VALUE>%s</ANNOTATION_VALUE>
                                </ALIGNABLE_ANNOTATION>
                            </ANNOTATION>
                        </TIER>
                    """ % (subject, new_last_time_slot_id, annotation_value))
                    parent.insert(parent.index(last_tier)+1, new_tier)
                    last_tier = new_tier

        return xml


if __name__ == "__main__":
    # -c ffprobe command if it is not ffprobe (e.g. avprobe on Ubuntu)
    # -v Directory containing video files
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            "-c <ffprobe command if not ffprobe> -v <video directory> -o <output directory>" + \
            "-m <metadata file>"

    # Set default values
    ffprobe_command = "ffprobe"
    output_dir = None
    video_dir = None
    metadata_file = None

    # Register command line arguments
    opt_list, file_list = getopt.getopt(sys.argv[1:], 'c:o:v:m:')
    for opt in opt_list:
        if opt[0] == '-c':
            ffprobe_command = opt[1]
        if opt[0] == '-o':
            output_dir = opt[1]
        if opt[0] == '-v':
            video_dir = opt[1]
        if opt[0] == '-m':
            metadata_file = opt[1]

    # Check for errors and report
    errors = []
    if video_dir is None or len(video_dir) == 0:
        errors.append("No video directory given")

    if file_list is None or len(file_list) == 0:
        errors.append("No files or directories given.")

    if metadata_file is None or len(file_list) == 0:
        errors.append("No metadata file given.")

    if len(errors) != 0:
        print("Errors:")
        print("\n".join(errors))
        print(usage)
        exit(1)

    # Report registered options
    print("OPTIONS", file=sys.stderr)
    print("Files: " + ", ".join(file_list), file=sys.stderr)
    print("Video directory: " + video_dir, file=sys.stderr)
    print("ffprobe command: " + ffprobe_command, file=sys.stderr)
    if output_dir is not None:
        print("Output directory: " + output_dir, file=sys.stderr)
    print("Metadata file: " + metadata_file, file=sys.stderr)

    # Built and run
    metadata2tiers = Metadata2tiers(metadata_file, file_list, video_dir, output_dir, ffprobe_command)
    metadata2tiers.run()
