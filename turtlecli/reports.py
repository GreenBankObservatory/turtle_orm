import difflib
import logging
import subprocess

from colorama import Fore

from turtlecli.utils import color_diff, gen2


logger = logging.getLogger(__name__)


class TurtleReport:
    def __init__(self, results, interactive=False, text_color=Fore.BLUE):
        self.results = results
        self.title = (
            "{}{}".format(self.title, ", interactively" if interactive else "")
        )
        self.text_color = text_color
        self.interactive = interactive
        self.result_generator = results

    def colorize(self, text):
        return "{}{}{}".format(self.text_color, text, Fore.RESET)

    def report_msg(self, text, raw=False):
        
        _, console_width_str = subprocess.check_output(['stty', 'size']).decode().split()
        try:
            console_width = int(console_width_str)
        except ValueError:
            console_width = 80
            logger.warning("Could not detect console width; falling back to default of {}".format(console_width))

        if raw:
            print(text)
            print("-" * console_width)
        else:
            print(self.colorize(text))
            print(self.colorize("-" * console_width))

    def gen_result_header(self):
        raise NotImplementedError("Must be implemented by child class")

    def gen_result_report(self):
        raise NotImplementedError("Must be implemented by child class")

    def print_report(self):
        self.report_msg(self.title)
        for result in self.result_generator:
            self.report_msg(self.gen_result_header(result))
            self.report_msg(self.gen_result_report(result), raw=True)
            if self.interactive:
                response = input(self.colorize("Press any key to see the next diff (or 'q' to exit the loop)"))
                if response.lower().startswith("q"):
                    break

class LogReport(TurtleReport):
    title = "Showing logs for all above results"
        
    def gen_result_header(self, result):
        return (
            "Logs for script {script}, executed at {exec} by observer {observer}"
            .format(
                observer=result.observer.name,
                script=result.obsprocedure.name,
                exec=result.datetime,
            )
        )

    def gen_result_report(self, result):
        return result.log

class ScriptReport(TurtleReport):
    title = "Showing scripts for all above results"

    def gen_result_header(self, result):
        return (
            "Contents of scripts executed at {exec}"
            .format(exec=result.datetime)
        )

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
        script_a_lines = script_a.split('\n')
        script_b_lines = script_b.split('\n')

        if compact:
            diff = difflib.unified_diff(script_a_lines, script_b_lines)
        else:
            diff = difflib.ndiff(script_a_lines, script_b_lines)
        colordiff = color_diff(diff)
        return colordiff

    def gen_result_header(self, result):
        # Due to our result_generator, result is actually two results
        result_a, result_b = result
        return(
            "Differences between scripts A (executed {a}) and B (executed {b})"
            .format(
                a=result_a.datetime,
                b=result_b.datetime,
            )
        )

    def gen_result_report(self, result):
        # Due to our result_generator, result is actually two results
        result_a, result_b = result
        diff = self.diff_scripts(result_a.executed_script, result_b.executed_script)
        return '\n'.join(diff)
