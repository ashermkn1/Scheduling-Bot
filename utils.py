from datetime import datetime
import asyncio


class BotTimer:
    """
    Simple asynchronous timer to facilitate scheduling events
    """
    def __init__(self, timeout, callback, capacity: int=0, args=None, kwargs=None):
        if kwargs is None:
            kwargs = {}
        self.capacity = capacity
        self.args = args
        print(args)
        print(self.args)
        self._kwargs = kwargs
        self._timeout = timeout
        self._start_time = datetime.utcnow()
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    @property
    def remaining(self):
        return self._timeout - self.elapsed

    @property
    def elapsed(self):
        return (datetime.utcnow() - self._start_time).total_seconds()

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback(*self.args, **self._kwargs)

    def cancel(self):
        self._task.cancel()
