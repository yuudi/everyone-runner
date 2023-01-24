import datetime

from apscheduler.schedulers.background import BackgroundScheduler


class ShutdownManager:
    def __init__(self, shutdown_func, inactive_timelimit):
        self.jobs = {}
        self.inactive_timelimit = inactive_timelimit
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.shutdown_func = shutdown_func

    def add_shutdown_job(self, user):
        job = self.scheduler.add_job(
            func=self.shutdown_user,
            args=[user],
            trigger='date',
            run_date=datetime.datetime.now() + datetime.timedelta(seconds=self.inactive_timelimit),
            misfire_grace_time=60,
        )
        self.jobs[user] = job

    def extend_shutdown_job(self, user):
        job = self.jobs.get(user)
        if job is None:
            self.add_shutdown_job(user)
            return
        job.reschedule(
            trigger='date',
            run_date=datetime.datetime.now() + datetime.timedelta(seconds=self.inactive_timelimit),
        )

    def shutdown_user(self, user):
        self.shutdown_func(user)
        del self.jobs[user]
