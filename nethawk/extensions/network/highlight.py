import re
import os
from rich.console import Console
from rich.text import Text

class NmapHighlighter:
    def __init__(self, console: Console):
        self.console = console
        self.patterns = {
            "key": re.compile(r"\b([A-Z][A-Z_ ]+):"),
            "capslock": re.compile(r"\b[A-Z]{2,}\b"),
            "time": re.compile(r"\b\d{2}:\d{2}(?::\d{2})?\b"),
            "date": re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
            "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
            "domain": re.compile(
                r"\b(?:[a-zA-Z][a-zA-Z0-9+.-]*://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?"
            ),
            "number": re.compile(r"\b\d+(?:\.\d+)?[a-zA-Z]*\b"),
            "proto": re.compile(r"\b\d+/(tcp|udp)\b"),
            "colon_text": re.compile(r": ?([^;:\n]+)(?=;)"),
            "banner_line": re.compile(r"(\|_?banner):\s*(.+)"),
            "header_line": re.compile(r"(\|_?http-server-header):\s*(.+)"),
            "product_version": re.compile(r"\b\w+(?:[-_]\d+[\w\.\-]*)\b"),
            "os": re.compile(r"\b(Ubuntu|Linux|linux)(?:[-_][\w.]+)?\b"),
            "mac": re.compile(r'\b(?:[0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}\b'),
            "hex": re.compile(r"\\x[0-9A-Fa-f]{2}"),
        }

    # def highlight_line(self, line):
    #     text = Text(line)

    #     for name in [
    #         "proto", "number", "ip", "domain",
    #         "capslock", "time", "date", "hex", "os"
    #     ]:
    #         for match in self.patterns[name].finditer(line):
    #             style = {
    #                 "proto": "bold magenta",
    #                 "number": "bold blue1",
    #                 # "colon_text": "bold red",
    #                 "ip": "bold green",
    #                 "domain": "bold magenta",
    #                 "capslock": "purple3",
    #                 # "key": "bold cyan1",
    #                 "time": "bold blue1",
    #                 "date": "bold blue1",
    #                 "hex": "bold green",
    #             }[name]
    #             start, end = match.span(0)
    #             text.stylize(style, start, end)
        
    #     for match in self.patterns["colon_text"].finditer(line):
    #         start, end = match.span(1)
    #         text.stylize("bold red", start, end)

    #     for match in self.patterns["key"].finditer(line):
    #         text.stylize("bold cyan1", match.start(1), match.end(1))  # Only key, not colon

    #     return text
    
    # Highlight a normal single line
    def highlight_line(self, line):
        text = Text(line)

        for match in self.patterns["proto"].finditer(line):
            text.stylize("bold magenta", match.start(), match.end())

        for match in self.patterns["number"].finditer(line):
            text.stylize("bold cyan", match.start(), match.end())

        for match in self.patterns["colon_text"].finditer(line):
            start, end = match.span(1)
            text.stylize("bold red", start, end)

        for match in self.patterns["capslock"].finditer(line):
            text.stylize("bold purple3", match.start(), match.end())

        for match in self.patterns["key"].finditer(line):
            text.stylize("bold cyan1", match.start(1), match.end(1))  # Only key, not colon

        for match in self.patterns["time"].finditer(line):
            text.stylize("bold blue1", match.start(), match.end())

        for match in self.patterns["date"].finditer(line):
            text.stylize("bold blue1", match.start(), match.end())

        for match in self.patterns["hex"].finditer(line):
            text.stylize("bold green", match.start(), match.end())

        for match in self.patterns["os"].finditer(line):
            text.stylize("bold red1", match.start(), match.end())

        for match in self.patterns["ip"].finditer(line):
            text.stylize("bold green", match.start(), match.end())

        for match in self.patterns["mac"].finditer(line):
            text.stylize("bold green", match.start(), match.end())

        for match in self.patterns["domain"].finditer(line):
            text.stylize("bold blue1", match.start(), match.end())

        return text

    def render_banner_block(self, block_lines):
        full_text = "".join(block_lines).replace('\n', '')
        text = Text(full_text)

        for pattern, style in [
            ("product_version", "bold red1"),
            ("os", "bold cyan")
        ]:
            for match in self.patterns[pattern].finditer(full_text):
                text.stylize(style, match.start(), match.end())

        self.console.print(text)

    def render_header_line(self, line):
        text = Text(line)

        match = self.patterns["header_line"].search(line)
        if not match:
            self.console.print(self.highlight_line(line))
            return

        key_start, key_end = match.span(1)
        val_start, val_end = match.span(2)
        text.stylize("white", key_start, key_end)

        val = match.group(2)
        offset = val_start
        for name, style in [
            ("product_version", "bold red1"),
            ("number", "bold red1"),
            ("os", "bold cyan")
        ]:
            for match in self.patterns[name].finditer(val):
                s, e = match.span()
                text.stylize(style, offset + s, offset + e)

        self.console.print(text)

    def process_output(self, lines):
        banner_block = []

        for line in lines:
            line = line.rstrip()

            if re.match(r"\|_?banner:", line):
                if banner_block:
                    self.render_banner_block(banner_block)
                    banner_block = []
                banner_block.append(line)
                continue

            if banner_block:
                if line.startswith("|"):
                    banner_block.append(line)
                    continue
                else:
                    self.render_banner_block(banner_block)
                    banner_block = []

            if re.match(r"\|_?http-server-header:", line):
                self.render_header_line(line)
            else:
                self.console.print(self.highlight_line(line))

        if banner_block:
            self.render_banner_block(banner_block)

# Example usage
# if __name__ == "__main__":
#     console = Console()
#     highlighter = NmapHighlighter(console)
    
#     with open("results.nmap", "r", encoding="utf-8") as f:
#         highlighter.process_output(f)
