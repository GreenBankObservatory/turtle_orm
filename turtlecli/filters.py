"""QuerySet Filters for History model"""

import re
import logging

from tortoise.models import History

CONSOLE_LOGGER = logging.getLogger("{}_user".format(__name__))


PROJECT_NAME_REGEX = re.compile(
    r"(?P<year>\d{2,4})(?P<semester>[ABC])[_\s\-]?(?P<code>\d{,10})", re.IGNORECASE
)


def filterByRange(start, end):
    """Return all History objects executed between start and end, inclusive"""

    results = History.objects.all()
    if start:
        results &= History.objects.filter(datetime__gte=start)
    if end:
        results &= History.objects.filter(datetime__lte=end)
    return results


def filterByProject(project_names, fuzzy=False, regex=False):
    """Look for the given project names in History

    There is some added value to the standard filterByValues here: if fuzzy
    is given, then a regex is used to attempt to parse common project names
    given in the "standard" format, then reconstruct them into _another_
    regex. This new regex is actually used in the query. The idea here is to
    handle silly stuff like GBT19A453 not working in the standard/exact search,
    despite obviously beinv AGBT19A_453
    """
    results = History.objects.none()
    for project_name in project_names:
        # If --regex given, do a regex search
        if regex:
            CONSOLE_LOGGER.debug(
                "Treating {project_name} as a regular expression due to presence "
                "of regex=True".format(project_name=project_name)
            )
            results |= History.objects.filter(
                obsprocedure__obsprojectref__name__iregex=project_name
            )
        # Otherwise do an exact, case-insensitive string search
        else:
            CONSOLE_LOGGER.debug(
                "Search for exact match of {project_name}".format(
                    project_name=project_name
                )
            )
            results |= History.objects.filter(
                obsprocedure__obsprojectref__name__iexact=project_name
            )

        if fuzzy:
            CONSOLE_LOGGER.debug(
                "Performing a regex search of project names due to fuzzy=True"
            )
            match = PROJECT_NAME_REGEX.match(project_name)
            CONSOLE_LOGGER.debug(
                "Given project name '{project_name}' matches regex '{PROJECT_NAME_REGEX}', "
                "so it is being transformed into a fuzzy query".format(
                    project_name=project_name, PROJECT_NAME_REGEX=PROJECT_NAME_REGEX
                )
            )
            if match:
                the_regex = "{year}.*{semester}.*{code}".format(**match.groupdict())
                CONSOLE_LOGGER.debug(
                    "'{project_name}' matches regex '{PROJECT_NAME_REGEX}', "
                    "so it is being transformed into a fuzzy query: '{the_regex}'".format(
                        project_name=project_name,
                        PROJECT_NAME_REGEX=PROJECT_NAME_REGEX,
                        the_regex=the_regex,
                    )
                )
                results |= History.objects.filter(
                    obsprocedure__obsprojectref__name__iregex=the_regex
                )
            else:
                CONSOLE_LOGGER.debug(
                    "No match found of '{project_name}' with regex '{PROJECT_NAME_REGEX}'".format(
                        project_name=project_name, PROJECT_NAME_REGEX=PROJECT_NAME_REGEX
                    )
                )

    return results


def filterByScript(script_names, regex=False):
    results = History.objects.none()
    if regex:
        CONSOLE_LOGGER.debug(
            "Treating given script names as regular expressions due to presence of regex=True"
        )
        for script_name in script_names:
            results |= History.objects.filter(obsprocedure__name__iregex=script_name)
    else:
        CONSOLE_LOGGER.debug(
            "Searching for exact, case-insensitive matches of script names"
        )
        for script_name in script_names:
            results |= History.objects.filter(obsprocedure__name__iexact=script_names)
    return results


def filterByValues(accessor, values, fuzzy=False, regex=False):
    if fuzzy or regex:
        if fuzzy:
            CONSOLE_LOGGER.debug(
                "Searching for case-insensitive substring matches of given '{accessor}' values".format(
                    accessor=accessor
                )
            )
        if regex:
            CONSOLE_LOGGER.debug(
                "Treating given '{accessor}' values as case-insensitive regular expressions".format(
                    accessor=accessor
                )
            )
        results = History.objects.none()
        for value in values:
            if fuzzy:
                results |= History.objects.filter(
                    **{"{accessor}__icontains".format(accessor=accessor): value}
                )
            if regex:
                results |= History.objects.filter(
                    **{"{accessor}__regex".format(accessor=accessor): value}
                )
    else:
        CONSOLE_LOGGER.debug(
            "Searching for exact, case-insensitive matches of given '{accessor}' values: {values}".format(
                accessor=accessor, values=values
            )
        )
        for value in values:
            results |= History.objects.filter(
                **{"{accessor}__iexact".format(accessor=accessor): values}
            )

    return results


def filterByObserver(observer_names, fuzzy=False, regex=False):
    return filterByValues("observer__name", observer_names, fuzzy, regex)


def filterByOperator(operator_names, fuzzy=False, regex=False):
    return filterByValues("operator__name", operator_names, fuzzy, regex)
