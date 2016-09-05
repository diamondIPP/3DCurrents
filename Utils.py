# --------------------------------------------------------
#       Utility functions for 3DCurrent module
# created on September 5th 2016 by M. Reichmann (remichae@phys.ethz.ch)
# --------------------------------------------------------

from datetime import datetime
try:
    import termcolor
except ImportError:
    termcolor = False
try:
    import screeninfo
except ImportError:
    screeninfo = False


def log_warning(msg):
    t = datetime.now().strftime('%H:%M:%S')
    print '{head} {t} --> {msg}'.format(t=t, msg=msg, head=termcolor.colored('WARNING:', 'red') if termcolor else 'WARNING')


def convert_time(t):
    return datetime.strptime(t, '%a %b %d %H:%M:%S %Y')


def print_banner(msg, symbol='='):
    print '\n{delim}\n{msg}\n{delim}\n'.format(delim=len(str(msg)) * symbol, msg=msg)


def isfloat(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def round_down_to(num, val):
    return int(num) / val * val


def load_resolution():
    if not screeninfo:
        return 1000
    try:
        m = screeninfo.get_monitors()
        return round_down_to(m[0].height, 500)
    except Exception as err:
        log_warning(err)
        return 1000


def make_transparent(pad):
    pad.SetFillStyle(4000)
    pad.SetFillColor(0)
    pad.SetFrameFillStyle(4000)


def do_nothing():
    pass


def format_histo(histo, name='', title='', x_tit='', y_tit='', marker=20, color=1, markersize=1., x_off=None, y_off=None, lw=1, fill_color=0,
                 stats=True, tit_size=.04, x_range=None, y_range=None, do_marker=True, style=None):
    h = histo
    h.SetTitle(title) if title else h.SetTitle(h.GetTitle())
    h.SetName(name) if name else h.SetName(h.GetName())
    try:
        h.SetStats(stats)
    except AttributeError or ReferenceError:
        pass
    # markers
    try:
        if do_marker:
            h.SetMarkerStyle(marker) if marker is not None else do_nothing()
            h.SetMarkerColor(color) if color is not None else do_nothing()
            h.SetMarkerSize(markersize) if markersize is not None else do_nothing()
    except AttributeError or ReferenceError:
        pass
    # lines/fill
    try:
        h.SetLineColor(color) if color is not None else h.SetLineColor(h.GetLineColor())
        h.SetFillColor(fill_color)
        h.SetLineWidth(lw)
        h.SetFillStyle(style) if style is not None else do_nothing()
    except AttributeError or ReferenceError:
        pass
    # axis titles
    try:
        x_axis = h.GetXaxis()
        if x_axis:
            x_axis.SetTitle(x_tit) if x_tit else h.GetXaxis().GetTitle()
            x_axis.SetTitleOffset(x_off) if x_off is not None else do_nothing()
            x_axis.SetTitleSize(tit_size)
            x_axis.SetRangeUser(x_range[0], x_range[1]) if x_range is not None else do_nothing()
        y_axis = h.GetYaxis()
        if y_axis:
            y_axis.SetTitle(y_tit) if y_tit else y_axis.GetTitle()
            y_axis.SetTitleOffset(y_off) if y_off is not None else do_nothing()
            y_axis.SetTitleSize(tit_size)
            y_axis.SetRangeUser(y_range[0], y_range[1]) if y_range is not None else do_nothing()
    except AttributeError or ReferenceError:
        pass


def make_run_string(run1, run2):
    return run1 if run1 == run2 else '{r1} - {r2}'.format(r1=run1, r2=run2)
