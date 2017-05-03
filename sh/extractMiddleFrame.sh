echo "=== Start: ==="
BASEDIR=$(pwd)
FILEPATH="$1"
OUTPUTDIR="$2"
FILENAME=$(basename "$FILEPATH")
DIRNAME="$OUTPUTDIR/$FILENAME-frames"

if [[ ! -e $FILEPATH ]]
then
  echo "$FILEPATH does not exist"
  exit
fi

if [[ ! -d $OUTPUTDIR ]]
then
  echo "$OUTPUTDIR is not a directory"
  exit
fi


echo "=== Creating directories... ==="
mkdir -p "$DIRNAME/all"
mkdir "$DIRNAME/middle"

echo "=== Extracting frames from video... ==="
# The filter makes the resulting image
# have the same size as the video when displayed
AVCONVOUTPUT=`avconv -i "$FILEPATH" -filter:v scale="'iw*max(1,sar)':'ih*max(1,1/sar)'" "$DIRNAME/all/frame-%5d.png"`

echo "=== Copying middel frame... ==="
cd "$DIRNAME/all"
MIDDLEFRAME=`ls *.png | wc -l | xargs -I{} perl -e 'use POSIX; $id = floor((@ARGV[0])/2); printf("frame-%05i.png", $id); print "\n";' {}`
cp "$MIDDLEFRAME" "../middle/$FILENAME.png"

echo "=== Creating 320x180 variant... ==="
convert "../middle/$FILENAME.png" -resize x180 ../middle/"$FILENAME"_320x180.png

echo "=== Renaming ==="
rename 's/\-\d+\.mp4//' "../middle/$FILENAME.png"
rename 's/\-\d+\.mp4//' "../middle/"$FILENAME"_320x180.png"

cd $BASEDIR

echo "=== Deleting all frames ==="
#rm -R "$DIRNAME/all"

echo "=== Done. ==="
