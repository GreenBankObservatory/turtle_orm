#!/usr/bin/env python3

import argparse
import inspect
import os
import pkgutil

import dateutil.parser as dp
import IPython
from colorama import Fore, Back, Style
import difflib

from django.utils import timezone
from django.db.models import Sum

from turtlecli.utils import (
    formatHistoryTable,
    DEFAULT_HISTORY_TABLE_HEADERS,
    DEFAULT_HISTORY_TABLE_FIELDNAMES
)

from turtlecli import subcommands

from tortoise.models import History

"""docstring"""


def filterByTime(dt, buffer):
    return History.objects.filter(
        datetime__gte=dt - buffer,
        datetime__lte=dt + buffer
    )

def filterByRange(start, end):
    results = History.objects.all()
    if start:
        results &= History.objects.filter(datetime__gte=start)
    if end:
        results &= History.objects.filter(datetime__lte=end)
    return results

def filterByProject(project_names):
    return History.objects.filter(obsprocedure__obsprojectref__name__in=project_names)

def filterByScript(script_names):
    return History.objects.filter(obsprocedure__name__in=script_names)


def parse_args():
    parser = argparse.ArgumentParser()

    # subparsers = parser.add_subparsers(
    #     title='subcommands',
    #     # description='valid subcommands',
    #     # help='sub-command help'
    # )
    # # Required due to argparse bug: https://stackoverflow.com/a/18283730/1883424
    # subparsers.required = True
    # subparsers.dest = 'subcommand'

    # for importer, module_name, _ in pkgutil.iter_modules([os.path.dirname(__file__) + "/subcommands"]):
    #     # Use level_name_regex to identify relevant "level" modules
    #     module = importer.find_module(module_name).load_module(module_name)
    #     module.add_parser(subparsers)

    parser.add_argument(
        '--observer',
        help='Filter for given observer'
    )

    parser.add_argument(
        '--operator',
        help='Filter for given operator'
    )

    parser.add_argument(
        '--time',
        metavar='DATETIME',
        type=dp.parse,
        help='The time of the thing'
    )
    parser.add_argument(
        '-B', '--buffer',
        type=float,
        default=0.25,
        help='Designates the size of the window that projects '
             'will be searched for within. Units are determined by --units. '
             'Note that the default will only be reasonable if the default '
             'unit is used.'
    )
    parser.add_argument(
        '--projects',
        metavar='PROJECT',
        nargs='+',
        help='The name(s) of the project(s). If multiple projects are given, '
             'then results will be shown for all of them'
    )
    parser.add_argument(
        '--scripts',
        metavar='SCRIPT',
        nargs='+',
        help='The name(s) of the script(s). If multiple scripts are given, '
             'then results will be shown for all of them. If --projects is '
             'given, only scripts from within the given project will be shown. '
             'NOTE: This option may give unexpected results if --projects is not specified, '
             'since script names are not guaranteed to be unique across all projects!'
    )
    parser.add_argument(
        '-l', '--last',
        metavar="DELTA",
        type=float,
        help='Limit to scripts executed within the last DELTA time units. '
             'See --units for details on time unit options'
    )
    parser.add_argument(
        '-a', '--after',
        metavar='DATETIME',
        type=dp.parse,
        help='Limit to scripts executed after this time'
    )
    parser.add_argument(
        '-b', '--before',
        metavar='DATETIME',
        type=dp.parse,
        help='Limit to scripts executed before this time'
    )

    parser.add_argument(
        '-g', '--group-by',
        default='project',
        # These are simply what I consider a reasonable set of things to filter by
        choices=['id', 'obsprocedure', 'observer', 'operator', 'datetime']
    )

    parser.add_argument(
        '-o', '--order-by',
        type=order_type,
        default='datetime',
        # These are simply what I consider a reasonable set of things to filter by
        choices=['id', 'obsprocedure', 'observer', 'operator', 'datetime']
    )

    parser.add_argument(
        '--direction',
        default='descending',
        choices=['ascending', 'descending']
    )

    parser.add_argument(
        '-u', '--unit',
        default='hours',
        # All (reasonable) choices that can be set for timedelta
        choices=['seconds', 'minutes', 'hours', 'days', 'weeks']
    )

    parser.add_argument(
        '--diff',
        action='store_true',
        help='Show the differences between the script for each result'
    )

    parser.add_argument(
        '--logs',
        action='store_true',
        help='Show the logs for each result'
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Drop into an interactive shell after the '
             'query is performed'
    )



    args = parser.parse_args()
    if args.buffer < 0:
        parser.error("--buffer value must be greater than 0")
    # try:
    args.buffer = timezone.timedelta(**{args.unit: args.buffer})
    # except:
    return args

def order_type(foo):
    return foo

def in_ipython():
    """Determine whether this script is being run via IPython; return bool"""

    try:
        __IPYTHON__
    except NameError:
        # logger.debug("Not in IPython")
        return False
    else:
        # logger.debug("In IPython")
        return True


# From: https://chezsoi.org/lucas/blog/colored-diff-output-with-python.html 
def color_diff(diff):
    for line in diff:
        if line.startswith('+'):
            yield Fore.GREEN + line + Fore.RESET
        elif line.startswith('-'):
            yield Fore.RED + line + Fore.RESET
        elif line.startswith('^'):
            yield Fore.BLUE + line + Fore.RESET
        else:
            yield line

