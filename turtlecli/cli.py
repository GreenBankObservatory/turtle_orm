#!/usr/bin/env python3
"""Commandline Interface to the Turtle DB"""

import argparse
import logging
import os
import shlex
import sys

import dateutil.parser as dp
from dateutil.relativedelta import relativedelta
import IPython

from django.utils import timezone
from django.db.models import Q
from django.db import connections

from tortoise.models import History
from turtlecli.filters import (
    filterByRange,
    filterByProject,
    filterByScript,
    filterByObserver,
    filterByOperator,
)
from turtlecli.utils import (
    genHistoryTable,
    in_ipython,
    formatSql,
    DEFAULT_HISTORY_TABLE_FIELDNAMES,
    get_console_width,
    format_date_time,
    iterable_to_fancy_string,
)
from turtlecli.reports import DiffReport, LogReport, ScriptReport
from turtlecli.gitify import gitify


FILE_LOGGER = logging.getLogger("{}_file".format(__name__))
CONSOLE_LOGGER = logging.getLogger("{}_user".format(__name__))


def parse_kwargs(kwargs_list):
    """Given an iterable of keyward-value strings of the format "keyword=value"
    parse them into a dict and return it.

    Values will be stripped of whitespace.
    """
    split = [[val.strip() for val in kwarg.split("=")] for kwarg in kwargs_list]
    CONSOLE_LOGGER.debug("Split %s into %s", split, kwargs_list)
    kwargs = {keyword: value for keyword, value in split}
    CONSOLE_LOGGER.debug("Converted %s into %s", split, kwargs)
    return kwargs


