#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Git-related operations"""

# import argparse
# import re
import os
import subprocess

# # ../AGBT19A_999.OREO.2019-06-14_15:57:59.OPERATOR.script.txt
# DATE_REGEX = re.compile(
#     r"(?P<project>\w+)\.(?P<scriptname>\w+).*(?P<date>\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2}).*\.script\.txt$"
# )


def gitify(results, output, include_log=False):
    subprocess.check_output(["git", "init"], cwd=output)

    for (
        project_name,
        script_name,
        execution_date,
        executed_script,
        log,
    ) in results.values_list(
        "obsprocedure__obsprojectref__name",
        "obsprocedure__name",
        "datetime",
        "executed_script",
        "log",
    ):
        commit_script_execution(
            project_name,
            script_name,
            execution_date,
            executed_script,
            log,
            output,
            include_log=include_log,
        )


def commit_script_execution(
    project_name,
    script_name,
    execution_date,
    executed_script,
    log,
    output,
    include_log=False,
):
    script_file_name = "{project_name}.{script_name}.script.py".format(
        project_name=project_name, script_name=script_name
    )
    log_file_name = "{project_name}.{script_name}.log.py".format(
        project_name=project_name, script_name=script_name
    )

    script_file_path = os.path.join(output, script_file_name)
    log_file_path = os.path.join(output, log_file_name)
    with open(script_file_path, "w") as file:
        file.write(executed_script)
    subprocess.check_output(["git", "add", script_file_name], cwd=output)

    if include_log:
        with open(log_file_path, "w") as file:
            file.write(log)
        subprocess.check_output(["git", "add", log_file_name], cwd=output)
    status = subprocess.check_output(["git", "diff", "--cached"], cwd=output)
    if status:
        subprocess.check_output(
            [
                "git",
                "commit",
                "-m",
                "Commit created by turtlecli",
                "--date",
                str(execution_date),
            ],
            cwd=output,
        )


# def gitify_path(dir_path):
#     dir_path = Path(dir_path)
#     files = [path for path in dir_path.iterdir() if path.is_file()]
#     for file_path in tqdm(files, unit="file"):
#         match = DATE_REGEX.match(file_path.name)
#         if match:
#             project_name = match.groupdict()["project"]
#             script_name = match.groupdict()["scriptname"]
#             execution_date = match.groupdict()["date"]
#             commit_script_execution(project_name, script_name, execution_date)


# def main():
#     args = parse_args()
#     path = args.path
#     gitify_path(path)


# def parse_args():
#     parser = argparse.ArgumentParser(
#         formatter_class=argparse.ArgumentDefaultsHelpFormatter
#     )
#     parser.add_argument("path")
#     return parser.parse_args()


# if __name__ == "__main__":
#     main()