def gen2(l):
    """Given an iterable, generate tuples of every two elements

    In : list(gen2([1,2,3]))
    Out: [(1, 2), (2, 3)]
    """

    for i in range(len(l) - 1):
        yield (l[i], l[i+1])


def summarize_script_changes(results, interactive=False):
    # Iterate through results as pairs -- that is, grab every two items out at a time
    for result_a, result_b in gen2(results):
        print("{color}Differences between scripts A (executed {a}) and B (executed {b}){reset}"
              .format(color=Fore.BLUE,
                      a=result_a.datetime,
                      b=result_b.datetime,
                      reset=Fore.RESET))

        diff = diff_scripts(result_a.executed_script, result_b.executed_script)
        print('\n'.join(diff))
        if interactive:
            print("-"*80)
            response = input("{}Press any key to see the next diff (or 'q' to exit the loop) {}"
                             .format(Fore.BLUE, Fore.RESET))
            if response.lower().startswith("q"):
                break


def summarize_logs(results, interactive=False):
    for result in results:
        print("{color}Logs for script {script}, executed at {exec} by observer {observer}{reset}"
              .format(color=Fore.BLUE,
                      observer=result.observer.name,
                      script=result.obsprocedure.name,
                      exec=result.datetime,
                      reset=Fore.RESET))

        print(result.log)
        print("-"*80)
        if interactive:
            response = input("{}Press any key to see the next log (or 'q' to exit the loop) {}"
                             .format(Fore.BLUE, Fore.RESET))
            if response.lower().startswith("q"):
                break


def diff_scripts(script_a, script_b, compact=True):
    script_a_lines = script_a.split('\n')
    script_b_lines = script_b.split('\n')

    if compact:
        diff = difflib.unified_diff(script_a_lines, script_b_lines)
    else:
        diff = difflib.ndiff(script_a_lines, script_b_lines)
    colordiff = color_diff(diff)
    return colordiff

def main():
    args = parse_args()

    description_parts = []
    results = History.objects.all()
    if args.projects:
        plural = 's' if args.projects and len(args.projects) > 1 else ''
        description_parts.append("for project{} {}"
                                 .format(plural, args.projects))
        results &= filterByProject(args.projects)

    if args.scripts:
        plural = 's' if args.scripts and len(args.scripts) > 1 else ''
        description_parts.append("for script{} {}"
                                 .format(plural, args.scripts))
        results &= filterByScript(args.scripts)

    if args.observer:
        description_parts.append("by observer {}".format(args.observer))
        results &= History.objects.filter(observer__name=args.observer)

    if args.operator:
        description_parts.append("with operator {}".format(args.operator))
        results &= History.objects.filter(operator__name=args.operator)


    if args.time:
        description_parts.append("that occurred within {} {} of {}"
                                 .format(args.buffer, args.unit, args.time))
        results &= filterByTime(args.time, args.buffer)

    if args.last:
        description_parts.append("that occurred within the last {} {}".format(args.last, args.unit))
        now = timezone.datetime.now()
        delta_start = now - timezone.timedelta(**{args.unit: args.last})
        results &= filterByRange(delta_start, now)

    if args.after or args.before:
        if args.after and args.before:
            description_parts.append("executed after {} but before {}".format(args.after, args.before))
        elif args.after or args.before:
            if args.after:
                description_parts.append("executed after {}".format(args.after))
            elif args.after:
                description_parts.append("executed before {}".format(args.before))
        results &= filterByRange(args.after, args.before)

    # The following operations only make sense if results have been found
    if results and args.order_by:
        description_parts.append("ordered by {} ({})"
                                 .format(args.order_by, args.direction))
        field = "{}{}".format('-' if args.direction == 'descending' else '',
                              args.order_by)
        results = results.order_by(field)

    # if args.group_by:
    #     results = results.group_by(args.group_by)

    if results:
        print("Displaying scripts {}".format(", ".join(description_parts)))
        print(formatHistoryTable(results))
    else:
        print("No scripts found {}".format(", ".join(description_parts)))

    print()

    if args.diff:
        print("Showing differences between all above results{}"
              .format(", interactively" if args.interactive else ""))
        # Note that we assume an interactive session if --interactive is set
        summarize_script_changes(results, interactive=args.interactive)


    if args.logs:
        print("Showing logs for all above results{}"
              .format(", interactively" if args.interactive else ""))
        summarize_logs(results, interactive=args.interactive)
        
    # If the user has requested an interactive session, enter it now.
    # However, don't bother trying if we are already being run via IPython,
    # because it won't work
    if args.interactive and not in_ipython():
        print("Results are available in the `results` variable.")
        # logger.debug("Entering interactive mode")
        IPython.embed(display_banner=False, exit_msg="Hope you had fun!")
        # logger.debug("Exited interactive mode")

    # Execute the selected subcommand
    # try:
    #     args.func(args)
    # except AttributeError as error:
    #     raise AttributeError("Every subparser must set its 'func' attribute! "
    #                          "Use 'parser.set_defaults(func=getByTime)'") from error


if __name__ == '__main__':
    main()
