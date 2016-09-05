#!/usr/bin/env python
# --------------------------------------------------------
#       Script to show the recorded current for the 3D beam test runs
# created on September 4th 2016 by M. Reichmann (remichae@phys.ethz.ch)
# --------------------------------------------------------

from datetime import datetime
from glob import glob
from time import sleep
from json import load
from collections import OrderedDict
import os.path

from ROOT import TCanvas, TText, TGraph, TPad, TGaxis
from ConfigParser import ConfigParser
from numpy import array
from argparse import ArgumentParser
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
        return {key: '{data}/{dev}_{ch}/'.format(data=self.DataDir, dev=dic['name'], ch=dic['ch']) for key, dic in self.Devices.iteritems()}
    # endregion

    # def set_device(self, nr, dia):
    #     self.reset_data()
    #     self.Number = self.get_device_nr(str(nr))
    #     self.Channel = self.get_device_channel(dia)
    #     self.Brand = self.ConfigParser.get('HV' + self.Number, 'name').split('-')[0].strip('0123456789')
    #     self.Model = self.ConfigParser.get('HV' + self.Number, 'model')
    #     self.Name = '{0} {1}'.format(self.Brand, self.Model)
    #     self.DataPath = self.find_data_path()

    def reset_data(self, device):
        self.Currents[device] = []
        self.Voltages[device] = []
        self.Time[device] = []

    def init_data(self):
        for device in self.Devices.iterkeys():
            self.reset_data(device)

    # endregion

    def draw_tpad(self, name, tit='', pos=None, fill_col=0, gridx=False, gridy=False, margins=None, transparent=False, logy=False, logx=False):
        margins = [.1, .1, .1, .1] if margins is None else margins
        pos = [0, 0, 1, 1] if pos is None else pos
        p = TPad(name, tit, *pos)
        p.SetFillColor(fill_col)
        p.SetMargin(*margins)
        p.SetLogy() if logy else do_nothing()
        p.SetLogx() if logx else do_nothing()
        p.SetGridx() if gridx else do_nothing()
        p.SetGridy() if gridy else do_nothing()
        make_transparent(p) if transparent else do_nothing()
        p.Draw()
        self.Stuff.append(p)
        return p

    def draw_axis(self, x1, x2, y1, y2, title, col=1, width=1, off=.15, tit_size=.035, lab_size=0.035, line=False, opt='+SU', tick_size=0.03, l_off=.01):
        range_ = [y1, y2] if x1 == x2 else [x1, x2]
        a = TGaxis(x1, y1, x2, y2, range_[0], range_[1], 510, opt)
        a.SetName('ax')
        a.SetLineColor(col)
        a.SetLineWidth(width)
        a.SetLabelSize(lab_size if not line else 0)
        a.SetTitleSize(tit_size)
        a.SetTitleOffset(off)
        a.SetTitle(title)
        a.SetTitleColor(col)
        a.SetLabelColor(col)
        a.SetLabelFont(42)
        a.SetTitleFont(42)
        a.SetTickSize(tick_size if not line else 0)
        a.SetNdivisions(0) if line else do_nothing()
        a.SetLabelOffset(l_off)
        a.Draw()
        self.Stuff.append(a)
        return a

    def draw_y_axis(self, x, ymin, ymax, tit, col=1, off=1., w=1, opt='+L', tit_size=.035, lab_size=0.035, tick_size=0.03, l_off=.01, line=False):
        return self.draw_axis(x, x, ymin, ymax, tit, col=col, off=off, opt=opt, width=w, tit_size=tit_size, lab_size=lab_size, tick_size=tick_size, l_off=l_off, line=line)

    def draw_x_axis(self, y, xmin, xmax, tit, col=1, off=1., w=1, opt='+L', tit_size=.035, lab_size=0.035, tick_size=0.03, l_off=.01, line=False):
        return self.draw_axis(xmin, xmax, y, y, tit, col=col, off=off, opt=opt, width=w, tit_size=tit_size, lab_size=lab_size, tick_size=tick_size, l_off=l_off, line=line)

    # ==========================================================================
    # region ACQUIRE DATA
    def get_logs_from_start(self, device):
        log_names = sorted([name for name in glob(self.DataPaths[device] + '*')])
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
        self.Time[device].append((self.StartTime - datetime(self.StartTime.year, 1, 1)).total_seconds())

    def set_stop(self, device, zero=False):
        self.Currents[device].append(self.Currents[device][-1] if not zero else 0)
        self.Voltages[device].append(self.Voltages[device][-1] if not zero else 0)
        self.Time[device].append((self.EndTime - datetime(self.EndTime.year, 1, 1)).total_seconds())

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
        total_seconds = (now - datetime(now.year, 1, 1)).total_seconds()
        if self.StartTime < now < self.EndTime and float(info[2]) < 1e30:
            index += 1
            if self.IgnoreJumps:
                if len(self.Currents[device]) > 100 and abs(self.Currents[device][-1] * 100) < abs(float(info[2]) * 1e9):
                    if abs(self.Currents[device][-1]) > 0.01:
                        return
                if 230 <= abs(float(info[2])) * 1e9 <= 250:
                    return
            self.Currents[device].append(float(info[2]) * 1e9)
            self.Time[device].append(total_seconds)
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
        self.make_graphs(device)
        self.set_margins(device)

    def draw_indep_graphs(self, rel_time=False, ignore_jumps=True):
        self.IgnoreJumps = ignore_jumps
        for device in self.Devices.iterkeys():
            self.ActiveDevice = self.Devices[device]
            if not self.Currents[device]:
                self.set_graphs(device, rel_time)
        c = TCanvas('c', 'Currents for Run {0}'.format(make_run_string(self.StartRun, self.EndRun)), int(self.Res * 1.5), int(self.Res * .75))
        pads = self.make_pads()
        self.draw_pads(pads)

        for device in self.Devices:
            if 'Multi' in device:
                self.ActiveDevice = self.Devices[device]
                break
            self.ActiveDevice = self.Devices[device]
        self.draw_voltage_pad(pads[0])
        self.draw_title_pad(pads[1])
        self.draw_current_pad(pads[2])

        self.Stuff.append([c] + pads)

    def draw_current_pad(self, pad):
        d = self.ActiveDevice['dia']
        pad.cd()
        self.draw_current_frame(pad)
        self.CurrentGraph[d].Draw('pl')

    def draw_voltage_pad(self, pad):
        d = self.ActiveDevice['dia']
        pad.cd()
        self.draw_voltage_frame(pad)
        self.VoltageGraph[d].Draw('p')
        self.draw_voltage_axis()

    def draw_title_pad(self, pad):
        pad.cd()
        text = 'Currents of the {dia} for run {r}'.format(dia=self.ActiveDevice['dia'], r=make_run_string(self.StartRun, self.EndRun))
        t1 = TText(0.08, 0.88, text)
        t1.SetTextSize(0.05)
        t1.Draw()
        self.Stuff.append(t1)

    def make_pads(self):
        p1 = self.draw_tpad('p1', gridy=True, margins=[.08, .07, .15, .15])
        p2 = self.draw_tpad('p2', transparent=True)
        p3 = self.draw_tpad('p3', gridx=True, margins=[.08, .07, .15, .15], transparent=True)
        return [p1, p2, p3]

    @staticmethod
    def draw_pads(pads):
        for p in pads:
            p.Draw()

    def find_margins(self):
        d = self.ActiveDevice['dia']
        x = [min(self.Time[d]), max(self.Time[d])]
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

    def make_graphs(self, device):
        tit = ' measured by {0}'.format(self.Devices[device]['name'])
        x = array(self.Time[device])
        # current
        y = array(self.Currents[device])
        g1 = TGraph(len(x), x, y)
        format_histo(g1, 'Current', 'Current' + tit, color=col_cur, markersize=.5)
        # voltage
        y = array(self.Voltages[device])
        g2 = TGraph(len(x), x, y)
        format_histo(g2, 'Voltage', 'Voltage' + tit, color=col_vol, markersize=.5)
        self.CurrentGraph[device] = g1
        self.VoltageGraph[device] = g2

    def draw_voltage_axis(self):
        m = self.Margins[self.ActiveDevice['dia']]
        vmin, vmax = m['v']
        a1 = self.draw_y_axis(m['x'][1], vmin, vmax, '#font[22]{Voltage [V]}', col=col_vol, off=.6, tit_size=.05, opt='+L', w=2, lab_size=label_size, l_off=.01)
        a1.CenterTitle()

    def draw_current_frame(self, pad):
        m = self.Margins[self.ActiveDevice['dia']]
        h2 = pad.DrawFrame(m['x'][0], m['y'][0], m['x'][1], m['y'][1])
        # X-axis
        h2.GetXaxis().SetTitle("#font[22]{time [hh:mm]}")
        h2.GetXaxis().SetTimeFormat("%H:%M")
        h2.GetXaxis().SetTimeOffset(-3600)
        h2.GetXaxis().SetTimeDisplay(1)
        h2.GetXaxis().SetLabelSize(label_size)
        h2.GetXaxis().SetTitleSize(axis_title_size)
        h2.GetXaxis().SetTitleOffset(1.05)
        h2.GetXaxis().SetTitleSize(0.05)
        # Y-axis
        h2.GetYaxis().SetTitleOffset(0.6)
        h2.GetYaxis().SetTitleSize(0.05)
        h2.GetYaxis().SetTitle("#font[22]{Current [nA]}")
        h2.GetYaxis().SetTitleColor(col_cur)
        h2.GetYaxis().SetLabelColor(col_cur)
        h2.GetYaxis().SetAxisColor(col_cur)
        h2.GetYaxis().CenterTitle()
        h2.GetYaxis().SetLabelSize(label_size)
        h2.GetYaxis().SetTitleSize(axis_title_size)
        h2.GetYaxis().SetTitleOffset(.6)
        # self.Stuff.append(h2)

    def draw_voltage_frame(self, pad):
        m = self.Margins[self.ActiveDevice['dia']]
        h1 = pad.DrawFrame(m['x'][0], m['v'][0], m['x'][1], m['v'][1])
        h1.SetTitleSize(axis_title_size)
        h1.GetXaxis().SetTickLength(0)
        h1.GetYaxis().SetTickLength(0)
        h1.GetXaxis().SetLabelOffset(99)
        h1.GetYaxis().SetLabelOffset(99)
        h1.SetLineColor(0)
    # endregion

    def print_run_times(self):
        print 'Starting with run {r1} at {t1}\nEnding   with run {r2} at {t2}'.format(r1=self.StartRun, r2=self.EndRun, t1=self.StartTime, t2=self.EndTime)


if __name__ == "__main__":
    pars = ArgumentParser()
    pars.add_argument('start_run', nargs='?', default='22008')
    pars.add_argument('end_run', nargs='?', default='')
    pars.add_argument('-l', '--runlog', nargs='?', default='run_log.json')
    pars.add_argument('-d', '--data', nargs='?', default='HV_DATA')
    pars.add_argument('-v', '--verbose', default=False, action='store_true')
    args = pars.parse_args()
    print args
    end_run = args.end_run if args.end_run else args.start_run
    run_list = args.start_run, end_run
    print_banner('RD42 3D Currents')
    z = Currents(run_list, args.runlog, args.data, verbose=args.verbose)
    z.print_run_times()
    z.draw_indep_graphs()
