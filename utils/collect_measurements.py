#!/usr/bin/env python
import csv
import json
import re

def extract_csv(fname, idx=0):
    with open(fname, 'rt') as csvfile:
        return dict( (name, int(size)) for name, size in  csv.reader(csvfile, delimiter=',', quotechar='"'))

def extract_accesses(fname):
    return sum(extract_csv(fname).values())

def extract_bsize(fname, ignore=['maximum', 'sum']):

    #group by layer
    table={}
    for name, val in extract_csv(fname).items():
        m=re.match("^(?P<type>(fWeight|dummy_copy))_(?P<segment_id>\d+_)?(?P<name>.*(?=_buf)).*", name) # _(?P<name>.*(?=_buf))$", name)
        if not m:
            if len(filter(lambda k: k in name, ignore))==0:
                print 'WARNING: did not recognize buffer:', name
        else:
            d=m.groupdict()['name']
            t=m.groupdict()['type']
            if d not in table: table[d]={}
            table[d][t]=val

    #reduce to get buffer size per layer
    for name in table:
        table[name]=sum(table[name].values())

    #return maximum buffer size
    return max(table.values())

def extract_point(facc, fbsize):

    # Sanity check in case files match the typical usecase in this project
    a=re.match('accesses_(?P<idx>\d+).csv', facc)
    b=re.match('memsize_(?P<idx>\d+).csv', fbsize)
    if a and b and a.groupdict()['idx'] != b.groupdict()['idx']:
        print "WARNING: indexes of %s and %s don't seem to match. Continuing but results may be wrong...."%(facc,fbsize)

    return {
        "networkcost": {
            "accesses": extract_accesses(facc),
            "buffer_size": extract_bsize(fbsize),
            "macs": 0
        }
    }


if __name__ == '__main__':
    import argparse

    #Construct the parser
    parser = argparse.ArgumentParser(description="CNN collect measurements tool")

    parser.add_argument('-a', '--accesses', nargs='+', dest='facc', required=True, action='store',
        help="List of csv files with measured memory sizes"
    )

    parser.add_argument('-b', '--bsize', nargs='+', dest='fbsize', required=True, action='store',
        help="List of csv files with measured memory sizes"
    )

    parser.add_argument('-o', '--output', dest='fout', required=True, action='store',
        help="Output filename"
    )

    # Parse arguments
    args = parser.parse_args()

    #extract the results
    results=[ extract_point(a,b) for a,b in zip(args.facc, args.fbsize)]

    #store to json
    with open(args.fout, 'wt') as f:
        json.dump(results, f, sort_keys=True, indent=4)
