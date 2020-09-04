
"""
util.report
~~~~~~~~~~~

Tool output.
"""

import re
from math import ceil

import monostyle.config as config
from monostyle.util.monostylestd import print_over, print_title, path_to_rel


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

    severity_maps = {
        "letter": {
            'E': error,
            'W': warning,
            'I': info,
            'L': log,
            'U': 'U'
        },
        "long": {
            'E': "Error",
            'W': "Warning",
            'I': "Info",
            'L': "Log",
            'U': "Unset"
        },
        "ascii": {
            'E': "<e>",
            'W': "/!\\",
            'I': "(i)",
            'L': "[=]",
            'U': "[ ]"
        },
        "icon": {
            'E': "\u274C\uFE0E",
            'W': "\u26A0\uFE0E",
            'I': "\u2139\uFE0E",
            'L': "\u1F4C3\uFE0E",
            'U': "\u2754\uFE0E"
        },
        "emoji": {
            'E': "\u274C",
            'W': "\u26A0",
            'I': "\u2139\uFE0F",
            'L': "\u1F4C3",
            'U': "\u2754"
        }
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
            "format_str": "{filename}{loc} {severity} {out} {msg}{line}",
            "show_filename": True,
            "absolute_path": False,
            "show_end": False,

            "severity_display": "letter",

            "out_sep_start": "'",
            "out_sep_end": "'",
            "out_max_len": 100,
            "out_ellipsis": "…",

            "show_line": True,
            "line_max_len": 200,
            "line_indent": ">>>",
            "line_ellipsis": "…",

            "show_autofix": False,
            "autofix_mark": "@",
            **options
        }
        output = {}
        for slot in self.__slots__:
            output[slot] = ""
        output["filename"] = ""
        output["loc"] = ""

        if not options.get("file_title", False) and options["show_filename"]:
            if options["absolute_path"]:
                output["filename"] = self.out.filename + ":"
            else:
                output["filename"] = path_to_rel(self.out.filename) + ":"

        sev_map = self.severity_maps.get(options["severity_display"], self.severity_maps["letter"])
        output["severity"] = sev_map.get(self.severity, sev_map["U"])

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
                output["out"] = output["out"][:options["out_max_len"]] + options["out_ellipsis"]
            output["out"] = options["out_sep_start"] + output["out"] + options["out_sep_end"]

        output["msg"] = self.msg

        if options["show_line"] and self.line:
            output["line"] = str(self.line).replace('\n', '¶')
            if len(output["line"]) > options["line_max_len"]:
                output["line"] = output["line"][:options["line_max_len"]] + options["line_ellipsis"]
            output["line"] = "\n" + options["line_indent"] + output["line"]

        if options["show_autofix"] and self.fix is not None:
            output["fix"] = options["autofix_mark"]
        return options["format_str"].format(**output)


    def __repr__(self):
        self.repr()


    def copy(self):
        return type(self)(self.severity, self.tool, self.out.copy(), self.msg,
                          self.line.copy(), self.fix.copy())


def options_overide(options=None):
    """Override the default print options."""
    if options is None:
        options = options_overide(config.console_options)

    options = {
        "file_title": True,
        "absolute_path": False,
        "file_title_underline": None,
        "show_summary": False,
        "summary_overline": '_',
        **options
    }
    return options


def print_reports(reports, options=None):
    """Print the reports in the command line."""
    if reports is None:
        return None

    options = options_overide()
    for report in reports:
        if report is not None:
            print_report(report, options)

    if options["show_summary"]:
        summary = reports_summary(reports, options)


def print_report(report, options=None, filename_prev=None):
    """Print a single report. Returns the filename of the report for storage."""
    if report is None:
        return
    if options and options["file_title"]:
        if filename_prev is None or filename_prev != report.out.filename:
            print_title(report.out.filename if options["absolute_path"]
                        else path_to_rel(report.out.filename),
                        underline=options["file_title_underline"])

    print_over(report.repr(options))
    return report.out.filename


def reports_summary(reports, options):
    """Show the count of each severity of the reports."""
    summary = dict.fromkeys(Report.severities, 0)
    summary.setdefault("total", 0)

    for report in reports:
        if report.severity in summary.keys():
            summary[report.severity] += 1
        summary["total"] += 1

    summary_text = []
    for key, val in summary.items():
        if key not in {'L', "total"} and (key != 'U' or val != 0):
            sev_map = Report.severity_maps.get(options["severity_display"],
                                               Report.severity_maps["letter"])
            summary_text.append(sev_map.get(key, sev_map["U"]) + ": " + str(val))

    summary_text.append("total" + ": " + str(summary["total"]))

    if options["summary_overline"]:
        print_over(options["summary_overline"] * len(", ".join(summary_text)))
    print_over(", ".join(summary_text))


#------------------------


def getline_lineno(fg, lineno):
    """Extracts single line selected by its line number."""
    return fg.slice((lineno, 0), (lineno+1, 0), True)


def getline_newline(fg, loc, n):
    """Extracts line including lines around it.

    loc -- position within the line.
    n -- number of lines to include around the line (odds below).
    """
    start = (loc[0] - ceil(n / 2), 0)
    end = (loc[0] + (n // 2) + 1, 0)
    return fg.slice(start, end, True)


def getline_punc(fg, pos, match_len, min_chars, margin):
    """Extracts line limited by punctuation.

    pos -- position within the line.
    match_len -- length of the output.
    min_chars -- minimal amount of chars to extract on both sides.
    margin -- length of the outer margin within to search for punctuation marks.
    """
    start = pos - min_chars - margin
    end = pos + match_len + min_chars + margin
    buf = fg.slice(start, end, True)

    margin_start, _, margin_end = buf.slice(start + margin, end - margin)

    if margin_start and len(margin_start) != 0:
        margin_start_str = str(margin_start)
        start_m = None
        for start_m in re.finditer(r"[.?!:,;]", margin_start_str):
            pass
        if start_m:
            start = margin_start.loc_to_abs(start_m.end(0))

    if margin_end and len(margin_end) != 0:
        if end_m := re.search(r"[.?!:,;]", str(margin_end)):
            end = margin_end.loc_to_abs(end_m.end(0))

    return buf.slice(start, end, True)
