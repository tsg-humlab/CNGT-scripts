from __future__ import print_function

import os
import sys
import re
from collections import defaultdict

if __name__ == "__main__":
    dir = sys.argv[1]
    output_dir = sys.argv[2]
    cmd = sys.argv[3]
    ids = defaultdict(list)
    for file in os.listdir(dir):
        fname, ext = os.path.splitext(file)
        if ext == '.vtt':
            id = re.sub(r'_S\d+$', '', fname)
            ids[id].append(file)

    for id, files in ids.items():
        if len(files) == 2:
            print(cmd, " ".join([os.path.join(dir, f) for f in files]), os.path.join(output_dir, id) + ".vtt")
        elif len(files) == 1:
            print("cp {} {}".format(os.path.join(dir, files[0]), os.path.join(output_dir, id) + ".vtt"))
