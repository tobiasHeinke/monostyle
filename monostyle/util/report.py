
"""
util.report
~~~~~~~~~~~

Tool output.
"""

import re

import monostyle.config as config
from monostyle.util.monostylestd import path_to_rel, print_title


class MsgTemplate():

    __slots__ = ('_template', '_components')

    key_re = re.compile(r"(?:(?<=[^{])|\A)\{(\?)?(\w+?)\}(?:(?=[^}])|\Z)")
    esc_re = re.compile(r"([{}])(?=\1)")


    def __init__(self, template):
        self._template = template
        self._components = self.parse(template)


    def parse(self, template):
        """Parse template.
        {key} and {?key} for optional components.
        Escape with double curly bracket.
        """
        components = []
        last = 0
        for key_m in re.finditer(self.key_re, template):
            before = template[last:key_m.start(0)].strip()
            if len(before) != 0:
                components.append((False, re.sub(self.esc_re, "", before), False))
            components.append((True, key_m.group(2), bool(key_m.group(1) is not None)))
            last = key_m.end(0)

        if last != len(template):
            components.append((False, template[last:].strip(), False))

        return tuple(components)


    def substitute(self, mapping=None, **kwargs):
        """Substitute template keys. kwargs overrides mapping."""
        if mapping is not None:
            if kwargs is not None:
                mapping.update(kwargs)

            kwargs = mapping

        msg = []
        missing_keys = None
        for is_key, value, is_optional in self._components:
            if not is_key:
                msg.append(value)
            else:
                subst = str(kwargs.get(value, "")).strip()
                if len(subst) != 0:
                    msg.append(subst)
                elif not is_optional:
                    if missing_keys is None:
                        missing_keys = []
                    msg.append("{" + value + "}")
                    missing_keys.append(value)

        msg = " ".join(msg)
        if missing_keys is not None:
            print("Error missing template keys:", ", ".join(missing_keys), "in message:", msg)

        return msg


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


    #--------------------
    # Severity

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


    #--------------------
    # Message Templates

    quantity = MsgTemplate("{what} {?where} {?how}").substitute
    existing = MsgTemplate("{what} {?where}").substitute
    missing = MsgTemplate("no {what} {?where}").substitute
    under = MsgTemplate("too few {what} {?where}").substitute
    over = MsgTemplate("too many {what} {?where}").substitute

    misplaced = MsgTemplate("{what} {where} should be {to_where}").substitute
    misformatted = MsgTemplate("{what} {?where} {?how}").substitute

    substitution = MsgTemplate("{what} {?where} should be {with_what}").substitute
    conditional = MsgTemplate("{what} {?where} should be {with_what} {when}").substitute
    option = MsgTemplate("{what} {?where} should be either {with_what}").substitute

    msg_templates = ("quantity", "existing", "missing", "under", "over",
                  "misplaced", "misformatted", "substitution", "conditional", "option")


    def override_templates(new_templates):
        """Override or add templates with a dict."""
        for key, value in new_templates.items():
            if (isinstance(key, str) and isinstance(value, str) and
                    (key in Report.msg_templates or getattr(Report, key) is None)):
                setattr(Report, key, MsgTemplate(value).substitute)


    #--------------------


    def repr(self, options=None):
        if options is None:
            options = {}
        options = {
            "format_str": "{fn}{loc} {severity} {out} {msg}{line}",
            "show_filename": True,
            "absolute_path": False,
            "show_end": False,

            "severity_display": "char",

            "out_sep_start": "'",
            "out_sep_end": "'",
            "out_max_len": 100,
            "out_ellipse": "…",

            "show_line": True,
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
            if options["absolute_path"]:
                output["fn"] = self.out.fn + ":"
            else:
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
        "absolute_path": False,
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
                    fn = report.out.fn if options["absolute_path"] else path_to_rel(report.out.fn)
                    print_title(fn, underline=options["file_title_underline"])

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
