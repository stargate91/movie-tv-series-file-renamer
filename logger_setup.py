import sys
import os
from datetime import datetime

def setup_logging(log_dir="logs"):
    class Logger:
        def __init__(self, console, logfile):
            self.console = console
            self.logfile = logfile
            self.buffer_console = ""
            self.buffer_file = ""

        def write(self, text):
            self.buffer_console += text
            self.buffer_file += text
            while "\n" in self.buffer_console:
                line_console, self.buffer_console = self.buffer_console.split("\n", 1)
                line_file, self.buffer_file = self.buffer_file.split("\n", 1)

                self.console.write(line_console + "\n")
                self.console.flush()

                timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
                self.logfile.write(timestamp + line_file + "\n")
                self.logfile.flush()

        def flush(self):
            if self.buffer_console:
                self.console.write(self.buffer_console)
                self.console.flush()
                self.buffer_console = ""

            if self.buffer_file:
                timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
                self.logfile.write(timestamp + self.buffer_file)
                self.logfile.flush()
                self.buffer_file = ""

    os.makedirs(log_dir, exist_ok=True)
    log_filename = datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.txt")
    log_path = os.path.join(log_dir, log_filename)
    log_file = open(log_path, "w", encoding="utf-8")

    sys.stdout = Logger(sys.stdout, log_file)
    sys.stderr = Logger(sys.stderr, log_file)
