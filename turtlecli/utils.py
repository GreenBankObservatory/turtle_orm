from tabulate import tabulate

from tortoise.models import ObsProcedure, History

DEFAULT_HISTORY_TABLE_HEADERS = (
    'Project Name',
    'Script Name',
    # TODO: Verify that this is indeed EST
    # TODO: DST??
    'Executed (EST)',
    'Observer',
    'Operator',
    'State'
)

DEFAULT_HISTORY_TABLE_FIELDNAMES = (
    'obsprocedure__obsprojectref__name',
    'obsprocedure__name',
    'datetime',
    'observer__name',
    'operator__name',
    'executed_state'
)

def formatTable(table, fieldnames, headers):
    return tabulate(
        table.to_dataframe(fieldnames=fieldnames),
        headers=headers)

def formatHistoryTable(histories, headers=None, fieldnames=None):
    if not headers:
        headers = DEFAULT_HISTORY_TABLE_HEADERS

    if not fieldnames:
        fieldnames = DEFAULT_HISTORY_TABLE_FIELDNAMES
    
    if len(headers) != len(fieldnames):
        raise ValueError("headers and fieldnames must be the same length!")

    return formatTable(histories, fieldnames, headers)
