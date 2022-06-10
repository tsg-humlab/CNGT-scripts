#!/usr/bin/python

"""
A class to add metadata tiers in an EAF.

Uses pympi (https://github.com/dopefishh/pympi) for the EAF specific processing.
"""

from __future__ import print_function

import getopt
import json
import os
import sys
from urlparse import urlparse
import subprocess
from collections import defaultdict
from pympi.Elan import Eaf


class Metadata2tiers:
    def __init__(self, metadata_file, eaf_files, video_dir, output_dir=None, ffprobe_command="ffprobe"):
        self.video_dir = video_dir
        if output_dir:
            self.output_dir = output_dir.rstrip(os.sep)
        if not os.path.isdir(self.output_dir):
            os.mkdir(self.output_dir, 0o750)
        self.ffprobe_command = ffprobe_command

        # Find all files recursively and add to a list
        self.all_files = []
        for f in eaf_files:
            self.add_file(f)

        # Read the metadata
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
        """
        Loads the metadata from the give CSV file.
        :param metadata_file:
        :return:
        """
        with open(metadata_file) as meta:
            header = meta.readline()  # Skip first row (header)
            self.metadata["header"] = header.split("\t")[1:5]
            for line in meta.readlines():
                fields = line.rstrip().split("\t")
                self.metadata["rows"][fields[0]] = fields[1:5]

    def run(self):
        """
        For each file in the list of files, processing is started.

        :return:
        """
        if not self.metadata:
            print("No metadata loaded.", file=sys.stderr)
        elif len(self.all_files) > 0:
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

        try:
            eaf = Eaf(file_name)
            videos = [os.path.basename(urlparse(media_descriptors['MEDIA_URL']).path)
                      for media_descriptors in eaf.media_descriptors
                      if media_descriptors['MIME_TYPE'] == 'video/mpeg']
            duration = self.find_max_duration(videos)
            if duration == 0.0:
                print("Duration could not be determined.", file=sys.stderr)
            else:
                annotation_values = self.create_annotation_values(file_name)
                self.add_new_annotations(eaf, annotation_values, duration)
                eaf.to_file(self.output_dir + os.sep + os.path.basename(urlparse(file_name).path), pretty=True)
        except IOError:
            print("The EAF %s could not be processed." % file_name, file=sys.stderr)

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

    def create_annotation_values(self, file_name):
        url = urlparse(file_name)
        basename = os.path.basename(url.path)

        metadata = self.metadata["rows"][basename]
        annotation_value = ", ".join(
                                        "[" + x[0] + ": " + x[1] + "]"
                                         for x in zip(self.metadata["header"], metadata)
                                    )
        return annotation_value
        
    def add_new_annotations(self, eaf, annotation_values, duration):
        for subject in ("S1", "S2"):
            tier_name = "Metadata " + subject
            eaf.add_tier(tier_name, ling="remarks", locale="en")
            eaf.add_annotation(tier_name, 0, duration, value=annotation_values)


if __name__ == "__main__":
    # -c ffprobe command if it is not ffprobe (e.g. avprobe on Ubuntu)
    # -v Directory containing video files
    # -o Output directory; optional
    usage = "Usage: \n" + sys.argv[0] + \
            " -c <ffprobe command if not ffprobe>"\
            " -v <video directory>" + \
            " -o <output directory>" + \
            " -m <metadata file>"

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

    # Build and run
    metadata2tiers = Metadata2tiers(metadata_file, file_list, video_dir, output_dir, ffprobe_command)
    metadata2tiers.run()
