#! /usr/bin/env python3

import argparse
from tabulate import tabulate

import django
django.setup()

import dateutil.parser as dp


from tortoise.models import ObsProcedure, History

"""docstring"""

def formatTable(table, fieldnames, headers):
    return tabulate(
        table.to_dataframe(fieldnames=fieldnames),
        headers=headers)

def formatHistoryTable(histories):
    headers = ('Script Name',
               'Executed',
               'Observer',
               'Operator')
    fieldnames = ('obsprocedure__name',
                  'datetime',
                  'observer__name',
                  'operator__name')

    return formatTable(histories, fieldnames, headers)

def getByTime(args):
    histories = History.objects.filterByTime(args.time, args.buffer)
    print(formatHistoryTable(histories))


def getByProject(args):
    explanation = "Results for project {}".format(args.name)
    if args.start and args.end:
        explanation += ", executed after {} but before {}".format(args.start, args.end)
    elif args.start or args.end:
        if args.start:
            explanation += ", executed after {}".format(args.start)
        elif args.start:
            explanation += ", executed before {}".format(args.end)
        else:
            raise ValueError("Hmmmm....")

    print("{}:".format(explanation))
    histories = History.objects.filterByProject(args.name, args.start, args.end)
    print(formatHistoryTable(histories))


def parse_args():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        title='subcommands',
        # description='valid subcommands',
        # help='sub-command help'
    )
    # Required due to argparse bug: https://stackoverflow.com/a/18283730/1883424
    subparsers.required = True
    subparsers.dest = 'subcommand'

    parser_getbytime = subparsers.add_parser('getbytime', help='getByTime help')
    parser_getbytime.add_argument('time', help='The time of the thing')
    parser_getbytime.add_argument('-b', '--buffer',
                                  type=int,
                                  default=15,
                                  help='Designates the size of the window, '
                                       'in minutes, that projects will be '
                                       'searched for within')
    parser_getbytime.set_defaults(func=getByTime)


    parser_getbyproject = subparsers.add_parser('getbyproject', help='getByProject help')
    parser_getbyproject.add_argument('name', help='The name of the project')
    parser_getbyproject.add_argument('-s', '--start',
                                     type=dp.parse,
                                     help='Limit to scripts executed after this time')
    parser_getbyproject.add_argument('-e', '--end',
                                     type=dp.parse,
                                     help='Limit to scripts executed before this time')
    parser_getbyproject.set_defaults(func=getByProject)
    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
