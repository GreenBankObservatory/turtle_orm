# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.

import logging

from django.db import models

from tortoise.managers import HistoryManager


logger = logging.getLogger(__name__)


class Observer(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=96)

    class Meta:
        managed = False
        db_table = 'Observer'

    def __str__(self):
        return "Observer {}".format(self.name)


class Operator(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=96)

    class Meta:
        managed = False
        db_table = 'Operator'

    def __str__(self):
        return "Operator {}".format(self.name)


class History(models.Model):
    id = models.BigAutoField(primary_key=True)
    obsprocedure = models.ForeignKey('ObsProcedure', on_delete='PROTECT', verbose_name='Procedure')
    observer = models.ForeignKey('Observer', on_delete='PROTECT')
    operator = models.ForeignKey('Operator', on_delete='PROTECT')
    datetime = models.DateTimeField()
    version = models.CharField(max_length=16)
    executed_script = models.TextField()
    executed_state = models.CharField(max_length=14)
    log = models.TextField()

    objects = HistoryManager()

    class Meta:
        managed = False
        db_table = 'History'

    def __str__(self):
        return ("History {} at {}"
                .format(self.id, self.datetime))


class ObsProjectRef(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=96)
    primary_observer = models.ForeignKey('Observer', on_delete='PROTECT', db_column='primary_observer')
    session = models.CharField(max_length=16)

    class Meta:
        managed = False
        db_table = 'ObsProjectRef'

    def __str__(self):
        # TODO: Better way to handle this (without changing the DB)?
        try:
            observer = self.primary_observer
        except Observer.DoesNotExist:
            logger.warning("No Observer exists with ID %s", self.primary_observer_id)
            observer = None

        return ("ObsProjectRef name: {}, observer: {}, session: {}"
                .format(self.name, observer, self.session))


class ObsProcedure(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=96)
    session = models.CharField(max_length=16)
    script = models.TextField()
    obsprojectref = models.ForeignKey('ObsProjectRef', on_delete='PROTECT')
    operator = models.ForeignKey('Operator', on_delete='PROTECT')
    observer = models.ForeignKey('Observer', on_delete='PROTECT')
    state = models.CharField(max_length=13)
    status = models.CharField(max_length=7)
    last_modified = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'ObsProcedure'

    def __str__(self):
        return ("ObsProcedure name: {}, session: {}, state: {}, status: {}"
                .format(self.name, self.session, self.state, self.status))

    def full_name(self):
        escaped_name = self.name.replace("/", "\/")
        return "{}/{}".format(self.obsprojectref.name, escaped_name)


class Queue(models.Model):
    id = models.BigAutoField(primary_key=True)
    obsprocedure = models.ForeignKey('ObsProcedure', on_delete='PROTECT')
    # prev = models.ForeignKey('Queue', on_delete='PROTECT')
    # next = models.ForeignKey('Queue', on_delete='PROTECT')
    name = models.CharField(max_length=96)
    script = models.TextField()
    project = models.ForeignKey('ObsProjectRef', on_delete='PROTECT')
    session = models.CharField(max_length=16)
    observer = models.ForeignKey('Observer', on_delete='PROTECT')
    operator = models.ForeignKey('Operator', on_delete='PROTECT')
    time_submitted = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'Queue'


class ConfigScript(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=96, blank=True, null=True)
    script = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configscript'
