import csv
import json
from os import sep
import sys
import uuid
from io import StringIO

SETTINGS = {
    # 'distributed': False,                            # (Not actually used, despite docs)
    'generating': (True, False)[1],                    # (True generates, False modifies)
    # 'maxinputs': six.MAXSIZE,                        # (Not actually used, despite docs)
    # 'required_fields': ['field1'],                   # (Fields to return from remotes)
    # 'run_in_preview': True,                          # (Not actually used, despite docs)
    # 'streaming_preop': '| makeresults',              # (Filters data from remote searchers)
    'type': ('events', 'reporting', 'streaming')[0],   # (events run local, streaming remote)

    'can_alter_field_names': True,
    'use_multivalue_fields': True
}

SEARCH_INFO = {}
COMMAND_ARGS = None
FIELD_ORDER = []
RUNID = uuid.uuid4().int & (1<<64)-1
DL = "_ri%d" % (RUNID % 100 + 100)
SLASH, QUOTE, SPACE, EQUAL, VALUE, NAMED, GROUP, MULTI = DL + "l_", DL + "q_", DL + "s_", DL + "e_", DL + "v_", DL + "n_", DL + "g_", DL + "m_"
TRUES =  [ 'TRUE',  'T', 'YES', 'Y', 'YEP' ]
FALSES = [ 'FALSE', 'F', 'NO',  'N', 'NOPE' ]


class SplunkCSV(csv.Dialect):
    delimiter = ','
    doublequote = True
    lineterminator = '\n' if sys.platform == 'win32' else '\r\n'
    quotechar = '"'
    quoting = csv.QUOTE_MINIMAL
    skipinitialspace = False


def reverse_replace(reversed):
    return reversed.replace(EQUAL, "=").replace(SPACE, " ").replace(QUOTE, "\"").replace(SLASH, "\\")


def args_to_dict(rawrgs, array_duplicates=True):
    cleaned = []
    for dirty in rawrgs:
        clean = dirty
        clean = clean.replace("\\\\", SLASH).replace("\\\"", QUOTE).replace(" ", SPACE)
        eq_in = False
        for eq in ["\"=\"", "\"=", "=\"", "="]:
            if eq in clean:
                eq_in = True
                cleaner = clean.split(eq, 1)
                if len(cleaner[0]) > 0:
                    cleaned.append(cleaner[0].replace("\"", "").replace("=", EQUAL))
                cleaned.append("=")
                if len(cleaner[1]) > 0:
                    cleaned.append(cleaner[1].replace("\"", "").replace("=", EQUAL))
        if not eq_in:
            cleaned.append(clean)
    
    fields, equals, as_map, by_map, was_by = [], {}, {}, {}, False
    joined = ' '.join(cleaned).replace(" = ", VALUE).replace(" as ", NAMED).replace(" aS ", NAMED).replace(" As ", NAMED).replace(" AS ", NAMED)
    separated = joined.split(' ')

    for separate in separated:
        if VALUE in separate:
            left_right = [reverse_replace(side) for side in separate.split(NAMED)]
            right_upper = left_right[1].upper()
            if right_upper in TRUES or right_upper in FALSES:
                left_right[1] = right_upper in TRUES
            else:
                try:
                    left_right[1] = int(left_right[1])
                except ValueError:
                    try:
                        left_right[1] = float(left_right[1])
                    except ValueError:
                        pass
            if left_right[0] in equals and array_duplicates:
                equals[left_right[0]].append(left_right[1])
            elif left_right[0] not in equals and array_duplicates:
                equals[left_right[0]] = [left_right[1]]
            else:
                equals[left_right[0]] = left_right[1]
        elif NAMED in separate:
            left_right = [reverse_replace(side) for side in separate.split(NAMED)]
            if left_right[0] != '':
                fields.append(left_right[0])
            as_map[left_right[0]] = left_right[1]
            by_map[left_right[0]] = was_by
        elif separate.lower() == 'by':
            was_by = True
        elif separate != '':
            field = reverse_replace(separate)
            fields.append(field)
            by_map[field] = was_by
    return { 'originally': rawrgs, 'key_values': equals, 'fieldnames': fields, 'as_aliases': as_map, 'grouped_by': by_map }


