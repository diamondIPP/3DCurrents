#!/usr/bin/env python
# --------------------------------------------------------
#       Script to create a run_log json file for the RD42 3D run files!
# created on September 4th 2016 by M. Reichmann (remichae@phys.ethz.ch)
# --------------------------------------------------------

from glob import glob
from time import ctime
import os.path
from argparse import ArgumentParser
from collections import OrderedDict
from datetime import datetime, timedelta
from json import dump


def parse_harris_log(file_name):
    log = OrderedDict()
    f = open(file_name)
    lines = []
    for line in f.readlines():
        info = filter(None, line.split(' '))
        if '/' in info[0]:
            info.pop(0)
        if len(info) > 1 and (info[0].isdigit() and len(info[0]) == 5):
            lines.append(info)
    hvs = {'neg': ['HV7-CH4', 'HV7-CH3'], 'pos': ['HV7-CH1', 'HV7-CH0']}
    for line in lines:
        run = str(line[0])
        log[run] = {}
        log[run]['nevents'] = line[8].replace('K', '000')
        names = ['Strip', 'Multi']

        for i, hv in enumerate(line[2].split(','), 1):
            log[run]['dia{0}'.format(i)] = '{name}-{sub}'.format(name=line[1], sub=names[i - 1])
            log[run]['bias{0}'.format(i)] = hv
            log[run]['hv{0}'.format(i)] = hvs['neg'][i - 1] if int(hv) < 0 else hvs['pos'][i - 1]
    f.close()
    return log

parser = ArgumentParser()
parser.add_argument('path', help='full path of directory where the data folders and Harris\' runlog are ')
args = parser.parse_args()

run_dirs = sorted(glob('{path}/*'.format(path=args.path)))
harris_log = glob('{path}/BeamTest*'.format(path=args.path))[0]

run_log = parse_harris_log(harris_log)

for run_dir in run_dirs:
    if run_dir.split('/')[-1].isdigit():
        run_number = str(run_dir.split('/')[-1])
        file_names = OrderedDict(sorted({int(f.split('_')[-1].split('.')[0]): f for f in glob('{path}/RUN*'.format(path=run_dir)) if f[-4].isdigit()}.iteritems()))
        end_time = datetime.strptime(ctime(os.path.getmtime(file_names.values()[-1])), '%a %b %d %H:%M:%S %Y') + timedelta(hours=1)
        first_run = datetime.strptime(ctime(os.path.getmtime(file_names.values()[0])), '%a %b %d %H:%M:%S %Y')
        second_run = datetime.strptime(ctime(os.path.getmtime(file_names.values()[1])), '%a %b %d %H:%M:%S %Y')
        start_time = (first_run - (second_run - first_run - timedelta(hours=1))).strftime('%a %b %d %H:%M:%S %Y')
        end_time = end_time.strftime('%a %b %d %H:%M:%S %Y')
        run_log[run_number]['begin'] = start_time
        run_log[run_number]['end'] = end_time

json_filename = '{path}/run_log.json'.format(path=args.path)
f = open(json_filename, 'w')
dump(run_log, f, indent=2, sort_keys=True)
f.truncate()
f.close()
print 'Gathered information and wrote into\n  -->{json}!'.format(json=json_filename)
