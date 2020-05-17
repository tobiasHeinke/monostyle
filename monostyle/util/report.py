
"""
util.report
~~~~~~~~~~~

Tool output.
"""

import monostyle.config as config
from monostyle.util.monostylestd import path_to_rel, print_title


class Report():
    """Universal tool output format.

    severity -- severity level of the report.
    tool -- name of the tool which issued the report.
    out -- extracted content Fragment defines the file path and name and position
    msg -- message.
    line -- extracted line Fragment.
    fix -- autofix options.
    """

    __slots__ = ('severity', 'tool', 'out', 'msg', 'line', 'fix')

    def __init__(self, severity, tool, out, msg, line=None, fix=None):
        self.severity = severity
        self.tool = tool
        self.out = out
        self.msg = msg
        self.line = line
        self.fix = fix


    error = 'E'
    warning = 'W'
    info = 'I'
    log = 'L'
    severities = (error, warning, info, log)

    severity_long = {
        'E': "Error",
        'W': "Warning",
        'I': "Info",
        'L': "Log",
        'U': "Unset"
    }
    severity_icons = {
        'E': "<e>",
        'W': "/!\\",
        'I': "(i)",
        'L': "[=]",
        'U': "[ ]"
    }

    def repr(self, options=None):
        if options is None:
            options = {}
        options = {
            "format_str": "{fn}{loc} {severity} {out} {msg}{line}",
            "show_filename":True,
            "show_end": False,

            "severity_display": "char",

            "out_sep_start": "'",
            "out_sep_end": "'",
            "out_max_len": 100,
            "out_ellipse": "…",

            "show_line":True,
            "line_max_len": 200,
            "line_indent": ">>>",
            "line_ellipse": "…",

            "autofix_mark": "@",
            **options
        }
        output = {}
        for slot in self.__slots__:
            output[slot] = ""
        output["fn"] = ""
        output["loc"] = ""

        if not options.get("file_title", False) and options["show_filename"]:
            output["fn"] = path_to_rel(self.out.fn) + ":"

        if options["severity_display"] == "char":
            output["severity"] = self.severity
        elif options["severity_display"] == "icon":
            output["severity"] = self.severity_icons.get(self.severity, self.severity_icons["U"])
        else:
            output["severity"] = self.severity_long.get(self.severity, self.severity_long["U"])

        output["tool"] = self.tool

        if self.out.start_lincol and self.out.start_lincol[0] != -1:
            output["loc"] = str(self.out.start_lincol[0] + 1) + "," + \
                            str(self.out.start_lincol[1] + 1)

            if options["show_end"]:
                output["loc"] += " - {0},{1}".format(self.out.end_lincol[0] + 1,
                                                     self.out.end_lincol[1] + 1)

        elif self.out.start_pos != -1:
            output["loc"] = str(self.out.start_pos)

            if options["show_end"]:
                output["loc"] += " - " + str(self.out.end_pos)

        if len(self.out) != 0:
            output["out"] = str(self.out).replace("\n", "")
            if len(output["out"]) > options["out_max_len"]:
                output["out"] = output["out"][:options["out_max_len"]] + options["out_ellipse"]
            output["out"] = options["out_sep_start"] + output["out"] + options["out_sep_end"]

        output["msg"] = self.msg

        if options["show_line"] and self.line:
            output["line"] = str(self.line).replace('\n', '¶')
            if len(output["line"]) > options["line_max_len"]:
                output["line"] = output["line"][:options["line_max_len"]] + options["line_ellipse"]
            output["line"] = "\n" + options["line_indent"] + output["line"]

        if self.fix is not None:
            output["fix"] = options["autofix_mark"]
        return options["format_str"].format(**output)


    def __repr__(self):
        self.repr()


    def copy(self):
        return type(self)(self.severity, self.tool, self.out.copy(), self.msg,
                          self.line.copy(), self.fix.copy())


def print_reports(reports, options=None):
    """Print the reports in the command line."""
    if reports is None:
        return None
    if options is None:
        options = config.console_options

    options = {
        "file_title": True,
        "file_title_underline": None,
        "show_summary": False,
        "summary_overline": '_',
        **options
    }

    fn_prev = None
    for report in reports:
        if report is not None:
            if options["file_title"]:
                if fn_prev != report.out.fn:
                    print_title(path_to_rel(report.out.fn),
                                underline=options["file_title_underline"])

                fn_prev = report.out.fn

            print(report.repr(options))

    if options["show_summary"]:
        # Show the count of each severity after the reports output.
        levels = Report.severity_icons.copy()
        for key in levels.keys():
            levels[key] = 0
        for report in reports:
            levels[report.severity] += 1

        summary = []
        for key, val in levels.items():
            if key != 'L' and (key != 'U' or val != 0):
                sev = key
                if options["severity_display"] == "icon":
                    sev = Report.severity_icons.get(key, Report.severity_icons["U"])
                elif options["severity_display"] == "long":
                    sev = Report.severity_long.get(key, Report.severity_long["U"])

                summary.append(sev + ": " + str(val))

        summary.append("total" + ": " + str(len(reports)))

        if options["summary_overline"]:
            print(options["summary_overline"] * len(", ".join(summary)))
        print(", ".join(summary))
