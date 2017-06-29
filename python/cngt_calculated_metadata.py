#!/usr/bin/python

"""
Script to calculate metadata from CNGT EAFs.
"""

import random, json


files = ['CNGT0001.eaf', 'CNGT0002.eaf', 'CNGT0003.eaf', 'CNGT0004.eaf']

metadata = {}


for file in files:
    metadata[file] = {
        'speed': {},
        'differentSigns': {},
        'classifiers': {},
        'sentenceLength': {},
        'lowFreqSigns': {},
        'fingerspelling': {},
        'interaction': {},
        'dominanceReversal': {}
    }


    metadata[file]['speed'] = random.randrange(0,255)
    metadata[file]['differentSigns'] = random.randrange(0,255)
    metadata[file]['classifiers'] = random.randrange(0,255)
    metadata[file]['sentenceLength'] = random.randrange(0,255)

    metadata[file]['lowFreqSigns'] = {}
    metadata[file]['lowFreqSigns']['S003'] = random.randrange(0,255)
    metadata[file]['lowFreqSigns']['S004'] = random.randrange(0,255)

    metadata[file]['fingerspelling'] = random.randrange(0,255)
    metadata[file]['interaction'] = random.randrange(0,255)
    metadata[file]['dominanceReversal'] = random.randrange(0,255)

print(json.dumps(metadata, sort_keys=True, indent=4))