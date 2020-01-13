"""Misc. utilities"""

import logging
import subprocess

from django.db import connection

from colorama import Fore
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import MySqlLexer
from tabulate import tabulate
import sqlparse


CONSOLE_LOGGER = logging.getLogger(__name__)


DEFAULT_HISTORY_TABLE_HEADERS = (
    "Executed",
    "Project Name",
    "Script Name",
    "Observer",
    "Operator",
    "State",
)

DEFAULT_HISTORY_TABLE_FIELDNAMES = (
    "datetime",
    "obsprocedure__obsprojectref__name",
    "obsprocedure__name",
    "observer__name",
    "operator__name",
    "executed_state",
)


def formatTable(table, headers):
    return tabulate(table, headers=headers)


def genHistoryTable(history_df, headers=None, verbose=False, timezone=None):
    if not headers:
        headers = DEFAULT_HISTORY_TABLE_HEADERS

    # Include index as a column!
    columns = [history_df.index.name, *history_df.columns]

    if len(headers) != len(columns):
        raise ValueError(
            "Number of headers ({}) must be equal to number of columns ({})!".format(
                len(headers), len(columns)
            )
        )
    if verbose:
        headers = [
            "{}\n({})".format(header, field) for header, field in zip(headers, columns)
        ]

    if timezone:
        headers = ["{} ({})".format(headers[0], timezone), *headers[1:]]

    return formatTable(history_df, headers)


def in_ipython():
    """Determine whether this script is being run via IPython; return bool"""

    try:
        __IPYTHON__
    except NameError:
        # CONSOLE_LOGGER.debug("Not in IPython")
        return False
    else:
        # CONSOLE_LOGGER.debug("In IPython")
        return True


# From: https://chezsoi.org/lucas/blog/colored-diff-output-with-python.html
def color_diff(diff):
    for line in diff:
        if line.startswith("+"):
            yield Fore.GREEN + line + Fore.RESET
        elif line.startswith("-"):
            yield Fore.RED + line + Fore.RESET
        elif line.startswith("^"):
            yield Fore.BLUE + line + Fore.RESET
        else:
            yield line


def gen2(l):
    """Given an iterable, generate tuples of every two elements

    In : list(gen2([1,2,3]))
    Out: [(1, 2), (2, 3)]
    """

    for i in range(len(l) - 1):
        yield (l[i], l[i + 1])


def formatSql(sql, indent=False):
    """Format and reindent the given `sql` and return it.

    Optionally indent every line of the SQL before returning it."""

    formatted = sqlparse.format(sql, reindent=True, keyword_case="upper")
    if indent:
        lines = []
        for line in formatted.split("\n"):
            lines.append("    {}".format(line))
        formatted = "\n".join(lines)

    # Hack to avoid Session being treated as a SQL keyword (converted to SESSION)
    formatted = formatted.replace("SESSION", "Session")
    return highlight(formatted, MySqlLexer(), TerminalFormatter())


def timeOfLastQuery():
    return connection.queries[-1]["time"]


class DjangoSqlFormatter(logging.Formatter):
    def format(self, record):
        return "\n{}".format(formatSql(record.args[1]))


def get_console_width():
    _, console_width_str = subprocess.check_output(["stty", "size"]).decode().split()
    return int(console_width_str)


def format_date_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def iterable_to_fancy_string(iterable, quote=False, word="and"):
    iterable_length = len(iterable)
    if quote:
        stringifier = lambda x: repr(str(x))
    else:
        stringifier = str

    if iterable_length == 0:
        return ""

    if iterable_length == 1:
        return stringifier(list(iterable)[0])

    if iterable_length == 2:
        return " {} ".format(word).join([stringifier(item) for item in iterable])

    l = [stringifier(item) for item in iterable]
    return "{}, {} {}".format(", ".join(l[:-1]), word, l[-1])