def mv_row_handler(row, incoming=True):
    global FIELD_ORDER
    if not SETTINGS['use_multivalue_fields']:
        return row
    for field in row.keys():
        if field.startswith('__mv_') and incoming and row[field] != '':
            true_field = field.replace('__mv_', '', 1)
            mv_field = row[field].replace('$$', MULTI)[1:-1]
            mv_list = [mv_item.replace(MULTI, '$') for mv_item in filter(lambda x: x != '', mv_field.split('$;$'))]
            row[true_field] = mv_list
        else:
            if field not in FIELD_ORDER:
                FIELD_ORDER.append(field)
            if not incoming and isinstance(row[field], list):
                other_field = '__mv_%s' % field
                if len(row[field]) > 0:
                    mv_list = [mv_item.replace('$', "$$") for mv_item in row[field]]
                    mv_field = ('$%s$' if len(mv_list) > 0 else '%s') % '$;$'.join(mv_list)
                    row[field] = ' '.join(row[field])
                    row[other_field] = mv_field
                else:
                    row[field] = ''
                    row[other_field] = ''
    return row


def main(in_stream, out_stream):
    global COMMAND_ARGS
    global SEARCH_INFO
    global SETTINGS
    repeat = True
    while repeat:
        chunk_header = in_stream.readline()
        if len(chunk_header) == 0:
            break
        lengths = [int(num) for num in chunk_header.rstrip('\n').split(',')[1:]]

        metadata = in_stream.read(lengths[0])
        loaded_metadata = json.loads(metadata)
        if loaded_metadata['action'] == 'getinfo':
            SEARCH_INFO = loaded_metadata
            if 'searchinfo' in loaded_metadata and 'raw_args' in loaded_metadata['searchinfo'] and COMMAND_ARGS is None:
                COMMAND_ARGS = args_to_dict(loaded_metadata['searchinfo']['raw_args'])
                print(json.dumps(COMMAND_ARGS, indent=4), file=sys.stderr)
            if len(COMMAND_ARGS['fieldnames']) > 0:
                if COMMAND_ARGS['fieldnames'][0] == '+gen':
                    SETTINGS['generating'] = True
                    COMMAND_ARGS['fieldnames'] = COMMAND_ARGS['fieldnames'][1:]
                if COMMAND_ARGS['fieldnames'][0] == '-gen':
                    SETTINGS['generating'] = False
                    COMMAND_ARGS['fieldnames'] = COMMAND_ARGS['fieldnames'][1:]
            return_header = {
                'type': SETTINGS['type'],
                'generating': SETTINGS['generating']
            }
            if 'required_fields' in SETTINGS and SETTINGS['type'] == 'streaming':
                return_header['required_fields'] = SETTINGS['required_fields']
            if 'streaming_preop' in SETTINGS and SETTINGS['type'] == 'streaming':
                return_header['streaming_preop'] = SETTINGS['streaming_preop']
            output = ''
        else:
            if not loaded_metadata['finished']:
                return_header = {'finished': False}
            else:
                return_header = {'finished': True}
                repeat = False

            if lengths[1] == 0 and SETTINGS['generating']:
                create = StringIO()
                fields = generate_fieldnames()
                writer = csv.DictWriter(create, fieldnames=fields, dialect=SplunkCSV)
                writer.writeheader()
                for row in generate_rows():
                    writer.writerow(row)
                output = create.getvalue()
            else:
                events = in_stream.read(lengths[1])
                table = csv.DictReader(StringIO(events), dialect=SplunkCSV)
                alters = StringIO()
                if SETTINGS['can_alter_field_names']:
                    inspect_fieldnames(table.fieldnames)
                    result = alter_rows(table)
                    fields = FIELD_ORDER + ['__mv_%s' % field for field in FIELD_ORDER]
                    writer = csv.DictWriter(alters, fieldnames=fields, dialect=SplunkCSV)
                    writer.writeheader()
                    writer.writerows(result)
                else:
                    inspect_fieldnames(table.fieldnames)
                    fields = FIELD_ORDER + ['__mv_%s' % field for field in FIELD_ORDER]
                    writer = csv.DictWriter(alters, fieldnames=fields, dialect=SplunkCSV)
                    writer.writeheader()
                    alter_rows(table, writer)
                output = alters.getvalue()

        return_header = json.dumps(return_header)
        toit = 'chunked 1.0,%d,%d\n%s\n%s' % (len(return_header), len(output), return_header, output)
        out_stream.write(toit)
        out_stream.flush()


def generate_fieldnames():
    return []


def generate_rows():
    collection = [{}]
    for event in collection:
        yield event


def inspect_fieldnames(fields):
    global FIELD_ORDER
    for field in fields:
        if not field.startswith('__mv_'):
            FIELD_ORDER.append(field)


def alter_rows(table, writer=None):
    results = []
    for row in table:
        row = mv_row_handler(row)
        
        if writer:
            writer.writerow(row)
        else:
            results.append(mv_row_handler(row, False))
    return results


try:
    main(sys.stdin, sys.stdout)
except Exception:
    import traceback
    print(traceback.format_exc(), file=sys.stderr)
