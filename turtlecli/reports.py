import difflib
import logging
import os

from colorama import Fore

from turtlecli.utils import color_diff, gen2, get_console_width


logger = logging.getLogger(__name__)


class TurtleReport:
    def __init__(self, results, interactive=False, text_color=Fore.BLUE):
        self.results = results
        self.title = "{}{}".format(self.title, ", interactively" if interactive else "")
        self.text_color = text_color
        self.interactive = interactive
        self.result_generator = results

    def colorize(self, text):
        return "{}{}{}".format(self.text_color, text, Fore.RESET)

    def print_report_msg(self, text, raw=False):
        try:
            console_width = get_console_width()
        except ValueError:
            console_width = 80
            logger.warning(
                "Could not detect console width; falling back to default of {}".format(
                    console_width
                )
            )

        if raw:
            print(text)
            print("-" * console_width)
        else:
            print(self.colorize(text))
            print(self.colorize("-" * console_width))

    def gen_filename(self):
        raise NotImplementedError("Must be implemented by child class")

    def gen_result_header(self):
        raise NotImplementedError("Must be implemented by child class")

    def gen_result_report(self):
        raise NotImplementedError("Must be implemented by child class")

    def save_report(self, path):
        for result in self.result_generator:
            full_path = os.path.join(path, self.gen_filename(result))
            with open(full_path, "w") as file:
                try:
                    file.write(self.gen_result_report(result))
                except Exception as error:
                    logger.error("Failed to generate filename for {result}; skipping".format(result=result))

            logger.debug(
                "Saved {result} to {full_path}".format(
                    result=result, full_path=full_path
                )
            )

    def print_report(self):
        self.print_report_msg(self.title)
        for result in self.result_generator:
            self.print_report_msg(self.gen_result_header(result))
            self.print_report_msg(self.gen_result_report(result))
            if self.interactive:
                response = input(
                    self.colorize(
                        "Press any key to see the next diff (or 'q' to exit the loop)"
                    )
                )
                if response.lower().startswith("q"):
                    break


class LogReport(TurtleReport):
    title = "Showing logs for all above results"

    def gen_filename(self, result):
        return "{project}.{script}.{exec}.{observer}.log.txt".format(
            observer=result.observer.name,
            project=result.obsprocedure.obsprojectref.name,
            script=result.obsprocedure.name,
            exec=result.datetime,
        ).replace(" ", "_")

    def gen_result_header(self, result):
        return "Logs for script {script}, executed at {exec} by observer {observer}".format(
            observer=result.observer.name,
            script=result.obsprocedure.name,
            exec=result.datetime,
        )

    def gen_result_report(self, result):
        return result.log


class ScriptReport(TurtleReport):
    title = "Showing scripts for all above results"

    def gen_filename(self, result):
        return "{project}.{script}.{exec}.{observer}.script.txt".format(
            observer=result.observer.name,
            project=result.obsprocedure.obsprojectref.name,
            script=result.obsprocedure.name,
            exec=result.datetime,
        ).replace(" ", "_")
        
    def gen_result_header(self, result):
        return "Contents of scripts executed at {exec}".format(exec=result.datetime)

    def gen_result_report(self, result):
        return result.executed_script


class DiffReport(TurtleReport):
    title = "Showing logs for all above results"

    def __init__(self, *args, **kwargs):
        super(DiffReport, self).__init__(*args, **kwargs)
        # Iterate through results as pairs -- that is, grab every two items out at a time
        self.result_generator = gen2(self.results)

    @staticmethod
    def diff_scripts(script_a, script_b, compact=True):
        script_a_lines = script_a.split("\n")
        script_b_lines = script_b.split("\n")

        if compact:
            diff = difflib.unified_diff(script_a_lines, script_b_lines)
        else:
            diff = difflib.ndiff(script_a_lines, script_b_lines)
        colordiff = color_diff(diff)
        return colordiff

    def gen_result_header(self, result):
        # Due to our result_generator, result is actually two results
        result_a, result_b = result
        return "Differences between scripts A (executed {a}) and B (executed {b})".format(
            a=result_a.datetime, b=result_b.datetime
        )

    def gen_result_report(self, result):
        # Due to our result_generator, result is actually two results
        result_a, result_b = result
        diff = self.diff_scripts(result_a.executed_script, result_b.executed_script)
        return "\n".join(diff)
