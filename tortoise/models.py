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
    name = models.CharField(max_length=96, help_text="Full name")

    class Meta:
        managed = False
        db_table = "Observer"

    def __str__(self):
        return "Observer {}".format(self.name)


class Operator(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=96, help_text="Full name")

    class Meta:
        managed = False
        db_table = "Operator"

    def __str__(self):
        return "Operator {}".format(self.name)


class History(models.Model):
    id = models.BigAutoField(primary_key=True)
    obsprocedure = models.ForeignKey(
        "ObsProcedure",
        on_delete="PROTECT",
        verbose_name="Procedure",
        help_text="ObsProcedure object being executed",
    )
    observer = models.ForeignKey(
        "Observer",
        on_delete="PROTECT",
        help_text="Observer in charge of script execution",
    )
    operator = models.ForeignKey(
        "Operator",
        on_delete="PROTECT",
        help_text="Operator in charge of script execution",
    )
    datetime = models.DateTimeField(help_text="Date of script execution")
    version = models.CharField(max_length=16, help_text="M&C Software Version")
    executed_script = models.TextField(
        help_text="The full contents of the executed observing script"
    )
    executed_state = models.CharField(
        max_length=14,
        choices=(
            ("Aborted", "obs_aborted"),
            ("Completed", "obs_completed"),
            ("In Progress", "obs_in_progess"),
        ),
        help_text="State of the script execution",
    )
    log = models.TextField(help_text="The execution log for the script")

    objects = HistoryManager()

    class Meta:
        managed = False
        db_table = "History"

    def __str__(self):
        return "History {} at {}".format(self.id, self.datetime)


class ObsProjectRef(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=96)
    primary_observer = models.ForeignKey(
        "Observer", on_delete="PROTECT", db_column="primary_observer"
    )
    session = models.CharField(max_length=16)

    class Meta:
        managed = False
        db_table = "ObsProjectRef"

    def __str__(self):
        # TODO: Better way to handle this (without changing the DB)?
        try:
            observer = self.primary_observer
        except Observer.DoesNotExist:
            logger.warning("No Observer exists with ID %s", self.primary_observer_id)
            observer = None

        return "ObsProjectRef name: {}, observer: {}, session: {}".format(
            self.name, observer, self.session
        )


class ObsProcedure(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=96, help_text="Name of the observation script")
    session = models.CharField(
        max_length=16, help_text="Session ID <NOTE: THIS IS NOT POPULATED>"
    )
    script = models.TextField(help_text="Observation script contents")
    obsprojectref = models.ForeignKey("ObsProjectRef", on_delete="PROTECT")
    operator = models.ForeignKey("Operator", on_delete="PROTECT")
    observer = models.ForeignKey("Observer", on_delete="PROTECT")
    state = models.CharField(
        max_length=13,
        choices=(
            ("Not Completed", "not_completed"),
            ("Completed", "completed"),
            ("Saved", "saved"),
        ),
    )
    status = models.CharField(
        max_length=7,
        choices=(
            ("Blank", ""),
            ("Illicit", "illicit"),
            ("Unknown", "unknown"),
            ("Valid", "valid"),
        ),
    )
    last_modified = models.DateTimeField(
        help_text="Date on which this script was last saved"
    )

    class Meta:
        managed = False
        db_table = "ObsProcedure"

    def __str__(self):
        return "ObsProcedure name: {}, session: {}, state: {}, status: {}".format(
            self.name, self.session, self.state, self.status
        )

    def full_name(self):
        escaped_name = self.name.replace("/", r"\/")
        return "{}/{}".format(self.obsprojectref.name, escaped_name)
