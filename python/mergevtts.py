import sys


def read_file(filename):
    with open(filename, 'r') as file:
        contents = "".join([line for line in file.readlines() if not line.startswith('WEBVTT')]).strip()
        return contents.split('\n\n')

if __name__ == "__main__":
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    output_file = sys.argv[3]

    all_cues = read_file(file1) + read_file(file2)
    all_cues.sort()
    output = "\n\n".join(all_cues)

    with open(output_file, 'w') as outfile:
        outfile.write("WEBVTT\n\n")
        outfile.write(output)
