#!/usr/bin/env python3

import argparse
import inspect
import logging
import os
import pkgutil

import dateutil.parser as dp
import IPython

from django.utils import timezone
from django.db.models import Q

from tortoise.models import History

from turtlecli.filters import (
    filterByTime,
    filterByRange,
    filterByProject,
    filterByScript
)

from turtlecli.utils import (
    genHistoryTable,
    order_type,
    in_ipython,
    gen2,
    formatSql,
    DEFAULT_HISTORY_TABLE_FIELDNAMES
)

from turtlecli.reports import DiffReport, LogReport, ScriptReport


"""Commandline Interface to the Turtle DB"""


logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--observers',
        nargs='+',
        metavar='OBSERVER',
        help='Filter for given observer(s)'
    )

    parser.add_argument(
        '--operators',
        nargs='+',
        metavar='OPERATOR',
        help='Filter for given operator(s)'
    )

    # TODO: Allow multiple options here
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
        '-a', '--after', '--start',
        metavar='DATETIME',
        type=dp.parse,
        help='Limit to scripts executed after this time'
    )
    parser.add_argument(
        '-b', '--before', '--end',
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
        # TODO: --diff is deprecated                        
        '--show-diffs', '--diff',
        action='store_true',
        help='Show the differences between the script for each result'
    )

    parser.add_argument(
        '--show-logs', '--logs',
        # TODO: --logs is deprecated        
        action='store_true',
        help='Show the logs for each result'
    )

    parser.add_argument(
        '--show-scripts',
        action='store_true',
        help='Show the contents of the executed script for each result'
    )

    parser.add_argument(
        '--state',
        help="Filter based on the state of script execution",
        choices=['completed', 'in_progress', 'aborted']
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit results to the given number'
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Drop into an interactive shell after the '
             'query is performed'
    )

    parser.add_argument(
        '--fuzzy',
        action='store_true',
        help='Make searches fuzzier (case insensitive, incomplete matches, etc.). Note that this will probably be a bit slower.'
    )

    # TODO: Fuzzy option. Would do things like search for names using icontains
    # TODO: Search within scripts/logs. Obviously slow, but could be useful
    args = parser.parse_args()

    ### Additional error checking ###

    # Ensure that the many time-related options aren't given together
    time_arg_bools = [
        bool(args.time),
        bool(args.last),
        bool(args.after or args.before)
    ]
    if time_arg_bools.count(True) > 1:
        parser.error("Only one of {}, {}, or {} may be given"
                     .format("--time",
                             "--last",
                             "(--after or --before)"))

    # Ensure that --buffer isn't given without --time
    # TODO: buffer has a default -- how to handle?
    # if args.buffer and not args.time:
    #     parser.error("--buffer has no effect if --time is not given!")

    # Ensure that the buffer isn't negative
    if args.buffer < 0:
        parser.error("--buffer value must be greater than 0")
    args.buffer = timezone.timedelta(**{args.unit: args.buffer})

    return args


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

    if args.observers:
        plural = 's' if args.observers and len(args.observers) > 1 else ''
        description_parts.append("by observer{} {}"
                                 .format(plural, args.observers))
        if args.fuzzy:
            query = Q()
            for observer in args.observers:
                query = Q(observer__name__icontains=observer)
            results &= History.objects.filter(query)
        else:
            results &= History.objects.filter(observer__name__in=args.observers)

    if args.operators:
        plural = 's' if args.operators and len(args.operators) > 1 else ''
        description_parts.append("with operator{} {}"
                                 .format(plural, args.operators))
        results &= History.objects.filter(operator__name__in=args.operators)

    if args.state:
        # Argument choices are shortened forms of the possible field values
        state = "obs_{}".format(args.state)
        description_parts.append("with state {}".format(state))
        results &= History.objects.filter(executed_state=state)
        
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

    # TODO: Consider testing results only once?
    # The following operations only make sense if results have been found
    if results.exists() and args.order_by:
        description_parts.append("ordered by {} ({})"
                                 .format(args.order_by, args.direction))
        field = "{}{}".format('-' if args.direction == 'descending' else '',
                              args.order_by)
        results = results.order_by(field)

    # This must occur after ordering!
    if results.exists() and args.limit:
        results = results[:args.limit]

    # if args.group_by:
    #     results = results.group_by(args.group_by)

    # TODO: Only show if verbosity >1 ?
    print("Executing query:")
    print(formatSql(str(results.query)))

    if results.exists():
        df = results.to_dataframe(fieldnames=DEFAULT_HISTORY_TABLE_FIELDNAMES)
        print("Displaying scripts {}".format(", ".join(description_parts)))
        print(genHistoryTable(df))
    else:
        print("No scripts found {}".format(", ".join(description_parts)))

    print()

    if args.show_scripts:
        ScriptReport(results, args.interactive).print_report()

    if args.show_diffs:
        if set(results.values_list('obsprocedure__name', flat=True)):
            logger.warning("Multiple script names detected; diffs may not make much sense!")
        DiffReport(results, args.interactive).print_report()

    if args.show_logs:
        LogReport(results, args.interactive).print_report()

    # If the user has requested an interactive session, enter it now.
    # However, don't bother trying if we are already being run via IPython,
    # because it won't work
    if args.interactive and not in_ipython():
        r = results
        logger.debug("Entering interactive mode")
        print("Results are available as:")
        print("  * A QuerySet, in the `r` variable.")
        print("  * As a DataFrame, in the `df` variable.")
        IPython.embed(display_banner=False, exit_msg="Hope you had fun!")
        logger.debug("Exited interactive mode")


if __name__ == '__main__':
    main()

# TODO: Search within scripts. Allow regex or wildcard
# TODO: Search within logs. Allow regex or wildcard
# TODO: Flesh out logging
# TODO: Finish refactoring of codebase
# TODO: Consider subcommands for things like "Show me details about a specific ObsProcedure" -- this is history-centric so far
# TODO: Port over the code from findObsScript that handles parsing of config keywords
# TODO: Provide easy way to search scheduling block executions (from log files)?
# TODO: Add --interactive-reports
# TODO: Unit tests!
# TODO: Sphinx documentation -- how best to document each argument (with examples)?
# TODO: Doctests -- this seems like the perfect application
