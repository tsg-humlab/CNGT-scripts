import sys
import datetime
import webvtt

input_file = sys.argv[1]
output_file = sys.argv[2]
delta_milliseconds = datetime.timedelta(milliseconds=int(sys.argv[3]))

vtt = webvtt.read(input_file)
for caption in vtt:
    caption.start = (
		    datetime.datetime.strptime(caption.start, '%H:%M:%S.%f') 
            + delta_milliseconds
        ).time().strftime('%H:%M:%S.%f')[:-3]
    caption.end = (
            datetime.datetime.strptime(caption.end, '%H:%M:%S.%f') 
            + delta_milliseconds
        ).time().strftime('%H:%M:%S.%f')[:-3]
    
vtt.save(output_file)
