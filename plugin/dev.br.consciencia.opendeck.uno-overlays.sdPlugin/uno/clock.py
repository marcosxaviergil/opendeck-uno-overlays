"""One text-field clock: vMix countdown functions with stagetimer appearances.

Pure state machine: every method takes the current monotonic time, nothing here
touches UNO, so the rules are testable on their own. Sources: vMix Shortcut
Function Reference (countdown functions) and stagetimer "Using Timers Correctly".
"""

import math
import time

from uno.api import UnoError
from uno.i18n import tr
from uno.images import RED, WHITE, WRAP_UP
from uno.values import format_clock, parse_hms

__all__ = ["Clock", "until_left"]

FLASHES = {"1": 1, "2": 2, "3": 3, "inf": math.inf}  # stagetimer: 1, 2 or 3 times, or until it stops


class Clock:
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.duration = parse_hms(cfg.get("duration"))
        self.running = self.done = self.auto = False  # auto: paused by "pause while off air"
        self.elapsed = self.since = 0.0
        self.flash_start = self.flash_until = 0.0
        # Writer bookkeeping: the key that runs it, text last written, a write in flight, a change to write.
        self.owner, self.written, self.busy, self.dirty = None, None, False, True

    @property
    def mode(self):
        return self.cfg.get("mode") or "countdown"

    def apply(self, operation, value, now):
        """vMix countdown functions. StartCountdown is undocumented: it starts or resumes, and after
        completion starts from the beginning, as PauseCountdown documents."""
        if operation == "start":
            if self.done:
                self._reset()
            if not self.running:
                self._run(now)
        elif operation == "pause":  # PauseCountdown: pause or resume, or if complete start from beginning
            if self.done:
                self._reset()
                self._run(now)
            elif self.running:
                self._suspend(now)
            else:
                self._run(now)
        elif operation == "suspend":  # SuspendCountdown: pause only
            self._suspend(now)
        elif operation == "stop":  # StopCountdown: stop and reset
            self._reset()
        elif operation == "set":  # SetCountdown: duration as hh:mm:ss
            self.duration = parse_hms(value)
        elif operation in ("change", "adjust"):  # ChangeCountdown: hh:mm:ss / AdjustCountdown: ± seconds
            self._move(operation, value, now)
        else:
            raise UnoError(tr("Unsupported clock function."))
        if not (self.running and self.done):
            self.flash_until = 0.0  # stagetimer: flashing lasts until the timer stops
        self.dirty = True

    def seconds(self, now):
        """(seconds to show, time is up). Negative = overtime."""
        elapsed = self.elapsed + (now - self.since if self.running else 0)
        if self.mode == "countup":
            return elapsed, self.duration > 0 and elapsed >= self.duration
        if self.mode == "until" and not (self.running or self.elapsed):
            return until_left(self.cfg), False  # not started: time left until the finish time
        if self.mode == "timeofday":
            return 0, False
        return self.duration - elapsed, self.duration - elapsed <= 0

    def text(self, now):
        fmt = self.cfg.get("format") or "mm:ss"
        if self.mode == "timeofday":
            return time.strftime("%H:%M:%S" if fmt == "hh:mm:ss" else "%H:%M")
        value, _ = self.seconds(now)
        if self.cfg.get("overtime") == "stop":
            value = max(0, value) if self.mode != "countup" else min(value, self.duration or value)
        shown = math.floor(value) if self.mode == "countup" else math.ceil(value)  # whole seconds left
        return format_clock(shown, fmt, "+" if self.cfg.get("overtimeSign") == "+" else "-")

    def color(self, now):
        """stagetimer wrap-up colors when yellow/red times are set; else red while running."""
        yellow, red = parse_hms(self.cfg.get("yellowAt")), parse_hms(self.cfg.get("redAt"))
        if self.mode in ("countdown", "until") and (yellow or red):
            left, done = self.seconds(now)
            normal, warning, last = WRAP_UP
            return last if done or left <= red else warning if left <= yellow else normal
        return RED if self.running else WHITE

    def hidden(self, now):
        """True during the "off" half of each flash second."""
        return now < self.flash_until and (now - self.flash_start) % 1 >= 0.5

    def complete(self, now):
        """True once when the time is up (vMix OnCountdownCompleted); starts the flash."""
        if not self.running or self.done or not self.seconds(now)[1]:
            return False
        self.done = True
        if self.cfg.get("overtime") == "stop":
            self.running, self.elapsed, self.dirty = False, self.duration, True
        self.flash_start, self.flash_until = now, now + FLASHES.get(self.cfg.get("flash"), 0)
        return True

    def follow_air(self, on_air, now):
        """Optional: pause while the overlay is off air, resume when it is back on air."""
        if self.running and not on_air:
            self._suspend(now)
            self.auto = True
        elif self.auto and on_air:
            self.running, self.since, self.auto = True, now, False

    def active(self, now):
        """Needs the writer: running, waiting to resume, flashing or with an unwritten change."""
        return self.running or self.auto or now < self.flash_until or self.dirty

    def _suspend(self, now):
        if self.running:
            self.running, self.elapsed = False, self.elapsed + now - self.since

    def _reset(self):
        self.running, self.elapsed, self.done, self.auto = False, 0.0, False, False

    def _run(self, now):
        if self.mode == "until" and not self.elapsed:  # stagetimer: duration calculated when it starts
            self.duration = until_left(self.cfg)
        self.running, self.since = True, now

    def _move(self, operation, value, now):
        was_running = self.running
        self._suspend(now)
        shown = self.seconds(now)[0]
        target = parse_hms(value) if operation == "change" else shown + float(value or 0)
        if self.mode == "until" and not self.elapsed:
            self.duration = shown
        if self.mode == "countup":
            self.elapsed = target
        elif self.mode != "timeofday":
            self.elapsed = self.duration - target
        self.done = False
        if was_running:
            self.running, self.since = True, now


def until_left(cfg):
    """Seconds from now to the "ends at" time of day (HH:MM or HH:MM:SS), today."""
    today = time.localtime()
    midnight = time.mktime(today[:3] + (0, 0, 0) + today[6:])
    until = str(cfg.get("until") or "").strip()
    return midnight + parse_hms(until + ":00" if until.count(":") == 1 else until) - time.time()
