#!/bin/bash
IDX=$1

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <point_idx>"
    exit
fi

#get predictions
points_file=$(ls *_points.json)
arr=($(python -c "import json; c=json.load(open('$points_file'))[$IDX]['networkcost']; print c['accesses'], c['buffer_size']"))
pacc=${arr[0]}
pb=${arr[1]}

#get measurements
macc=$(python -c "import re; print sum(map(lambda l: int(re.search('(\d+)\s*$', l).group(1)),  open('accesses_$IDX.csv').readlines()))")
mb=$(python -c "import re; v=map(lambda l: int(re.search('(\d+)\s*$', l).group(1)),  filter(lambda s: not (s.startswith('maximum') or s.startswith('sum')), open('memsize_$IDX.csv').readlines())); print max([a+b for a,b in zip(v[::2],v[1::2])])")

#print in table format
printf "%-13s %-15s %-15s %-15s\n" "" "measured" "predicted" "diff"
printf "%-13s %-15d %-15d %-15d\n" "buffer size:" $mb   $pb    $(($mb-$pb))
printf "%-13s %-15d %-15d %-15d\n" "accesses:" $macc $pacc  $(($macc-$pacc))

