from vFense.core.operations._constants import AgentOperations
from vFense.plugins.patching.operations import Install
from vFense.plugins.patching.scheduler.jobs import install_os_apps_in_agents
from vFense.core.scheduler import Schedule
from vFense.core.scheduler._constants import (
    ScheduleKeys, ScheduleTriggers
)
from vFense.core.scheduler.manager import JobManager
from vFense.core.scheduler.status_codes import (
    SchedulerCodes, SchedulerFailureCodes
)
from vFense.core.results import ApiResultKeys

class AgentAppsJobManager(JobManager):
    def install_os_apps_once(self, install, run_date, job_name,
                             time_zone=None):
        """Install 1 or multiple applications to 1 or multiple agents.
        Args:
            install (Install): An instance of Install.
            run_date (float): The unix time, aka epoch time
            job_name (str): The name of this job.

        Kwargs:
            time_zone (str):  Example... UTC, Chile/EasterIsland
        """
        results = {}
        if isinstance(install, Install):
            invalid_fields = install.get_invalid_fields()
            if not invalid_fields:
                install.fill_in_defaults()
                job_kwargs = install.to_dict()
                job = (
                    Schedule(
                        job_name, install_os_apps_in_agents, job_kwargs,
                        run_date=run_date,
                        operation=AgentOperations.INSTALL_OS_APPS,
                        time_zone=time_zone, trigger=ScheduleTriggers.DATE
                    )
                )
                results = self.add_date_job(job)

            else:
                msg = (
                    'Failed to create install job, invalid fields were passed'
                )
                results[ApiResultKeys.GENERIC_STATUS_CODE] = (
                    SchedulerFailureCodes.FailedToCreateObject
                )
                results[ApiResultKeys.VFENSE_STATUS_CODE] = (
                    SchedulerFailureCodes.FailedToCreateSchedule
                )
                results[ApiResultKeys.MESSAGE] = msg
                results[ApiResultKeys.ERRORS] = invalid_fields
                results[ApiResultKeys.DATA] = install.to_dict()

        else:
            msg = (
                'Invalid {0} Instance, must pass an instance of Install.'
                .format(type(install))
            )
            results[ApiResultKeys.GENERIC_STATUS_CODE] = (
                SchedulerFailureCodes.FailedToCreateObject
            )
            results[ApiResultKeys.VFENSE_STATUS_CODE] = (
                SchedulerFailureCodes.FailedToCreateSchedule
            )
            results[ApiResultKeys.MESSAGE] = msg

        return results

    def install_os_apps_for_agent_cron(self, install, job_name, start_date,
                                       year=None, month=None, day=None,
                                       day_of_week=None, hour=None,
                                       minute=None, time_zone=None,
                                       end_date=None):
        """Install 1 or multiple applications to 1 or multiple agents.
        Args:
            install (Install): An instance of Install.
            job_name (str): The name of this job.
            start_date (float): The unix time, aka epoch time

        Kwargs:
            time_zone (str):  Example... UTC, Chile/EasterIsland
            year (int|str): 4-digit year
            month (int|str): month (1-12)
            day (int|str): day of the (1-31)
            week (int|str): ISO week (1-53)
            day_of_week (int|str): number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun)
            hour (int|str): hour (0-23)
            minute (int|str): minute (0-59)
            end_date (float): The unix time, aka epoch time
        """

        results = {}
        if isinstance(install, Install):
            invalid_fields = install.get_invalid_fields()
            if not invalid_fields:
                install.fill_in_defaults()
                job_kwargs = install.to_dict()
                job = (
                    Schedule(
                        job_name, install_os_apps_in_agents, job_kwargs,
                        start_date,
                        operation=AgentOperations.INSTALL_OS_APPS,
                        time_zone=time_zone, trigger=ScheduleTriggers.CRON,
                        year=year, hour=hour, day_of_week=day_of_week,
                        month=month, day=day, minute=minute, end_date=end_date
                    )
                )

                results = self.add_cron_job(job)

            else:
                msg = (
                    'Failed to create install job, invalid fields were passed'
                )
                results[ApiResultKeys.GENERIC_STATUS_CODE] = (
                    SchedulerFailureCodes.FailedToCreateObject
                )
                results[ApiResultKeys.VFENSE_STATUS_CODE] = (
                    SchedulerFailureCodes.FailedToCreateSchedule
                )
                results[ApiResultKeys.MESSAGE] = msg
                results[ApiResultKeys.ERRORS] = invalid_fields
                results[ApiResultKeys.DATA] = install.to_dict()

        else:
            msg = (
                'Invalid {0} Instance, must pass an instance of Install.'
                .format(type(install))
            )
            results[ApiResultKeys.GENERIC_STATUS_CODE] = (
                SchedulerFailureCodes.FailedToCreateObject
            )
            results[ApiResultKeys.VFENSE_STATUS_CODE] = (
                SchedulerFailureCodes.FailedToCreateSchedule
            )
            results[ApiResultKeys.MESSAGE] = msg

        return results