# --------------------------------------------------------
#       Utility functions for 3DCurrent module
# created on September 5th 2016 by M. Reichmann (remichae@phys.ethz.ch)
# --------------------------------------------------------

from datetime import datetime
from matplotlib import dates
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
    t = ' '.join(t.split(' ')[1:])
    return datetime.strptime(str(t), '%b %d %H:%M:%S %Y')


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


def execute(cmd, args, ex=None):
    ex = args if ex is None else ex
    args = [args] if (type(args) is not list and type(args) is not dict) else args
    if type(args) is list:
        cmd(*args) if ex is not None else do_nothing()
    else:
        cmd(**args) if ex is not None else do_nothing()


def format_yaxis(ax, tit=None, ran=None, size=12, col=None, grid=None):
    execute(ax.set_ylabel, {'ylabel': tit, 'color': col if col is not None else 'black', 'size': size}, tit)
    execute(ax.set_ylim, ran)
    for tl in ax.get_yticklabels():
        execute(tl.set_color, col)
    execute(ax.grid, [grid, 'major', 'y'], grid)


def format_xaxis(ax, tit=None, ran=None, size=12, col=None, grid=None, time=None):
    execute(ax.set_xlabel, {'xlabel': tit, 'color': col if col is not None else 'black', 'size': size}, tit)
    execute(ax.set_xlim, ran)
    for tl in ax.get_xticklabels():
        execute(tl.set_color, col)
    execute(ax.grid, [grid, 'major', 'x'], grid)
    execute(ax.xaxis.set_major_formatter, time)
    execute(ax.xaxis.set_major_locator, dates.MinuteLocator(interval=30), time)


def make_transparent(pad):
    pad.SetFillStyle(4000)
    pad.SetFillColor(0)
    pad.SetFrameFillStyle(4000)


def do_nothing():
    pass


def make_run_string(run1, run2):
    return run1 if run1 == run2 else '{r1} - {r2}'.format(r1=run1, r2=run2)
