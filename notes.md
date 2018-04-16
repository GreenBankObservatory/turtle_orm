## Create project

    $ virtualenv tchamber-turtle-orm-env
    $ pip install django mysqlclient ipython
    # Get the structure set up
    $ django-admin startproject turtle_orm .

    $ ./manage.py startapp turtle
    CommandError: 'turtle' conflicts with the name of an existing Python module and cannot be used as an app name. Please try another name.


    $ ./manage.py startapp tortoise

    $ ./manage.py inspectdb > tortoise/models.py

    $ ./manage.py shell

    In [1]: from tortoise.models import *
    ...
    RuntimeError: Model class tortoise.models.History doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS.


And that was it! ORM is now functional. Manual steps:

* Clean up model names to proper camel case
* Add __str__ methods

And, of course, some issues... first of all, many models don't have primary keys. This is simply due to the fact that their tables are malformed; not sure how to handle it.


## Questions that we want the ORM to handle

* What scripts have been run for project FOO?
* What was happening at time BAR?
* 




## Random shit

    WARNINGS:
    ?: (mysql.W002) MySQL Strict Mode is not set for database connection 'default'
            HINT: MySQL's Strict Mode fixes many data integrity problems in MySQL, such as data truncation upon insertion, by escalating warnings into errors. It is strongly recommended you activate it. See: https://docs.djangoproject.com/en/2.0/ref/databases/#mysql-sql-mode

    Fixed this by adding `'sql_mode': 'STRICT_ALL_TABLES'`




    All of the auth tables were causing issues and we don't need them anyway, so I'm removing them from ORM

    Paul and I agreed that the turtle DB should not be modified by this ORM. So, I've created a readonly user that I will be using.
