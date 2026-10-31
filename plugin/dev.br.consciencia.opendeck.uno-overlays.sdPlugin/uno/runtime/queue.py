"""The global job queue: every UNO operation from every device, key, knob and inspector.

Jobs run one at a time in arrival order. Control work (keys, knobs, inspector
edits, slot changes) runs before inspector reads. Numeric ticks for the same
field merge into the job still waiting, unless a later job for that overlay was
queued after it, so a fast knob sends one change per turn instead of one per tick.
"""

import asyncio
import itertools
from collections import deque

__all__ = ["CONTROL", "READ", "Job", "QueueMixin"]

CONTROL, READ = 0, 1


class Job:
    def __init__(self, run, seq, owners=(), token=None, overlay=None, future=None, numeric=None):
        self.run, self.seq = run, seq
        self.owners = set(owners)
        self.token, self.overlay = token, overlay
        self.future, self.numeric = future, numeric
        self.dropped = False


class QueueMixin:
    def _init_queue(self):
        self.queues = (deque(), deque())  # CONTROL, READ
        self.wake = asyncio.Event()
        self.worker = None
        self.serial = itertools.count()
        self.barriers = {}  # (token, overlay or None) -> seq of the last non-numeric job
        self.accumulators = {}  # numeric key -> job still accepting ticks

    def enqueue_job(self, job, priority=CONTROL, barrier=True):
        if job.token is not None and barrier:
            self.barriers[(job.token, job.overlay)] = job.seq
        self.queues[priority].append(job)
        self.wake.set()
        if self.worker is None or self.worker.done():
            self.worker = asyncio.create_task(self.work())
        return job

    def submit(
        self, run, *, owners=(), token=None, overlay=None, priority=CONTROL, future=None, numeric=None, barrier=True
    ):
        job = Job(run, next(self.serial), owners, token, overlay, future, numeric)
        return self.enqueue_job(job, priority, barrier)

    async def run_job(self, run, **options):
        future = asyncio.get_running_loop().create_future()
        self.submit(run, future=future, **options)
        return await future

    async def work(self):
        while True:
            queue = self.queues[CONTROL] or self.queues[READ]
            if not queue:
                self.wake.clear()
                await self.wake.wait()
                continue
            job = queue.popleft()
            if job.dropped:
                continue
            numeric = job.numeric
            if numeric and numeric["phase"] == "update" and self.accumulators.get(numeric["key"]) is job:
                del self.accumulators[numeric["key"]]  # later ticks start a new job
            task = self.spawn(job.run(job))
            await asyncio.wait({task})
            error = None if task.cancelled() else task.exception()
            if numeric and error is not None and self.accumulators.get(numeric["key"]) is job:
                del self.accumulators[numeric["key"]]
            if job.future is not None:
                if not job.future.done():
                    if task.cancelled():
                        job.future.cancel()
                    elif error is not None:
                        job.future.set_exception(error)
                    else:
                        job.future.set_result(task.result())
            elif error is not None:
                for ctx in numeric["deltas"] if numeric else job.owners:
                    await self.report(ctx, error)

    def drop_owner(self, job, ctx):
        """Remove a context from a job that has not started. True when the job is empty."""
        if job.future is not None or job.dropped:
            return False
        if job.numeric:
            if ctx not in job.numeric["deltas"]:
                return False
            del job.numeric["deltas"][ctx]
            if job.numeric["deltas"]:
                return False
            if self.accumulators.get(job.numeric["key"]) is job:
                del self.accumulators[job.numeric["key"]]
            if job.numeric.get("timer"):
                job.numeric["timer"].cancel()
        elif job.owners != {ctx}:
            return False
        job.dropped = True
        return True

    def cancel_context(self, ctx):
        # Queued work of this control is dropped; a job already running finishes.
        for queue in self.queues:
            for job in list(queue):
                if self.drop_owner(job, ctx):
                    queue.remove(job)
        for job in list(self.accumulators.values()):
            self.drop_owner(job, ctx)  # numeric jobs waiting for their Delay
        for key, entry in list(self.timers.items()):
            if entry[0] == ctx:
                entry[1].cancel()
                self.timers.pop(key, None)
        for task in list(self.tasks):
            if getattr(task, "uno_context", None) == ctx:
                task.cancel()

    def mergeable(self, job):
        # Merge only when no later non-numeric job touches this overlay or all
        # overlays. Numeric jobs for other fields are independent of this one.
        return (
            not job.dropped
            and self.barriers.get((job.token, job.overlay), -1) < job.seq
            and self.barriers.get((job.token, None), -1) < job.seq
        )

    def requeue(self, job):
        job.numeric["timer"] = None
        if job.dropped:
            return
        job.seq = next(self.serial)
        self.enqueue_job(job, barrier=False)