def parse_args():
    console_width = get_console_width()
    width = console_width * 0.8 if console_width > 80 / 0.8 else 80
    parser = argparse.ArgumentParser(
        prog="turtlecli",
        description="A program for easily querying the Turtle database",
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(
            prog, width=width
        ),
    )

    ### General Group ###
    general_group = parser.add_argument_group(
        title="General", description="General-purpose arguments"
    )
    general_group.add_argument(
        "-L", "--limit", type=int, default=10, help="Limit results to the given number"
    )
    general_group.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Drop into an interactive shell after the query is performed",
    )
    general_group.add_argument(
        "--exact",
        action="store_true",
        help="Make searches more precise, and faster. This will perform exact, "
        "case-insensitive searches on things like observer name, project name, etc.",
    )
    general_group.add_argument(
        "--regex",
        action="store_true",
        help="Indicates that given search terms are MySQL-style regular expressions. For "
        "example, if this is given then --project-names '^AGBT.*72$' would be treated "
        "as a regular expression and all resultls in which the project name starts "
        " with AGBT and ends with 72 would be returned",
    )
    general_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Make output more verbose. Note: this will display SQL "
        "queries made during the initial query",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Specify the logging level. Note that "
        "this will override --verbose, if both "
        "are present.",
    )

    ### Things Group ###
    things_group = parser.add_argument_group(
        title="Entities", description="Arguments that relate to filtering by entity"
    )
    things_group.add_argument(
        "-p",
        "--project-names",
        "--project",
        "--projects",
        metavar="PROJECT",
        nargs="+",
        help="The name(s) of the project(s). If multiple projects are given, "
        "then results will be shown for all of them. Respects --regex",
    )
    things_group.add_argument(
        "-s",
        "--script-names",
        "--script",
        "--scripts",
        metavar="SCRIPT",
        nargs="+",
        help="The name(s) of the script(s). If multiple scripts are given, "
        "then results will be shown for all of them. If --projects is "
        "given, only scripts from within the given project will be shown. "
        "Respects --regex. "
        "NOTE: This option may give unexpected results if --projects is not specified, "
        "since script names are not guaranteed to be unique across all projects!",
    )
    things_group.add_argument(
        "-o",
        "--observers",
        nargs="+",
        metavar="OBSERVER",
        help="Filter for given observer(s). Respects --regex",
    )
    things_group.add_argument(
        "-O",
        "--operators",
        nargs="+",
        metavar="OPERATOR",
        help="Filter for given operator(s). Respects --regex",
    )
    things_group.add_argument(
        "--state",
        help="Filter based on the state of script execution",
        choices=["completed", "in_progress", "aborted"],
    )

    ### Time Group ###
    time_group = parser.add_argument_group(
        title="Time",
        description="Arguments that filter within the time domain. "
        "NOTE: ALL options in this section are with respect to the script "
        "EXECUTION time! Script termination times are not recorded, though you "
        "can look within the logs to see roughly when script termination ocurred",
    )
    time_group.add_argument(
        "-l",
        "--last",
        metavar="DELTA",
        type=float,
        help="Limit to scripts executed within the last DELTA time units. "
        "See --units for details on time unit options",
    )
    time_group.add_argument(
        "-a",
        "--after",
        "--start",
        metavar="DATETIME",
        type=dp.parse,
        help="Limit to scripts executed after this time (note: any reasonable "
        "datetime format will work here). This time is INCLUSIVE. "
        "It DOES NOT respect --buffer!",
    )
    time_group.add_argument(
        "-b",
        "--before",
        "--end",
        metavar="DATETIME",
        type=dp.parse,
        help="Limit to scripts executed before this time "
        "(note: any reasonable datetime format will work here). This time is "
        "INCLUSIVE. It DOES NOT respect --buffer!",
    )

    # TODO: Allow multiple options here
    time_group.add_argument(
        "-t",
        "--times",
        metavar="DATETIME",
        nargs="+",
        type=dp.parse,
        help="Script execution time (note: any reasonable datetime "
        "format will work here). This works in conjunction with --buffer to "
        "find all scripts executed near the given time",
    )
    time_group.add_argument(
        "-B",
        "--buffer",
        type=float,
        default=0.25,
        help="Designates the size of the time window that projects "
        "will be searched for within. For an exact time, use 0 here. "
        "Units are determined by --units. "
        "Note that the default will only be reasonable if the default "
        "unit is used.",
    )
    time_group.add_argument(
        "-u",
        "--unit",
        default="hours",
        # All (reasonable) choices that can be set for relativedelta
        choices=["seconds", "minutes", "hours", "days", "weeks", "months", "years"],
    )

    ### Sorting Group ###
    sorting_group = parser.add_argument_group(
        title="Sorting", description="Arguments specify sorting options"
    )
    sorting_group.add_argument(
        "-S",
        "--sort-by",
        default="datetime",
        # These are simply what I consider a reasonable set of things to filter by
        choices=["id", "obsprocedure", "observer", "operator", "datetime"],
        help="Field to results by",
    )
    sorting_group.add_argument(
        "-d",
        "--direction",
        default="descending",
        choices=["ascending", "descending"],
        help="Direction to sort results",
    )

    ### Output Group ###
    output_group = parser.add_argument_group(
        title="Output", description="Arguments specify output options"
    )
    output_group.add_argument(
        "--output",
        default=".",
        help="Specify the path into which all output files will be written."
        "If the path does not exist, an attempt will be made to create it.",
    )
    output_group.add_argument(
        # TODO: --diff is deprecated
        "--show-diffs",
        "--diff",
        action="store_true",
        help="Show the differences between the scripts for each result",
    )
    output_group.add_argument(
        "--show-logs",
        "--logs",
        # TODO: --logs is deprecated
        action="store_true",
        help="Show the log for each result",
    )
    output_group.add_argument(
        "--save-logs",
        action="store_true",
        help="Save the log for each result to file. Path is relative to --output.",
    )
    output_group.add_argument(
        "--show-scripts",
        action="store_true",
        help="Show the contents of the executed script for each result",
    )
    output_group.add_argument(
        "--save-scripts",
        action="store_true",
        help="Save the script for each result to file. Path is relative to --output.",
    )
    output_group.add_argument(
        "--show-sql",
        action="store_true",
        help="Display every SQL query that is executed during the script. "
        "NOTE: This is primarily intended for use in --interactive mode; "
        "for standard operations simply use --verbose",
    )
    output_group.add_argument(
        "--export-to-git",
        action="store_true",
        help="Export all results to a git repository, with every execution "
        "forming a commit. Execution date is used as commit date. File name "
        "is in the format {PROJECT}.{SCRIPTNAME}.py",
    )

    ### Advanced Group ###
    advanced_group = parser.add_argument_group(
        title="Advanced",
        description="Note that these will take a LONG time. It is "
        "advisable to couple them with a reasonable --limit value. "
        "Note also that none of these are case-sensitive",
    )
    advanced_group.add_argument(
        "-k",
        "--kwargs",
        nargs="+",
        metavar="KEY=VALUE",
        help="Search for one or more keyword=value style statements within observation "
        "scripts. Note that whitespace DOES NOT matter here (though key/value pairs "
        "must be separated by spaces)",
    )
    advanced_group.add_argument(
        "--script-contains",
        nargs="+",
        metavar="STRING",
        help="One or more strings that will be searched for within scripts (case-insensitive)",
    )
    advanced_group.add_argument(
        "--log-contains",
        nargs="+",
        metavar="STRING",
        help="One or more strings that will be searched for within logs (case-insensitive)",
    )
    advanced_group.add_argument(
        "--script-regex",
        nargs="+",
        metavar="REGEX",
        help="One or more MySQL-style regular expression that will be "
        "used to search within scripts",
    )
    advanced_group.add_argument(
        "--log-regex",
        nargs="+",
        metavar="REGEX",
        help="One or more MySQL-style regular expression that will be "
        "used to search within logs",
    )

    args = parser.parse_args()

    if args.exact and args.regex:
        parser.error("--exact cannot be given alongside --regex!")

    if args.kwargs:
        # Parse the keyword-value strings inside of kwargs. If there is
        # a ValueError, consider it a parsing error
        # Replace the user's kwargs with the version we have parsed into a dict
        try:
            args.kwargs = parse_kwargs(args.kwargs)
        except ValueError:
            parser.error(
                "kwargs must be of the format 'keyword=value'; got {}".format(
                    args.kwargs
                )
            )

    ### Additional error checking ###
    buffer_given = args.buffer != parser.get_default("buffer")
    # Ensure that --buffer isn't given without --time
    # if buffer_given and parser.get_default("times") not in args.times:
    #     parser.error("--buffer has no effect if --times is not given!")

    if buffer_given and (
        parser.get_default("last") != args.last
        or parser.get_default("after") != args.after
        or parser.get_default("before") != args.before
    ):
        parser.error(
            "--buffer has no effect on time-related options other than --times!"
        )
    # Ensure that the buffer isn't negative
    if args.buffer < 0:
        parser.error("--buffer value must be greater than 0")
    args.buffer = relativedelta(**{args.unit: args.buffer})

    if args.output != parser.get_default("output") and not (
        args.save_scripts or args.save_logs or args.export_to_git
    ):
        parser.error(
            "--output is meaningless without --save-scripts, --save-logs, or --export-to-git"
        )

    return args


