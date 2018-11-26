import logging

from django.db import connection

from pygments import highlight
from pygments.lexers import MySqlLexer
from pygments.formatters import TerminalFormatter
from colorama import Fore
import sqlparse
from tabulate import tabulate


logger = logging.getLogger(__name__)


DEFAULT_HISTORY_TABLE_HEADERS = (
    "Project Name",
    "Script Name",
    # TODO: Verify that this is indeed EST
    # TODO: DST??
    "Executed (EST)",
    "Observer",
    "Operator",
    "State",
)

DEFAULT_HISTORY_TABLE_FIELDNAMES = (
    "obsprocedure__obsprojectref__name",
    "obsprocedure__name",
    "datetime",
    "observer__name",
    "operator__name",
    "executed_state",
)


def formatTable(table, headers):
    return tabulate(table, headers=headers)


def genHistoryTable(history_df, headers=None, verbose=False):
    if not headers:
        headers = DEFAULT_HISTORY_TABLE_HEADERS

    if len(headers) != len(history_df.columns):
        raise ValueError("Number of headers must be equal to number of columns!")
    if verbose:
        headers = ["{}\n({})".format(header, field) for header, field in zip(headers, history_df.columns)]
    return formatTable(history_df, headers)


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

    logger.debug("Formatted %s into %s", sql, formatted)
    # Hack to avoid Session being treated as a SQL keyword (converted to SESSION)
    formatted = formatted.replace("SESSION", "Session")
    return highlight(formatted, MySqlLexer(), TerminalFormatter())


def timeOfLastQuery():
    return connection.queries[-1]["time"]


class DjangoSqlFormatter(logging.Formatter):
    def format(self, record):
        return "\n{}".format(formatSql(record.args[1]))


# class DjangoSqlFilter(logging.Filter):
#     def filter(self, record):
#         return "History" in record.args[1]
