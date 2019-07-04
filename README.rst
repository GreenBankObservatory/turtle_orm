``turtlecli`` Documentation
===========================

Background
----------

The Turtle database stores a history of every observation script that has ever been executed on the GBT, along with their respective operator, observer, project, etc.


Overview
--------

``turtlecli`` will allow you to easily answer questions such as:

    - What scripts have been run in the last 24 hours? What is in their logs?
    - What was happening at a given time?
    - When has a given project been run?
    - How has a given script changed over time? Or: it used to work, what happened?
    - Which scripts have I run... ever? What were their contents?

Note that these questions can be partially answered by using a combination of the OpsLog and DSS, but neither of these tools is a direct reflection what actually happened on the system. That is, the Turtle DB represents a third source of truth for answering "what happened?" sorts of questions, but it has been markedly more opaque than the other two.

A few notes:
    - For most use cases, you will want to include either ``--fuzzy`` or ``--regex`` to make the searches a little more thorough
    - Running this from your workstation will probably be very slow, and you will thus be prompted if you attempt to do so. I'd recommend using a machine intended for data processing instead.
    - This is an early draft, and there isn't really any error checking, so certain combinations of arguments might lead to unexpected behavior
    - This script has a read-only view of the turtle database, and thus is unable to break anything
    - Until this finds a permanent home, you'll probably want to ``$ alias turtlecli=~monctrl/bin/turtlecli``
    - More complete help is available via the ``--help`` argument

Example Usage
-------------

Scripts in the last 24 hours
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This should complement the `OpsLog <https://dss.gb.nrao.edu/ops/search>`_, but with some additional (and more precise) information, along with logs. Note that you could also do ``--last 1 --unit days`` here.

.. code-block:: bash

    $ ~monctrl/bin/turtlecli --last 24 --logs
    Displaying scripts that occurred within the last 24.0 hours, ordered by datetime (descending)
        Project Name    Script Name              Executed (EST)       Observer         Operator         State
    --  --------------  -----------------------  -------------------  ---------------  ---------------  -------------
     0  AGBT18A_314     mapping                  2018-04-17 14:24:52  Toney Minter     David Rose       obs_completed
     1  AGBT18A_314     mapping                  2018-04-17 14:13:08  Toney Minter     David Rose       obs_completed

    Showing logs for all above results
    Logs for script mapping, executed at 2018-04-17 14:24:52 by observer Toney Minter
    [14:24:53] ******** Begin Scheduling Block
    [14:24:53] ******** observer = Toney Minter, SB name = mapping, project ID = AGBT18A_314, date = 17 Apr 2018
    <snip>


What was happening at a given time?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Something went wrong at February 3rd, 2014 at 3:00am? What was happening in the 2-hour window centered on this datetime?

Note that buffer here grabs scripts that were executed within +- 1 hour of the given datetime.

.. code-block:: bash

    $ ~monctrl/bin/turtlecli --times 'Feb 3 2014 3am' --buffer 1
    Displaying scripts that occurred within 1:00:00 hours of 2014-02-03 03:00:00, ordered by datetime (descending)
        Project Name    Script Name    Executed (EST)       Observer    Operator    State
    --  --------------  -------------  -------------------  ----------  ----------  --------------
     0  AGBT13B_405     Abell773       2014-02-03 03:08:27  Lucas Hunt  Greg Monk   obs_in_progess
     1  AGBT13B_405     3C147          2014-02-03 02:52:14  Lucas Hunt  Greg Monk   obs_completed


When has a given project been run?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This would complement https://dss.gb.nrao.edu/project/GBT18A-460, but, again, will show what actually happened instead of what was scheduled or reported.

.. code-block:: bash

    $ ~monctrl/bin/turtlecli --project AGBT18A_460
    Displaying scripts for project ['AGBT18A_460'], ordered by datetime (descending)
        Project Name    Script Name         Executed (EST)       Observer        Operator    State
    --  --------------  ------------------  -------------------  --------------  ----------  -------------
     0  AGBT18A_460     3-FRB121102_C-Band  2018-04-16 22:19:25  Andrew Seymour  David Rose  obs_completed
    <snip>
     8  AGBT18A_460     1-Fluxcal_C-Band    2018-03-26 02:02:31  Ryan Lynch      Greg Monk   obs_aborted


How has a given script changed over time?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Is the script I'm running now different than the last time it worked?

Note that the diff output will be colored in the terminal, and somewhat easier to read. Also note that --interactive is passed here, which means you will be stepped through each diff, one at a time. At the end, you will drop into an interactive shell.

.. code-block:: bash

    $ ~monctrl/bin/turtlecli --project AGBT18A_460 --script 3-FRB121102_C-Band --diff --interactive
    Displaying scripts for project ['AGBT18A_460'], for script ['3-FRB121102_C-Band'], ordered by datetime (descending)
        Project Name    Script Name         Executed (EST)       Observer        Operator    State
    --  --------------  ------------------  -------------------  --------------  ----------  -------------
     0  AGBT18A_460     3-FRB121102_C-Band  2018-04-16 22:19:25  Andrew Seymour  David Rose  obs_completed
     1  AGBT18A_460     3-FRB121102_C-Band  2018-03-26 02:24:36  Ryan Lynch      Greg Monk   obs_completed

    Showing differences between all above results, interactively
    Differences between scripts A (executed 2018-04-16 22:19:25) and B (executed 2018-03-26 02:24:36)
    ---

    +++

    @@ -3,7 +3,7 @@


     src = "FRB121102"
     #duration = 2.5*3600
    -stopTime = "00:30:00"
    +stopTime = "04:30:00"
     #stopTime = Horizon(5.5)

     config_nocal = """
    @@ -17,7 +17,7 @@

     pol = 'Linear'
     backend   = 'VEGAS'
     bandwidth = 1500.0
    -tint = 81.92e-6
    +tint = 40.96e-6
     nwin = 4
     deltafreq = 0.0
     swmode = 'tp_nocal'
    @@ -47,7 +47,7 @@

     pol = 'Linear'
     backend   = 'VEGAS'
     bandwidth = 1500.0
    -tint = 81.92e-6
    +tint = 40.96e-6
     nwin = 4
     deltafreq = 0.0
     swmode = 'tp'
    --------------------------------------------------------------------------------
    Press any key to see the next diff (or 'q' to exit the loop)
    Results are available in the `results` variable.


Which scripts have I run... ever?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify ``--observer`` in order to show only scripts that they have executed.

.. code-block:: bash

    $ ~monctrl/bin/turtlecli --observer 'Thomas Chamberlin' --show-scripts
    Displaying scripts by observer Thomas Chamberlin, ordered by datetime (descending)
        Project Name    Script Name                  Executed (EST)       Observer           Operator         State
    --  --------------  ---------------------------  -------------------  -----------------  ---------------  -------------
     0  TINT            integration1_vegas           2018-04-13 19:17:48  Thomas Chamberlin  Amanda Wichterm  obs_completed
    <snip>
    17  JAPI            Ryan_LO1_config_test         2018-02-27 18:21:04  Thomas Chamberlin  Greg Monk        obs_aborted

    Showing script contents for all above results
    Contents of scripts executed at 2018-04-13 19:17:48
    --------------------------------------------------------------------------------
    #Configuration
    lband_acs_tp = """
    receiver  = 'Rcvr1_2'
    <snip>
