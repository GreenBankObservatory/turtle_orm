from tortoise.models import History


def filterByTime(dt, buffer):
    return History.objects.filter(
        datetime__gte=dt - buffer,
        datetime__lte=dt + buffer
    )

def filterByRange(start, end):
    results = History.objects.all()
    if start:
        results &= History.objects.filter(datetime__gte=start)
    if end:
        results &= History.objects.filter(datetime__lte=end)
    return results

def filterByProject(project_names):
    return History.objects.filter(obsprocedure__obsprojectref__name__in=project_names)

def filterByScript(script_names):
    return History.objects.filter(obsprocedure__name__in=script_names)
