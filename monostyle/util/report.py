
"""
util.report
~~~~~~~~~~~

Tool output.
"""

import re
from math import ceil

import monostyle.config as config
from monostyle.util.monostyle_io import print_over, print_title, path_to_rel

class MessageTemplate():
    """Formatting for messages."""

    __slots__ = ('_template', '_components')

    key_re = re.compile(r"(?:(?<=[^{])|\A)\{(\?)?(\w+?)\}(?:(?=[^}])|\Z)")
    esc_re = re.compile(r"([{}])(?=\1)")


    def __init__(self, template):
        """
        template -- Formatting string.
        """
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

        message = []
        missing_keys = None
        for is_key, value, is_optional in self._components:
            if not is_key:
                message.append(value)
            else:
                subst = str(kwargs.get(value, "")).strip()
                if len(subst) != 0:
                    message.append(subst)
                elif not is_optional:
                    if missing_keys is None:
                        missing_keys = set()
                    message.append("{" + value + "}")
                    missing_keys.add(value)

        message = " ".join(message)
        if missing_keys is not None:
            print("Error missing template keys:", ", ".join(missing_keys), "in message:", message)

        return message


class Report():
    """Universal tool output format."""

    __slots__ = ('severity', 'tool', 'output', 'message', 'line', 'fix')

    def __init__(self, severity, tool, output, message, line=None, fix=None):
        """
        severity -- severity level of the report.
        tool -- name of the tool which issued the report.
        output -- extracted content Fragment defines the file path and name and position
        message -- message outputted to the user.
        line -- extracted line Fragment.
        fix -- autofix options.
        """
        self.severity = severity
        self.tool = tool
        self.output = output
        self.message = message
        self.line = line
        self.fix = fix


    # -- Severity ------------------------------------------------------------

    fatal = 'F'
    error = 'E'
    warning = 'W'
    info = 'I'
    log = 'L'
    severities = (fatal, error, warning, info, log)

    severity_maps = {
        "letter": {
            'F': fatal,
            'E': error,
            'W': warning,
            'I': info,
            'L': log,
            'U': 'U'
        },
        "long": {
            'F': "Fatal",
            'E': "Error",
            'W': "Warning",
            'I': "Info",
            'L': "Log",
            'U': "Unset"
        },
        "ascii": {
            'F': "{#}",
            'E': "<e>",
            'W': "/!\\",
            'I': "(i)",
            'L': "[=]",
            'U': "(?)"
        },
        "icon": {
            'F': "\U0001F6D1\uFE0E",
            'E': "\u274C\uFE0E",
            'W': "\u26A0\uFE0E",
            'I': "\u2139\uFE0E",
            'L': "\U0001F4C3\uFE0E",
            'U': "\u2754\uFE0E"
        },
        "emoji": {
            'F': "\U0001F6D1\uFE0F",
            'E': "\u274C\uFE0F",
            'W': "\u26A0\uFE0F",
            'I': "\u2139\uFE0F",
            'L': "\U0001F4C3\uFE0F",
            'U': "\u2754\uFE0F"
        },
        "color": {
            'F': "\U0001F534\uFE0F",
            'E': "\U0001F7E0\uFE0F",
            'W': "\U0001F7E1\uFE0F",
            'I': "\U0001F535\uFE0F",
            'L': "\u26AB\uFE0F",
            'U': "\u26AA\uFE0F"
        },
        "shape": {
            'F': "\U0001F534\uFE0E",
            'E': "\u274C\uFE0E",
            'W': "\U0001F53A\uFE0E",
            'I': "\u2757\uFE0E",
            'L': "\U0001F7E5\uFE0E",
            'U': "\u2753\uFE0E"
        }
    }


    def map_severity(thresholds, value, start=None):
        """Convert a value to a severity with a list of thresholds."""
        severities = tuple(reversed(Report.severities))
        if not start or start not in severities:
            start = 'I'
        direction = severities[0] <= severities[-1]
        for index, threshold in enumerate(thresholds, -1 + severities.index(start)):
            if bool(value > threshold if direction else value < threshold):
                return severities[min(max(index, 0), len(severities) - 1)]
        return severities[min(max(len(thresholds) -1 + severities.index(start), 0),
                              len(severities) - 1)]


    # -- Message -------------------------------------------------------------

    quantity = MessageTemplate("{what} {?where} {?how}").substitute
    existing = MessageTemplate("{what} {?where}").substitute
    missing = MessageTemplate("no {what} {?where}").substitute
    under = MessageTemplate("too few {what} {?where}").substitute
    over = MessageTemplate("too many {what} {?where}").substitute

    misplaced = MessageTemplate("{what} {where} should be {to_where}").substitute
    misformatted = MessageTemplate("{what} {?where} {?how}").substitute

    substitution = MessageTemplate("{what} {?where} should be {with_what}").substitute
    conditional = MessageTemplate("{what} {?where} should be {with_what} {when}").substitute
    option = MessageTemplate("{what} {?where} should be either {with_what}").substitute

    message_templates = {"quantity", "existing", "missing", "under", "over",
                     "misplaced", "misformatted", "substitution", "conditional", "option"}


    def override_templates(new_templates):
        """Override or add templates with a dict."""
        for key, value in new_templates.items():
            if (isinstance(key, str) and isinstance(value, str) and
                    (key in Report.message_templates or getattr(Report, key) is None)):
                setattr(Report, key, MessageTemplate(value).substitute)


    def write_out_quantity(number, subject, irregular_plural=None, limit=None):
        """Spell out number and inflect the subject for singular and plural forms."""
        if limit is None:
            limit = 99
        number = int(number)
        table = (
            ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"),
            ("ten", "eleven", "twelve", "thir", "four", "fif", "six", "seven", "eigh", "nine"),
            ("", "", "twen", "thir", "for", "fif", "six", "seven", "eigh", "nine")
        )
        if number != 1:
            if not irregular_plural:
                for suffix in {"s", "sh", "ch", "x", "z"}:
                    if subject.endswith(suffix):
                        subject += "es"
                        break
                else:
                    subject += "s"
            else:
                subject = irregular_plural

        if number >= 0 and number <= min(limit, 99):
            if number == 0:
                number = table[0][0]
            else:
                n, d = divmod(number, 10)
                if n < 2:
                    number = table[n][d]
                    if n == 1 and d > 3:
                        number += "teen"
                else:
                    number = table[min(n, 2)][n] + "ty"
                    if d != 0:
                        number += "-" + table[0][d]

        return str(number) + " " + subject


    # -- Fix -----------------------------------------------------------------

    fix_map = (
        {"letter": "/_/",
        "long": "/noautofix/",
        "ascii": "_",
        "icon": "\u2B1C\uFE0E",
        "emoji": "\u2B1C\uFE0F",
        "color": "\u2B1C\uFE0F",
        "shape": "\u2B55\uFE0E"},

        {"letter": "/a/",
        "long": "/autofixed/",
        "ascii": "@",
        "icon": "\u2714\uFE0E",
        "emoji": "\u2714\uFE0F",
        "color": "\u2705\uFE0F",
        "shape": "\U0001F6A9\uFE0E"})


    # -- Line ----------------------------------------------------------------

    def set_line_lineno(self, code, start_end=True):
        """Extract a single line.
        start_end -- use start or end as location.
        """
        lineno = self.output.get_start(False)[0] if start_end else self.output.get_end(False)[0]
        self.line = code.slice((lineno, 0), (lineno+1, 0))
        return self


    def set_line_newline(self, code, n, start_end=True):
        """Extract a line including lines around it.
        n -- number of lines to include around the line (odds below).
        start_end -- use start or end as location.
        """
        lineno = self.output.get_start(False)[0] if start_end else self.output.get_end(False)[0]
        start = (lineno - ceil(n / 2), 0)
        end = (lineno + (n // 2) + 1, 0)
        self.line = code.slice(start, end)
        return self


    def set_line_punc(self, code, min_chars, margin):
        """Extracts line limited by punctuation.
        min_chars -- minimal amount of chars to extract on both sides.
        margin -- length of the outer margin within to search for punctuation marks.
        """
        start = self.output.start_pos - min_chars - margin
        end = self.output.end_pos + min_chars + margin
        buf = code.slice(start, end)

        margin_start, _, margin_end = buf.slice(start + margin, end - margin, plenary=True)

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

        self.line = buf.slice(start, end)
        return self


    def set_line_offset(self, code, offset, after_before=None):
        """Extracts a lines limited by an offset.
        offset -- span to include.
        after_before -- offset after end, before start or half on both sides.
        """
        is_pos = isinstance(offset, int)
        start = self.output.get_start(is_pos)
        end = self.output.get_end(is_pos)
        if after_before is None:
            if is_pos:
                diff = offset // 2
                start -= diff
                end += diff
            else:
                diff = tuple(map(lambda e: e // 2 if e != 0 else 0, offset))
                start = tuple(a - b for a, b in zip(start, diff))
                end = tuple(a + b for a, b in zip(end, diff))
        elif after_before:
            if is_pos:
                end += offset
            else:
                end = tuple(a + b for a, b in zip(end, offset))
        else:
            if is_pos:
                start -= offset
            else:
                start = tuple(a - b for a, b in zip(start, offset))

        self.line = code.slice(start, end)
        return self


    # ------------------------------------------------------------------------

    def repr(self, options=None):
        def join_entries(entries, options, formatting):
            lines = []
            invalid_keys = set()
            for format_line in options["formatting"]:
                line = []
                for key in format_line:
                    value = entries.get(key, Ellipsis)
                    if value is Ellipsis:
                        invalid_keys.add(key)
                        break
                    if value is not None:
                        if start := options.get(key + "_start", None):
                            line.append(start)
                        line.append(value)
                        if end := options.get(key + "_end", None):
                            line.append(end)
                        else:
                            line.append(" ")
                if line:
                    lines.append(''.join(line).rstrip())

            if invalid_keys:
                if not Report.repr.user_notified:
                    print("Report formatting key error: " + ", ".join(invalid_keys))
                    Report.repr.user_notified = True
                options["formatting"] = formatting
                return join_entries(entries, options, formatting)

            return '\n'.join(lines)

        if options is None:
            options = {}

        formatting = (("filename", "location", "severity", "output", "message"), ("line",))
        options = {
            "formatting": formatting,
            "show_filename": True,
            "absolute_path": False,
            "filename_end": ":",

            "location_column": ":",
            "show_location_end": False,
            "location_span": " - ",
            "number_width": "0",

            "severity_display": "long",

            "output_start": "'",
            "output_end": "' ",
            "output_limit": 100,
            "output_ellipsis": "…",

            "show_line": True,
            "line_limit": 200,
            "line_start": ">>>",
            "line_ellipsis": "…",
            "show_marker": False,
            "marker_start": "¦",
            "marker_end": "¦",
            "marker_both": "¤",

            "show_autofix": False,
            "show_autofix_always": False,
            "autofix_display": "long",
            **options
        }
        entries = dict.fromkeys(self.__slots__, None)
        entries.update((("filename", None), ("location", None)))

        if not options.get("show_file_title", False) and options["show_filename"]:
            if options["absolute_path"]:
                entries["filename"] = self.output.filename
            else:
                entries["filename"] = path_to_rel(self.output.filename)

        sev_map = self.severity_maps.get(options["severity_display"], self.severity_maps["letter"])
        entries["severity"] = sev_map.get(self.severity, sev_map["U"])

        entries["tool"] = self.tool

        number_width = (str(options["number_width"]) if str(options["number_width"]).isdigit()
                        else "0")
        if self.output.start_lincol and self.output.start_lincol[0] != -1:
            entries["location"] = (("{0:" + number_width + "}{1}{2:" + number_width + "}")
                                   .format(self.output.start_lincol[0] + 1,
                                           options["location_column"],
                                           self.output.start_lincol[1] + 1))
            if options["show_location_end"] and self.output.start_lincol != self.output.end_lincol:
                entries["location"] += (("{0}{1:" + number_width + "}{2}{3:" + number_width + "}")
                                        .format(options["location_span"],
                                                self.output.end_lincol[0] + 1,
                                                options["location_column"],
                                                self.output.end_lincol[1] + 1))

        elif self.output.start_pos != -1:
            entries["location"] = ("{0:" + number_width + "}").format(self.output.start_pos + 1)
            if options["show_location_end"] and self.output.start_pos != self.output.end_pos:
                entries["location"] += (("{0}{1:" + number_width + "}")
                                        .format(options["location_span"], self.output.end_pos + 1))

        if len(self.output) != 0:
            entries["output"] = str(self.output).replace("\n", '¶')
            if len(entries["output"]) > options["output_limit"]:
                entries["output"] = entries["output"][:options["output_limit"]]
                entries["output"] += options["output_ellipsis"]

        entries["message"] = self.message

        if options["show_line"] and self.line:
            if (not options["show_marker"] or
                    (not self.line.is_in_span(self.output.start_pos) and
                     not self.line.is_in_span(self.output.end_pos))):
                line_str = str(self.line)
            else:
                before, inner, after = self.line.slice(self.output.start_pos, self.output.end_pos,
                                                       plenary=True)
                if len(inner) == 0:
                    line_str = "".join((str(before), options["marker_both"], str(after)))
                else:
                    line_str = "".join((str(before), options["marker_start"], str(inner),
                                        options["marker_end"], str(after)))

            entries["line"] = line_str.replace('\n', '¶')
            if len(entries["line"]) > options["line_limit"]:
                entries["line"] = entries["line"][:options["line_limit"]]
                entries["line"] += options["line_ellipsis"]

        if (options["show_autofix"] and
                (self.fix is not None or options["show_autofix_always"])):
            entries["fix"] = self.fix_map[self.fix is not None].get(
                                 options["autofix_display"],
                                 self.fix_map[self.fix is not None]["long"])

        return join_entries(entries, options, formatting)

    repr.user_notified = False


    def __repr__(self):
        return self.repr()


    def copy(self):
        """Copy report."""
        return type(self)(self.severity, self.tool, self.output.copy(), self.message,
                          self.line.copy(), self.fix.copy())


# ----------------------------------------------------------------------------

def options_overide(options=None):
    """Override the default print options."""
    if options is None:
        options = config.console_options
        if options is None:
            options = {}

    return {
        "show_file_title": True,
        "absolute_path": False,
        "file_title_ruler": None,
        "compact": False,
        "show_summary": False,
        "summary_ruler": '_',
        **options
    }


def print_reports(reports, options=None, filename_prev=None, is_final=True):
    """Print the reports in the command line."""
    if not reports:
        return filename_prev

    options = options_overide(options)
    if options["sort_key"]:
        key = {
            "severity": lambda report: (report.output.filename, report.severity),
            "tool": lambda report: (report.output.filename, report.tool),
            "start_pos": lambda report: (report.output.filename, report.output.start_pos),
            "start_lincol": lambda report: (report.output.filename, report.output.start_lincol),
            "autofix": lambda report: (report.output.filename, bool(report.fix is None)),
        }
        # fail silently
        if options["sort_key"] in key:
            reports.sort(key=key[options["sort_key"]])

    for report in reports:
        if report is None:
            continue
        filename_prev = print_report(report, options, filename_prev)

    if is_final and options["show_summary"]:
        reports_summary(reports, options)
    return reports[-1].output.filename


def print_report(report, options=None, filename_prev=None):
    """Print a single report. Returns the filename of the report for storage."""
    if report is None:
        return
    if options and options["show_file_title"]:
        if filename_prev is None or filename_prev != report.output.filename:
            print_title(report.output.filename if options["absolute_path"]
                        else path_to_rel(report.output.filename),
                        underline=options["file_title_ruler"])

    print_over(report.repr(options))
    if not options["compact"]:
        print_over()
    return report.output.filename


def reports_summary(reports, options):
    """Show the count of each severity of the reports."""
    summary = dict.fromkeys(Report.severities, 0)
    summary.setdefault("total", 0)

    for report in reports:
        if report.severity in summary.keys():
            summary[report.severity] += 1
        summary["total"] += 1

    summary_text = []
    for key, value in summary.items():
        if key not in {'L', "total"} and (key != 'U' or value != 0):
            sev_map = Report.severity_maps.get(options["severity_display"],
                                               Report.severity_maps["letter"])
            summary_text.append(sev_map.get(key, sev_map["U"]) + ": " + str(value))

    summary_text.append("total" + ": " + str(summary["total"]))

    if options["summary_ruler"]:
        print_over(options["summary_ruler"] * len(", ".join(summary_text)))
    print_over(", ".join(summary_text))
