#!/usr/bin/python3

import sys, re
from enum import Enum
from difflib import unified_diff
import argparse

parser = argparse.ArgumentParser(description='Parse output of terraform plan and report changes and stats')
parser.add_argument('-q', '--quiet', help='Report count of changes instead of human readable diff',
        action='store_true', default=False)
args = parser.parse_args()

# this var is used to count diff between current state and wanted state
diff_count = 0

stack_list_item_re = re.compile('^rancher_stack\.([a-zA-Z-]+):\sRefreshing\sstate...')
stack_diff_header_re = re.compile('^(~|\+|-)\srancher_stack\.([a-zA-Z-]+)$')
catalog_env_diff_re = re.compile('^\s*environment\.([\w%_-]+):\s*"([^"]*)"\s*=>\s*"([^"]*)"$')
catalog_id_diff_re = re.compile('^\s*catalog_id:\s*"([^"]*)"\s*=>\s*"([^"]*)"$')
compose_diff_re = re.compile('^\s*(rancher_compose|docker_compose):\s*"([^"]*)"\s*=>\s*"([^"]*)"$')
extract_diff_re = re.compile('([^:]+):\s+"(.*)"\s+=>\s+"(.*)"$')

convert_diff_type = {
        '+': 'Adding',
        '~': 'Modifying',
        '-': 'Deleting'}

class State(Enum):
    BEFORE_STACK_LIST = "Before stack list"
    STACK_LIST = "Stack list"
    AFTER_STACK_LIST = "After stack list"
    STACK_DIFF = "Stack Diff"


def parse_stack_list_line(line):
    # _print("List line : %s" % line)
    pass

def _print(line=''):
    if not args.quiet:
        print(line)

def parse_compose_diff_line(line, diff_type, stack_name):
    _print('''######################
# %s %s
######################
    ''' % (convert_diff_type[diff_type], stack_name))
    line = line.strip()
    if diff_type != '~':
        return
    # _print("Parsing : %s" % line)
    matches = extract_diff_re.match(line)
    item = matches.group(1)
    diff1 = matches.group(2).replace('\\n', '\n').splitlines()
    diff2 = matches.group(3).replace('\\n', '\n').splitlines()
    diff = unified_diff(diff1, diff2, n=100000)
    _print("* %s:\n----------\n" % item)
    i = 1
    for line in diff:
        if i > 3:
            _print(line)
        i += 1
    _print()
    # update diff count
    global diff_count
    local_diff_count = 0
    for line in unified_diff(diff1, diff2, n=0):
        local_diff_count += 1
    diff_count = diff_count + max(0, local_diff_count - 3)

def parse_catalog_env_diff_line(line, diff_type, stack_name):
    #_print("Catalog env line %s" % line)
    matches = catalog_env_diff_re.match(line)
    var = matches.group(1)
    old_value = matches.group(2)
    new_value = matches.group(3)
    if var == '%':
        _print('''######################
# Modifying catalog env %s
######################
''' % stack_name)
    _print("%s: %s => %s" % (var, old_value, new_value))
    global diff_count
    diff_count += 1

def parse_catalog_id_diff_line(line, diff_type, stack_name):
    matches = catalog_id_diff_re.match(line)
    old_value = matches.group(1)
    new_value = matches.group(2)
    _print('''######################
# Modifying catalog version %s
######################
%s => %s''' % (stack_name, old_value, new_value))
    global diff_count
    diff_count += 1

state = State.BEFORE_STACK_LIST

for line in sys.stdin:
    # remove trailling new line
    line = line.strip("\n")
    # _print("%s : %s" % (state, line))

    if state == State.BEFORE_STACK_LIST:
        if stack_list_item_re.match(line) is not None:
            state = State.STACK_LIST
            parse_stack_list_line(line)
    elif state == State.STACK_LIST:
        if stack_list_item_re.match(line) is None:
            state = State.AFTER_STACK_LIST
        else:
            parse_stack_list_line(line)
    elif state == State.AFTER_STACK_LIST:
        if stack_diff_header_re.match(line) is not None:
            state = State.STACK_DIFF
            matches = stack_diff_header_re.match(line)
            diff_type = matches.group(1)
            current_stack_name = matches.group(2)
    elif state == State.STACK_DIFF:
        if catalog_env_diff_re.match(line) is not None:
            parse_catalog_env_diff_line(line, diff_type, current_stack_name)
        elif catalog_id_diff_re.match(line) is not None:
            parse_catalog_id_diff_line(line, diff_type, current_stack_name)
        elif compose_diff_re.match(line) is not None:
            parse_compose_diff_line(line, diff_type, current_stack_name)
        else:
            if not args.quiet:
                _print()
            state = State.AFTER_STACK_LIST

if not args.quiet:
    print("Total diff count : %s" % diff_count)
else:
    print(diff_count)

