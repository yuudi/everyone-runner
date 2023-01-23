from apscheduler.schedulers.background import BackgroundScheduler

class Scheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def add_job(self, func, *args, **kwargs):
        self.scheduler.add_job(func, *args, **kwargs)

    def remove_job(self, job_id):
        self.scheduler.remove_job(job_id)

    def shutdown(self):
        self.scheduler.shutdown()