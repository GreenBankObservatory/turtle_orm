"""QuerySet Filters for History model"""

from datetime import timedelta
import os
from glob import glob
import re
import logging

from astropy.io import fits
import dateutil.parser as dp

from tortoise.models import History

CONSOLE_LOGGER = logging.getLogger("{}_user".format(__name__))


PROJECT_NAME_REGEX = re.compile(
    r"(?P<prefix>(?P<type>[AT])?\w*)(?P<year>\d{2,4})(?P<semester>[ABC])[_\s\-]?(?P<code>\d{,10})[_\s\-]?(?P<session>\d+)?",
    re.IGNORECASE,
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
    despite obviously be AGBT19A_453
    """
    results = History.objects.none()
    session_filter = None
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

        if fuzzy and not regex:
            CONSOLE_LOGGER.debug(
                "Performing a regex search of project names due to fuzzy=True"
            )
            match = PROJECT_NAME_REGEX.search(project_name)
            if match:
                obs_type = match.groupdict().get("type", None)
                session = match.groupdict().get("session", None)
                if session:
                    if not obs_type or obs_type == "A":
                        # science_data_path =
                        scanlog_paths = glob(
                            "/home/archive/science-data/**/AGBT{year}{semester}_{code}_{session}/ScanLog.fits".format(
                                **match.groupdict()
                            )
                        )
                    else:
                        scanlog_paths = glob(
                            "/home/archive/test-data/**/TGBT{year}{semester}_{code}_{session}/ScanLog.fits".format(
                                **match.groupdict()
                            )
                        )
                    try:
                        if len(scanlog_paths) != 1:
                            raise ValueError("aw man")
                        scanlog_path = scanlog_paths[0]
                        scanlog = fits.open(scanlog_path)
                        execution_times = sorted(
                            set(dp.parse(i[0]) for i in scanlog[1].data)
                        )
                    except (FileNotFoundError, ValueError, KeyError):
                        CONSOLE_LOGGER.info(
                            "Given project name '{project_name}' looks "
                            "like it includes a session identifier. For whatever reason, "
                            "Turtle does not store any session information, so we are "
                            "looking to {scanlog_path} for more. However, it doesn't exist or couldn't be read, so "
                            "we're simply ignoring the session identifier altogether".format(
                                project_name=project_name, scanlog_path=scanlog_path
                            )
                        )
                    else:
                        session_filter = History.objects.none()
                        if len(execution_times) < 100:
                            for execution_time in execution_times:
                                # Put a little cushion in here to handle slight inconsistencies between turtle and M&C
                                session_filter |= filterByRange(
                                    execution_time - timedelta(minutes=15),
                                    execution_time + timedelta(minutes=15),
                                )
                        else:
                            CONSOLE_LOGGER.info(
                                "Too many scans to perform discrete search; instead search for scripts "
                                "executed between first and last scan ({start} to {end})".format(
                                    execution_times[0], execution_times[-1]
                                )
                            )
                            session_filter |= filterByRange(
                                execution_times[0] - timedelta(minutes=15),
                                execution_time[-1] + timedelta(minutes=15),
                            )
                        CONSOLE_LOGGER.info(
                            "Given project name '{project_name}' looks "
                            "like it includes a session identifier. For whatever reason, "
                            "Turtle does not store any session information, so we are "
                            "looking to {scanlog_path} for more. The first scan was executed at "
                            "{start}, and the last was executed at {end}, so we're "
                            "using those as the time boundaries for session {session}".format(
                                project_name=project_name,
                                start=execution_times[0],
                                end=execution_times[-1],
                                scanlog_path=scanlog_path,
                                session=session,
                            )
                        )
                CONSOLE_LOGGER.debug(
                    "Given project name '{project_name}' matches regex '{PROJECT_NAME_REGEX}', "
                    "so it is being transformed into a fuzzy query".format(
                        project_name=project_name, PROJECT_NAME_REGEX=PROJECT_NAME_REGEX
                    )
                )
                the_regex = "{prefix}{year}.*{semester}.*{code}".format(
                    **match.groupdict()
                )
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

    if session_filter is not None:
        results &= session_filter
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
                    **{"{accessor}__iregex".format(accessor=accessor): value}
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
