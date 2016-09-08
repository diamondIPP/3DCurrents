#!/usr/bin/env python
# --------------------------------------------------------
#       Script to show the recorded current for the 3D beam test runs
# created on September 4th 2016 by M. Reichmann (remichae@phys.ethz.ch)
# --------------------------------------------------------

from glob import glob
from time import sleep
from json import load
from collections import OrderedDict
import os.path

import matplotlib.pyplot as plt
from matplotlib import ticker
from ConfigParser import ConfigParser
from numpy import array
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from Utils import *

# ====================================
# CONSTANTS
# ====================================
axis_title_size = 0.04
label_size = .03
col_vol = 602  # 807
col_cur = 899  # 418


# ====================================
# CLASS FOR THE DATA
# ====================================
class Currents:
    """reads in information from the keithley log file"""

    def __init__(self, runs, log_dir, data_dir, verbose=False):

        # settings
        self.Res = load_resolution()

        # config
        self.Dir = '/'.join(os.path.realpath(__file__).split('/')[:-1])
        self.Verbose = verbose
        self.ConfigParser = self.load_parser()
        self.StartRun = runs[0]
        self.EndRun = runs[1]
        self.LogDir = self.load_logdir(log_dir)
        self.DataDir = self.load_datadir(data_dir)

        # run info
        self.RunLog = self.load_runlog()
        self.StartTime = convert_time(self.RunLog[self.StartRun]['begin'])
        self.EndTime = convert_time(self.RunLog[self.EndRun]['end'])

        # device info
        self.Devices = self.get_device_nrs()
        self.ActiveDevice = None

        # logs
        self.DataPaths = self.create_data_path()
        self.LogNames = None

        # data
        self.IgnoreJumps = True
        self.Currents = {}
        self.Voltages = {}
        self.Time = {}
        self.init_data()
        self.MeanCurrent = 0
        self.MeanVoltage = 0
        #
        # plotting
        self.CurrentGraph = {}
        self.VoltageGraph = {}
        self.Margins = {}
        # graph pads
        self.VoltagePad = None
        self.CurrentPad = None
        self.TitlePad = None
        self.Histos = {}
        self.Stuff = []

    # ==========================================================================
    # region INIT
    def log_info(self, msg):
        if self.Verbose:
            t = datetime.now().strftime('%H:%M:%S')
            print 'INFO: {t} --> {msg}'.format(t=t, msg=msg)

    def load_logdir(self, logdir):
        n_dirs = len(logdir.split('/'))
        return '{dir}/{logs}'.format(dir=self.Dir, logs=logdir) if n_dirs == 1 else logdir

    def load_datadir(self, data_dir):
        n_dirs = len(data_dir.split('/'))
        return '{dir}/{data}'.format(dir=self.Dir, data=data_dir) if n_dirs == 1 else data_dir

    def load_runlog(self):
        try:
            f = open(self.LogDir)
            data = load(f)
            f.close()
        except IOError as err:
            log_warning('{err}\n  Could not load default RunInfo!'.format(err=err))
            return None
        run_logs = OrderedDict(sorted(data.iteritems()))
        return run_logs

    def load_parser(self):
        parser = ConfigParser()
        parser.read('{dir}/HV.conf'.format(dir=self.Dir))
        self.log_info('HV Devices: {0}'.format([name for name in parser.sections() if name.startswith('HV')]))
        return parser

    def get_device_nrs(self):
        devices = {}
        for run, dic in self.RunLog.iteritems():
            if not self.EndRun >= run >= self.StartRun:
                continue
            for key, value in dic.iteritems():
                if key.startswith('hv'):
                    dia = dic['dia{nr}'.format(nr=key[-1])]
                    if dia in devices and devices[dia]['full'] != value:
                        log_warning('You\'re comparing apples and oranges! I won\'t allow that!')
                        exit(-1)
                    info = value.split('-')
                    devices[dia] = {'full': value, 'name': self.ConfigParser.get(info[0], 'name'), 'ch': info[1] if len(info) > 1 else 'CH0', 'dia': dia}
        return devices

    def create_data_path(self):
        data_dic = {}
        for key, dic in self.Devices.iteritems():
            data_dic[key] = '{data}/{dev}_{ch}/'.format(data=self.DataDir, dev=dic['name'], ch=dic['ch'])
        return data_dic

    # endregion

    def reset_data(self, device):
        self.Currents[device] = []
        self.Voltages[device] = []
        self.Time[device] = []

    def init_data(self):
        for device in self.Devices.iterkeys():
            self.reset_data(device)

    # endregion

    # ==========================================================================
    # region ACQUIRE DATA
    def get_logs_from_start(self, device):
        log_names = sorted(glob(self.DataPaths[device] + '*'))
        start_log = None
        for i, name in enumerate(log_names):
            log_date = self.get_log_date(name)
            if log_date >= self.StartTime:
                break
            start_log = i
        self.log_info('Starting with log: {0}'.format(log_names[start_log].split('/')[-1]))
        return log_names[start_log:]

    @staticmethod
    def get_log_date(name):
        log_date = name.split('/')[-1].split('_')
        log_date = ''.join(log_date[-6:])
        return datetime.strptime(log_date, '%Y%m%d%H%M%S.log')

    def set_start(self, device, zero=False):
        self.Currents[device].append(self.Currents[device][-1] if not zero else 0)
        self.Voltages[device].append(self.Voltages[device][-1] if not zero else 0)
        # self.Time[device].append((self.StartTime - datetime(self.StartTime.year, 1, 1)).total_seconds())
        self.Time[device].append(self.StartTime)

    def set_stop(self, device, zero=False):
        self.Currents[device].append(self.Currents[device][-1] if not zero else 0)
        self.Voltages[device].append(self.Voltages[device][-1] if not zero else 0)
        # self.Time[device].append((self.EndTime - datetime(self.EndTime.year, 1, 1)).total_seconds())
        self.Time[device].append(self.EndTime)

    def find_data(self, device):
        if self.Currents[device]:
            return
        stop = False
        self.LogNames = self.get_logs_from_start(device)
        for i, name in enumerate(self.LogNames):
            self.MeanCurrent = 0
            self.MeanVoltage = 0
            log_date = self.get_log_date(name)
            data = open(name, 'r')
            # jump to the correct line of the first file
            if not i:
                self.find_start(data, log_date)
            index = 0
            if index == 1:
                self.set_start(device)
            for line in data:
                # if index < 20:
                #     print line
                info = line.split()
                if isfloat(info[1]) and len(info) > 2:
                    now = datetime.strptime(log_date.strftime('%Y%m%d') + info[0], '%Y%m%d%H:%M:%S')
                    if self.StartTime < now < self.EndTime and float(info[2]) < 1e30:
                        self.save_data(device, now, info, index)
                        index += 1
                    if self.EndTime < now:
                        stop = True
                        break
            data.close()
            if stop:
                break
        if self.Currents[device]:
            self.set_stop(device)
        else:
            self.set_start(device, zero=True)
            self.set_stop(device, zero=True)

    def save_data(self, device, now, info, index):
        if self.StartTime < now < self.EndTime and float(info[2]) < 1e30:
            index += 1
            if self.IgnoreJumps:
                if len(self.Currents[device]) > 100 and abs(self.Currents[device][-1] * 100) < abs(float(info[2]) * 1e9):
                    if abs(self.Currents[device][-1]) > 0.01:
                        return
                if 230 <= abs(float(info[2])) * 1e9 <= 250:
                    return
            self.Currents[device].append(float(info[2]) * 1e9)
            self.Time[device].append(now)
            # self.Time[device].append(total_seconds)
            self.Voltages[device].append(float(info[1]))

    def find_start(self, data, log_date):
        lines = len(data.readlines())
        data.seek(0)
        if lines < 10000:
            return
        was_lines = 0
        for i in range(6):
            lines /= 2
            for j in xrange(lines):
                data.readline()
            while True:
                info = data.readline().split()
                if not info:
                    break
                if isfloat(info[1]):
                    now = datetime.strptime(log_date.strftime('%Y%m%d') + info[0], '%Y%m%d%H:%M:%S')
                    if now < self.StartTime:
                        was_lines += lines
                        break
                    else:
                        data.seek(0)
                        for k in xrange(was_lines):
                            data.readline()
                        break

    def convert_to_relative_time(self, device):
        zero = self.Time[device][0]
        for i in xrange(len(self.Time)):
            self.Time[device][i] = self.Time[i] - zero

    # endregion

    # ==========================================================================
    # region PLOTTING
    def set_graphs(self, device, rel_time=True):
        self.find_data(device)
        self.convert_to_relative_time(device) if rel_time else do_nothing()
        sleep(.1)
        # self.make_graphs(device)
        self.set_margins(device)

    def make_graphs(self):
        d = self.ActiveDevice['dia']
        fig = plt.figure(figsize=(15, 10), dpi=100)
        fig.suptitle('Currents of the {dia} for run {r}'.format(dia=self.ActiveDevice['dia'], r=make_run_string(self.StartRun, self.EndRun)), size=20)
        t = dates.date2num(array(self.Time[d]))
        current = array(self.Currents[d])

        plt.plot_date(t, current, 'b.-', xdate=True)
        ax1 = fig.get_axes()[0]
        m = self.Margins[d]
        format_yaxis(ax1, 'Current [nA]', col='b', ran=m['y'], size=20, grid=True)
        format_xaxis(ax1, 'Time [hh:mm]', ran=m['x'], size=20, grid=True, time=dates.DateFormatter('%H:%M'))
        ax1.yaxis.set_major_locator(ticker.MultipleLocator((m['y'][1] - m['y'][0]) / 8.))
        ax1.yaxis.set_minor_locator(ticker.MultipleLocator((m['y'][1] - m['y'][0]) / 16.))

        ax2 = ax1.twinx()
        voltage = array(self.Voltages[d])
        ax2.plot_date(t, voltage, 'r.-', xdate=True)

        format_xaxis(ax2, ran=m['x'])
        format_yaxis(ax2, 'Voltage [V]', ran=m['v'], size=20, col='r', grid=False)
        ax2.yaxis.set_major_locator(ticker.MultipleLocator((m['v'][1] - m['v'][0]) / 8.))
        ax2.yaxis.set_minor_locator(ticker.MultipleLocator((m['v'][1] - m['v'][0]) / 16.))

        plt.show()

    def draw_indep_graphs(self, rel_time=False, ignore_jumps=True):
        self.IgnoreJumps = ignore_jumps
        for device in self.Devices.iterkeys():
            self.ActiveDevice = self.Devices[device]
            if not self.Currents[device]:
                self.set_graphs(device, rel_time)
        for device in self.Devices:
            if 'Multi' in device:
                self.ActiveDevice = self.Devices[device]
                break
            self.ActiveDevice = self.Devices[device]
        self.make_graphs()

    def find_margins(self):
        d = self.ActiveDevice['dia']
        t = dates.date2num(self.Time[d])
        x = [t[0], t[-1]]
        dx = .05 * (x[1] - x[0])
        ymin, ymax = min(self.Currents[d]), max(self.Currents[d])
        dy = .05 * (ymax - ymin)
        if ymin > 0:
            ymin = 0
        else:
            ymin = ymin - dy if ymin < -1 else -1
        if ymax < 0:
            ymax = 0
        else:
            ymax = ymax + dy if ymax > 1 else 1
        xmax, xmin = min(self.Voltages[d]), max(self.Voltages[d])
        max_v = max(abs(xmin), abs(xmax))
        neg_v = True if xmin < 0 else False
        xmin, xmax = -1100, 1100
        if max_v < 200 and neg_v:
            xmin, xmax = -200, 0
        elif max_v < 200 and not neg_v:
            xmin, xmax = 0, 200
        return {'x': [x[0] - dx, x[1] + dx], 'y': [ymin, ymax], 'v': [xmin, xmax]}

    def set_margins(self, device):
        self.Margins[device] = self.find_margins()

    # endregion

    def print_run_times(self):
        print 'Starting with run {r1} at {t1}\nEnding   with run {r2} at {t2}'.format(r1=self.StartRun, r2=self.EndRun, t1=self.StartTime, t2=self.EndTime)


if __name__ == "__main__":
    pars = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    pars.add_argument('start_run', nargs='?', default='22008', help='start run to look at')
    pars.add_argument('end_run', nargs='?', default='', help='end run to look at, leave blank if you only want to look at a single run')
    pars.add_argument('-l', '--runlog', nargs='?', default='run_log.json', help='full path of the run_log.json file created by createRunList.py script (if not already in the program directory!)')
    pars.add_argument('-d', '--data', nargs='?', default='HV_CERN_08_2016', help='full path of hv data directory')
    pars.add_argument('-v', '--verbose', default=False, action='store_true', help='activate verbosity')
    args = pars.parse_args()
    print args
    end_run = args.end_run if args.end_run else args.start_run
    run_list = args.start_run, end_run
    print_banner('RD42 3D Currents')
    z = Currents(run_list, args.runlog, args.data, verbose=args.verbose)
    z.print_run_times()
    z.draw_indep_graphs()
