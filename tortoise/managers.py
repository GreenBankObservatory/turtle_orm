import logging

from django.db import models
from django.utils import timezone

from django_pandas.managers import DataFrameManager

logger = logging.getLogger(__name__)


class HistoryManager(DataFrameManager):
    def filterByProject(self, name, start=None, end=None):
        """Given an ObsProjectRef name, return all matching objects"""

        results = self.filter(obsprocedure__obsprojectref__name=name)
        if start:
            results &= self.filter(datetime__gte=start)
        if end:
            results &= self.filter(datetime__lte=end)
        return results
            

    def filterByTime(self, dt, buffer=15):
        """Given a datetime, return all nearby objects

        If buffer is given, it designates (in minutes) the size of the window
        that is searched (+- the given number of minute)"""

        buffer_delta = timezone.timedelta(minutes=buffer)
        return self.filter(datetime__gte=dt - buffer_delta,
                           datetime__lte=dt + buffer_delta)

    # def filterByTimeStr(self, dt_str, *args, **kwargs):
        
    #     return self.filterByTime(dt)
