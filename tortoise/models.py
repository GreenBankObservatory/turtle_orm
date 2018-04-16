# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class History(models.Model):
    id = models.BigAutoField(primary_key=True)
    obsprocedure_id = models.IntegerField()
    observer_id = models.IntegerField()
    operator_id = models.IntegerField()
    datetime = models.DateTimeField()
    version = models.CharField(max_length=16)
    executed_script = models.TextField()
    executed_state = models.CharField(max_length=14)
    log = models.TextField()

    class Meta:
        managed = False
        db_table = 'History'


class Obsprocedure(models.Model):
    name = models.CharField(max_length=96)
    session = models.CharField(max_length=16)
    script = models.TextField()
    obsprojectref_id = models.IntegerField()
    operator_id = models.IntegerField()
    observer_id = models.IntegerField()
    state = models.CharField(max_length=13)
    status = models.CharField(max_length=7)
    last_modified = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'ObsProcedure'


class Obsprojectref(models.Model):
    name = models.CharField(unique=True, max_length=96)
    primary_observer = models.IntegerField()
    session = models.CharField(max_length=16)

    class Meta:
        managed = False
        db_table = 'ObsProjectRef'


class Observer(models.Model):
    name = models.CharField(max_length=96)

    class Meta:
        managed = False
        db_table = 'Observer'


class Operator(models.Model):
    name = models.CharField(max_length=96)

    class Meta:
        managed = False
        db_table = 'Operator'


class Queue(models.Model):
    id = models.BigAutoField(primary_key=True)
    obsprocedure_id = models.IntegerField()
    prev_id = models.BigIntegerField()
    next_id = models.BigIntegerField()
    name = models.CharField(max_length=96)
    script = models.TextField()
    project_id = models.IntegerField()
    session = models.CharField(max_length=16)
    observer_id = models.IntegerField()
    operator_id = models.IntegerField()
    time_submitted = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'Queue'


class Security(models.Model):
    id = models.IntegerField(unique=True)
    authkey = models.CharField(max_length=96)

    class Meta:
        managed = False
        db_table = 'Security'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=80)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group_id = models.IntegerField()
    permission_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group_id', 'permission_id'),)


class AuthMessage(models.Model):
    user_id = models.IntegerField()
    message = models.TextField()

    class Meta:
        managed = False
        db_table = 'auth_message'


class AuthPermission(models.Model):
    name = models.CharField(max_length=50)
    content_type_id = models.IntegerField()
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type_id', 'codename'),)


class AuthUser(models.Model):
    username = models.CharField(unique=True, max_length=30)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.CharField(max_length=75)
    password = models.CharField(max_length=128)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    is_superuser = models.IntegerField()
    last_login = models.DateTimeField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user_id = models.IntegerField()
    group_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user_id', 'group_id'),)


class AuthUserUserPermissions(models.Model):
    user_id = models.IntegerField()
    permission_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user_id', 'permission_id'),)


class Configscript(models.Model):
    name = models.CharField(max_length=96, blank=True, null=True)
    script = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configscript'


class DjangoContentType(models.Model):
    name = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)