def generateRegexpStatement(keyword, value):
    return r"{keyword}\s*=\s*[\'\"]{value}[\'\"]".format(keyword=keyword, value=value)


def main():
    args = parse_args()

    # Set up logging
    if args.verbose:
        log_level = "DEBUG"
    elif args.log_level:
        log_level = args.log_level

    if not args.verbose:
        # If we are not in verbose mode, then we only output simple errors
        sys.excepthook = excepthook

    # Set our CONSOLE_LOGGER level
    logging.getLogger("turtlecli").setLevel(log_level)
    CONSOLE_LOGGER.setLevel(log_level)
    # Set Django's DB CONSOLE_LOGGER level, too
    if args.show_sql:
        logging.getLogger("django.db.backends").setLevel("DEBUG")

    CONSOLE_LOGGER.debug("Done parsing arguments!")
    FILE_LOGGER.info("argv: %s", " ".join([shlex.quote(arg) for arg in sys.argv]))

    description_parts = []
    results = History.objects.all()
    if args.project_names:
        plural = "s" if args.project_names and len(args.project_names) > 1 else ""
        description_parts.append(
            "for project name{} {}".format(
                plural,
                iterable_to_fancy_string(args.project_names, quote=True, word="or"),
            )
        )
        results &= filterByProject(
            args.project_names, fuzzy=not args.exact, regex=args.regex
        )

    if args.script_names:
        plural = "s" if args.script_names and len(args.script_names) > 1 else ""
        description_parts.append(
            "for script name{} {}".format(
                plural,
                iterable_to_fancy_string(args.script_names, quote=True, word="or"),
            )
        )
        results &= filterByScript(args.script_names, regex=args.regex)

    if args.observers:
        plural = "s" if args.observers and len(args.observers) > 1 else ""
        description_parts.append(
            "by observer name{} {}".format(
                plural, iterable_to_fancy_string(args.observers, quote=True, word="or")
            )
        )
        results &= filterByObserver(
            args.observers, fuzzy=not args.exact, regex=args.regex
        )

    if args.operators:
        plural = "s" if args.operators and len(args.operators) > 1 else ""
        description_parts.append(
            "with operator name{} {}".format(
                plural, iterable_to_fancy_string(args.operators, quote=True, word="or")
            )
        )
        results &= filterByOperator(
            args.operators, fuzzy=not args.exact, regex=args.regex
        )

    if args.state:
        # Argument choices are shortened forms of the possible field values
        state = "obs_{}".format(args.state)
        description_parts.append("with state {}".format(state))
        results &= History.objects.filter(executed_state=state)

    if args.times:
        time_bits = History.objects.none()
        stubs = []
        for time in args.times:
            start = time - args.buffer
            end = time + args.buffer
            stubs.append(
                "{} {} of {} (i.e. between {} and {})".format(
                    getattr(args.buffer, args.unit), args.unit, time, start, end
                )
            )
            time_bits |= filterByRange(start, end)

        description_parts.append(
            "that occurred within {}".format(
                iterable_to_fancy_string(stubs, quote=False, word="or")
            )
        )
        results &= time_bits

    if args.last:
        now = timezone.datetime.now()
        delta_start = now - relativedelta(**{args.unit: args.last})
        description_parts.append(
            "that occurred within the last {} {} (i.e. between {} and {})".format(
                args.last,
                args.unit,
                format_date_time(delta_start),
                format_date_time(now),
            )
        )
        results &= filterByRange(delta_start, now)

    if args.after or args.before:
        if args.after and args.before:
            description_parts.append(
                "executed after {} but before {}".format(args.after, args.before)
            )
        elif args.after or args.before:
            if args.after:
                description_parts.append("executed after {}".format(args.after))
            elif args.after:
                description_parts.append("executed before {}".format(args.before))
        results &= filterByRange(args.after, args.before)

    # Handle script contains
    if args.script_contains:
        description_parts.append(
            "with script containing: {}".format(args.script_contains)
        )
        query = Q()
        for contains in args.script_contains:
            query |= Q(executed_script__icontains=contains)

        results &= History.objects.filter(query)

    # Handle log contains
    if args.log_contains:
        description_parts.append("with log containing: {}".format(args.log_contains))
        query = Q()
        for contains in args.log_contains:
            query |= Q(log__icontains=contains)

        results &= History.objects.filter(query)

    # Handle script regex
    if args.script_regex:
        description_parts.append("with script regex: {}".format(args.script_regex))
        query = Q()
        for regex in args.script_regex:
            query |= Q(executed_script__iregex=regex)

        results &= History.objects.filter(query)

    # Handle log regex
    if args.log_regex:
        description_parts.append("with log regex: {}".format(args.log_regex))
        query = Q()
        for regex in args.log_regex:
            query |= Q(log__iregex=regex)

        results &= History.objects.filter(query)

    # Handle kwargs
    if args.kwargs:
        description_parts.append("with config kwargs: {}".format(args.kwargs))
        query = Q()
        for keyword, value in args.kwargs.items():
            # TODO: How to also handle &= ?
            query |= Q(executed_script__iregex=generateRegexpStatement(keyword, value))

        results &= History.objects.filter(query)

    # TODO: Consider testing results only once?
    # The following operations only make sense if results have been found
    if results.exists() and args.sort_by:
        description_parts.append(
            "ordered by {} ({})".format(args.sort_by, args.direction)
        )
        field = "{}{}".format(
            "-" if args.direction == "descending" else "", args.sort_by
        )
        results = results.order_by(field)

    all_results = results
    all_results_count = all_results.count()
    # This must occur after ordering!
    # Don't limit if limit is set to 0
    if results.exists() and args.limit != 0:
        results = results[: args.limit]

    # if args.group_by:
    #     results = results.group_by(args.group_by)

    # THIS IS WHERE THE QUERY IS ACTUALLY EXECUTED
    df = results.to_dataframe(fieldnames=DEFAULT_HISTORY_TABLE_FIELDNAMES)

    # First 2 queries are not relevant to us
    queries = connections["default"].queries[2:]
    # We only show this if we are logging DEBUG messages, _and_ we are not
    # already logging all SQL queries (that would be redundant)
    if CONSOLE_LOGGER.level == logging.DEBUG and not args.show_sql and queries:
        CONSOLE_LOGGER.debug("Executed query:\n" + formatSql(queries[-1]["sql"]))

    # Sum up query time from all relevant queries
    query_time = sum(float(query["time"]) for query in queries)

    num_results = len(df)
    if args.limit != 0 and args.limit <= num_results:
        limit_str = " due to `limit` of {}; for all {} results re-run with --limit 0".format(
            num_results, all_results_count
        )
    else:
        limit_str = ""
    plural = "s" if num_results > 1 else ""
    print(
        "Found {} result{} in {:.3f} seconds{}".format(
            num_results, plural, query_time, limit_str
        )
    )
    FILE_LOGGER.info(
        "Found {} result{} in {:.3f} seconds".format(num_results, plural, query_time)
    )
    if not df.empty:
        print("Displaying scripts {}".format(", ".join(description_parts)))
        print(genHistoryTable(df, verbose=args.verbose or log_level == "DEBUG"))
    else:
        print("No scripts found {}".format(", ".join(description_parts)))
        if args.exact:
            CONSOLE_LOGGER.info("Try again without --exact to perform fuzzy searches")
        if not args.regex:
            CONSOLE_LOGGER.info(
                "Try again with --regex to treat given arguments as regular expressions"
            )
    print("")

    if args.output and args.output != ".":
        os.makedirs(args.output, exist_ok=True)
        CONSOLE_LOGGER.debug("Created directory %s", args.output)

    if args.show_scripts or args.save_scripts:
        report = ScriptReport(results, args.interactive)
        if args.show_scripts:
            report.print_report()

        if args.save_scripts and not args.export_to_git:
            report.save_report(args.output)

    if args.show_diffs:
        if set(results.values_list("obsprocedure__name", flat=True)):
            CONSOLE_LOGGER.warning(
                "Multiple script names detected; diffs may not make much sense!"
            )
        DiffReport(results, args.interactive).print_report()

    if args.show_logs or args.save_logs:
        report = LogReport(results, args.interactive)
        if args.show_logs:
            report.print_report()

        if args.save_logs and not args.export_to_git:
            report.save_report(args.output)

    if args.export_to_git:
        gitify(results, args.output, include_log=args.save_logs)

    # If the user has requested an interactive session, enter it now.
    # However, don't bother trying if we are already being run via IPython,
    # because it won't work
    if args.interactive and not in_ipython():
        from tortoise.models import ObsProcedure, Observer, Operator, ObsProjectRef

        CONSOLE_LOGGER.info("")
        r = results
        ar = all_results
        CONSOLE_LOGGER.info("Entering interactive mode")
        CONSOLE_LOGGER.info("Results are available as:")
        CONSOLE_LOGGER.info(
            "  * A Django QuerySet (see: "
            "https://docs.djangoproject.com/en/2.2/ref/models/querysets), "
            "in the `r` (limited results) and `ar` (all results) variables. \n"
            "    This contains History objects; available fields are:"
        )
        field_str = "\n".join(
            [
                "    * {}: {}".format(field.name, field.help_text)
                for field in History._meta.fields
            ]
        )
        CONSOLE_LOGGER.info(field_str)
        CONSOLE_LOGGER.info(
            "  * As a Pandas DataFrame (see: "
            "https://pandas.pydata.org/pandas-docs/stable/api.html#dataframe) "
            "in the `df` variable."
        )
        IPython.embed(display_banner=False, exit_msg="Hope you had fun!")
        CONSOLE_LOGGER.debug("Exiting interactive mode")


def excepthook(type, value, traceback):
    print(value, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

# TODO: Handle &= operator for queries. Some sort of option will be needed
# TODO: Finish refactoring of codebase
# TODO: Consider subcommands for things like "Show me details about a specific ObsProcedure" -- this is history-centric so far
# TODO: Add --interactive-reports
# TODO: Unit tests!
# TODO: Sphinx documentation -- how best to document each argument (with examples)?
# TODO: Doctests -- this seems like the perfect application
