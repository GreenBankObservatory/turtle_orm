import dateutil.parser as dp

from turtlecli.utils import formatHistoryTable

from tortoise.models import History


def getByTime(args):
    print("Scripts executed within {} minutes += {}:".format(args.buffer, args.time))

    histories = History.objects.filterByTime(args.time, args.buffer)
    print(formatHistoryTable(histories))


def add_parser(subparsers):
    parser = subparsers.add_parser('getbytime', help='getByTime help')
    parser.add_argument('time',
                        type=dp.parse,
                        help='The time of the thing')
    parser.add_argument('-b', '--buffer',
                        type=int,
                        default=15,
                        help='Designates the size of the window, '
                             'in minutes, that projects will be '
                             'searched for within')
    parser.set_defaults(func=getByTime)

    return parser
