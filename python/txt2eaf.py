import sys
import itertools
from datetime import datetime, timedelta
from pympi.Elan import Eaf


txt_file = sys.argv[1]
eaf_template_file = sys.argv[2]
output_file = sys.argv[3]


def grouper(n, iterable, fillvalue=None):
    """grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"""
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)

with open(txt_file) as txt_file:
    lines = txt_file.readlines()

# If second line is empty assume a title
if lines[1].strip() == '':
    print("EMTPY SECOND LINE")
    title = lines.pop(0)
else:
    lines.insert(0, '')

groups = list(grouper(3, lines))

annotations = []

for group in groups:
    begin = datetime.strptime(group[1].strip(), '%H:%M:%S').time()
    begin = int(timedelta(hours=begin.hour, minutes=begin.minute, seconds=begin.second).total_seconds())
    tier, annotation = group[2].split(": ", 1)
    annotations.append({
        "tier": tier,
        "begin": begin,
        "value": annotation.strip(),
        "end": None
    })
    if len(annotations) > 1:
        end = begin - 1
        annotations[-2]["end"] = end

# Give the last annotation a duration of 1 sec.
annotations[-1]['end'] = annotations[-1]['begin'] + 1

# Check durations > 0
for i, annotation in enumerate(annotations):
    if annotation['end'] <= annotation['begin']:
        annotation.update({'end': annotation['begin'] + 1})



def process_eaf(eaf, file_name, annotations):
    for annotation in annotations:
        # print(annotation['value'])
        eaf.add_annotation(annotation['tier'], annotation['begin']*1000, annotation['end']*1000, value=annotation['value'])

try:
    eaf = Eaf(eaf_template_file)
    process_eaf(eaf, eaf_template_file, annotations)
    eaf.to_file(output_file, pretty=True)
except IOError:
    print("The EAF %s could not be processed." % eaf_template_file, file=sys.stderr)
    print(sys.exc_info()[0])