import dateutil.parser as dp

from turtlecli.utils import formatHistoryTable
from tortoise.models import History


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


def add_parser(subparsers):
    parser = subparsers.add_parser('getbyproject', help='getByProject help')

    parser.add_argument(
        'name',
        help='The name of the project'
    )
    parser.add_argument(
        '-l', '--last',
        metavar="HOURS",
        nargs='?',
        type=float,
        help='Limit to scripts executed within the last HOURS hours'
    )
    parser.add_argument(
        '-s', '--start',
        type=dp.parse,
        help='Limit to scripts executed after this time'
    )
    parser.add_argument(
        '-e', '--end',
        type=dp.parse,
        help='Limit to scripts executed before this time'
    )

    parser.set_defaults(func=getByProject)

    # args = parser.parse_args()

    # if (args.start or args.end) and args.last:
    #     parser.error("If specifying --last, neither --start nor --end may be specified!")
