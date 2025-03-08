from django_cron import CronJobBase, Schedule
from app.tasks import fetch_electricity_prices, control_shelly_devices  #

class FetchElectricityPricesCronJob(CronJobBase):
    RUN_EVERY_MINS = 60  

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'app.fetch_prices_cron'  

    def do(self):
        fetch_electricity_prices()

class ControlShellyDevicesCronJob(CronJobBase):  # 
    RUN_EVERY_MINS = 61  

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'app.control_shelly_devices_cron'  # 

    def do(self):
        control_shelly_devices()
