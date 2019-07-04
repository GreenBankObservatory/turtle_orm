# -*- coding: utf-8 -*-
import argparse
import pickle

import dateutil.parser as dp
from tabulate import tabulate

import django

django.setup()
from django.db.models.functions import Cast
from django.db.models import FloatField, F, Count, Min, Max, Q

from tortoise.models import Observer, Operator

μs_in_a_day = 86_400_000_000

# Example usage:
# $ time DJANGO_SETTINGS_MODULE=turtle_orm.settings python3 turtlecli/observer_operator_report.py  \
#   --min-last 2018  --min-script-exec 1000


def do_stats(
    obs_or_ops,
    sort_by="-total_runs",
    min_script_executions=None,
    min_last_obs_date=None,
):
    # Prefetch tables that will need to be joined for every observer
    obs_or_ops = obs_or_ops.prefetch_related("history__obsprocedure__obsprojectref")

    # Create the annotations that we will need for our metrics
    obs_or_ops = obs_or_ops.annotate(
        # Count number if associated script executions for each observer
        total_runs=Count("history"),
        # Count number if these executions that completed successfully
        runs_completed=Count(
            "history", filter=Q(history__executed_state="obs_completed")
        ),
        # Count number of unique procedures
        unique_scripts_run=Count("history__obsprocedure", distinct=True),
        # Count number of unique projects
        unique_projects_run=Count(
            "history__obsprocedure__obsprojectref", distinct=True
        ),
        # Date of first execution
        first_run=Min("history__datetime"),
        # Date of last execution
        last_run=Max("history__datetime"),
        # Get the difference then convert to days
        days=(F("last_run") - F("first_run")) / μs_in_a_day,
        # We need to Cast here to force both of these to be Floats
        runs_per_day=(
            Cast(F("total_runs"), FloatField()) / Cast(F("days"), FloatField())
        ),
    ).order_by(sort_by)

    if min_script_executions:
        obs_or_ops = obs_or_ops.filter(total_runs__gte=min_script_executions)

    if min_last_obs_date:
        obs_or_ops = obs_or_ops.filter(last_run__gte=min_last_obs_date)

    values = obs_or_ops.values(
        "name",
        "total_runs",
        "runs_completed",
        "unique_scripts_run",
        "unique_projects_run",
        "first_run",
        "last_run",
        "days",
        "runs_per_day",
    )

    table = tabulate(values, headers="keys", tablefmt="fancy_grid")
    # num_queries = len(connections["default"].queries)
    # print("{} queries".format(num_queries))
    return table, obs_or_ops


def get_ops_or_obs(model_class, names):
    if names is None:
        ops_or_obs = model_class.objects.all()
    else:
        ops_or_obs = model_class.objects.filter(name__in=names)
        if len(names) != len(ops_or_obs):
            not_found = set(names).difference(ops_or_obs.values_list("name", flat=True))
            raise ValueError(
                "Given {} names not found: {}".format(
                    model_class._meta.verbose_name, not_found
                )
            )
    return ops_or_obs


def get_observers(observer_names=None):
    return get_ops_or_obs(Observer, observer_names)


def get_operators(operator_names=None):
    return get_ops_or_obs(Operator, operator_names)


def write_pickle(queryset, filename="results.pkl"):
    with open(filename, "w") as file:
        pickle.dump(queryset, file)
        print("Wrote {}\n".format(filename))


def write_table(table, filename="results.txt"):
    with open(filename, "w") as file:
        file.write(table)
        print("Wrote {}\n".format(filename))


def write_output(
    obs_or_ops,
    sort_by="-total_runs",
    min_script_executions=None,
    min_last_obs_date=None,
    do_write_table=False,
    do_write_pickle=False,
):
    table, queryset = do_stats(
        obs_or_ops,
        sort_by,
        min_script_executions=min_script_executions,
        min_last_obs_date=min_last_obs_date,
    )
    print(table)
    if do_write_table:
        filename = "{}_results.txt".format(obs_or_ops.model.__name__.lower())
        write_table(table, filename)
    if do_write_pickle:
        filename = "{}_results.pkl".format(queryset.model.__name__.lower())
        write_pickle(queryset, filename)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--observers",
        nargs="+",
        metavar="OBSERVER",
        help="Name(s) of observers that should appear in the report",
    )
    parser.add_argument(
        "-O",
        "--operators",
        nargs="+",
        metavar="OPERATOR",
        help="Name(s) of operators that should appear in the report",
    )
    parser.add_argument(
        "--min-script-executions",
        type=int,
        help="The minimum number (inclusive) of script executions "
        "required to appear in the report",
    )
    parser.add_argument(
        "--min-last-obs-date",
        type=dp.parse,
        help="Script executions prior to the given date (inclusive) will be ignored",
    )
    parser.add_argument(
        "--write-table",
        action="store_true",
        help="If given, write tables to text files",
    )
    parser.add_argument(
        "--write-pickle",
        action="store_true",
        help="If given, write results to .pkl files (useful debugging for giant queries)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    write_output(
        get_observers(args.observers),
        min_script_executions=args.min_script_executions,
        min_last_obs_date=args.min_last_obs_date,
        do_write_table=args.write_table,
        do_write_pickle=args.write_pickle,
    )
    print()
    write_output(
        get_operators(args.operators),
        min_script_executions=args.min_script_executions,
        min_last_obs_date=args.min_last_obs_date,
        do_write_table=args.write_table,
        do_write_pickle=args.write_pickle,
    )


if __name__ == "__main__":
    main()
