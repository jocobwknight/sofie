from __future__ import print_function, unicode_literals
import os
import sys
import csv
import json
from datetime import datetime
from collections import OrderedDict

"""
What? This script can handle Splunk Custom Search Commands (V2) with only built-ins, and in a single 150-LOC script

Why?  1.) Squeezing any bit of performance I can; 2.) Low-level control; 3.) Because it's cool; 4.) To understand it

How?  Read on! It's essentially just string manipulation and stdin/stdout transactions with the splunkd process
"""

LOGS = os.path.abspath(__file__) + '.log'
"""{
    "action": "getinfo",
    "preview": false,
    "streaming_command_will_restart": false,
    "searchinfo": {
        "args": ["take my", "breath=away"],
        "raw_args": ["\"take my\"", "breath=away"],
        "dispatch_dir": "...",
        "sid": "...",
        "app": "custom",
        "owner": "them",
        "username": "you",
        "session_key": "...",
        "splunkd_uri": "https://127.0.0.1:8089",
        "splunk_version": "8.0.5",
        "search": "...",
        "command": "custom",
        "maxresultrows": 0,
        "earliest_time": "0",
        "latest_time": "0"
    }
}"""
META = {}  # Sample above
BODY = []  # Comes in as CSV, but converted to list of OrderedDict objects for each record
EXECUTING, EXECUTED = {'finished': False}, {'finished': True}


if sys.version_info[0] == 2:  # TODO: Need to test this on Python3
    from io import BytesIO
    def hear(i, s): return i.read(s)
    def tell(i, c): i.write(c)
    def hold(): return BytesIO()
else:
    from io import StringIO
    def hear(i, s): return i.buffer.read(s).decode('utf-8')
    def tell(i, c): i.buffer.write(bytes(c, encoding='utf-8'))
    def hold(): return StringIO()


# TODO: Pretty much the cheapest way to log. You could log directly into Splunk, or you just give up on self-respect
def log(it, nw=False):
    it = str(it)
    with open(LOGS, ('w' if nw else 'a')) as a:
        a.write(str(datetime.now()) + ' ' + it + ('' if it.endswith('\n') else '\n'))


# TODO: Read directly into the csv.reader so it's not storing the data twice
def order(c):
    full = list(csv.reader(c.splitlines()))
    return [OrderedDict(zip(full[0], r)) for r in full[1:]]


# TODO: Read the meta directly with json.load so it's not storing twice (like the body)
def read(i):
    header = i.readline()
    parts = header.split(',')  # Header will be: chunked 1.0,{int: meta length},{int: body length}
    meta_len, body_len = int(parts[1]), int(parts[2])  # IMPORTANT: these lengths are character count, not bytes
    meta = json.loads(hear(i, meta_len))
    if body_len > 0:
        body = order(hear(i, body_len))
    else:
        body = []
    return meta, body


# TODO: Same thing, write to json.dump / csv.writer directly. Avoided because of PY2/3 buffering differences but...
def write(o, m, b):
    m = json.dumps(m)
    p = hold()
    w = csv.writer(p)
    if len(b) > 0:
        w.writerow(list(b[0].keys()))
        for r in b:
            v = []
            for j, u in r.items():
                v.append(u)
            w.writerow(v)
        b = p.getvalue()
    else:
        b = ''
    h = 'chunked 1.0,%d,%d' % (len(m), len(b))
    tell(o, '\n'.join((h, m, b) if len(b) > 0 else (h, m)))
    o.flush()


# TODO: Despite the claims, Splunk fires up the process several times. It would be nice to cache the meta on sid...
def getinfo(meta):
    global META
    META = meta
    meta = INFO if meta['action'] == 'getinfo' else (EXECUTED if meta['finished'] else EXECUTING)
    return meta


def transaction(i=sys.stdin, o=sys.stdout):
    meta, body = read(i)
    meta, body = getinfo(meta), ([] if meta['action'] == 'getinfo' else execute(body))
    write(o, meta, body)
    return 'finished' in meta and meta['finished']


def main():
    while not transaction():
        pass


# From here should be all you have to worry about for all the behavior...

"""  Here are the GetInfo options I could glean from code analysis... (change the INFO constant accordingly)
                    eventing         reporting        streaming
distributed         False            False            True*|False
generating          True|False*      True|False*      True|False*
maxinputs           < limits.conf    < limits.conf    < limits.conf
required_fields     ['fn', ...]      ['fn', ...]      ['fn', ...]
requires_preop      N/A              N/A              True|False*
run_in_preview      N/A              True*|False      N/A
streaming_preop     N/A              N/A              '{SPL}'
type                'events'         'reporting'      'streaming'
*-default  """
INFO = {"type": "streaming", 'distributed': True}  # TODO: A lot of permutations here. This needs a lot of testing


def execute(body):
    """Handles manipulating the body
    :param body: [OrderedDict(...), ...]
    :return: [OrderedDict(...), ...]"""
    global BODY   # Not necessary unless you want to wait for META['finished'] to handle all events
    BODY += body  # ...but to so that, make sure to change META['finished'] to False while sending non-final chunks
    return body   # (This example just sends the chunk right back after converting to and from runtime objects)
# ...to here


main()  # TODO: Now that we've "cracked the code" behind SCP2, just translate it into something fast like Go
