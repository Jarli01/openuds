# -*- coding: utf-8 -*-

#
# Copyright (c) 2012 Virtual Cable S.L.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice, 
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice, 
#      this list of conditions and the following disclaimer in the documentation 
#      and/or other materials provided with the distribution.
#    * Neither the name of Virtual Cable S.L. nor the names of its contributors 
#      may be used to endorse or promote products derived from this software 
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE 
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''
from uds.core.jobs.Scheduler import Scheduler
from uds.core.jobs.DelayedTaskRunner import DelayedTaskRunner
from uds.core import jobs
from uds.core.util.Config import GlobalConfig
import threading, time, signal
import logging

logger = logging.getLogger(__name__)

class SchedulerThread(threading.Thread):
    def run(self):
        Scheduler.scheduler().run()
        
    def notifyTermination(self):
        Scheduler.scheduler().notifyTermination()

class DelayedTaskThread(threading.Thread):
    def run(self):
        DelayedTaskRunner.runner().run()

    def notifyTermination(self):
        DelayedTaskRunner.runner().notifyTermination()


class TaskManager(object):
    keepRunning = True
    
    @staticmethod
    def sigTerm(sigNum, frame):
        '''
        This method will ensure that we finish correctly current running task before exiting.
        If we need to stop cause something went wrong (that should not happen), we must send sigterm, wait a while (10-20 secs) and after that send sigkill
        kill task
        sleep 10
        kill -9 task
        Take a look at killTaskManager.sh :-)
        '''
        logger.info("Caught term signal, finishing task manager")
        TaskManager.keepRunning = False
    
    @staticmethod
    def registerJob(jobName, jobType):
        jobs.factory().insert(jobName, jobType)
    
    
    @staticmethod
    def registerScheduledTasks():
        from uds.core.workers.ServiceCacheUpdater import ServiceCacheUpdater
        from uds.core.workers.UserServiceCleaner import UserServiceInfoItemsCleaner, UserServiceRemover
        from uds.core.workers.PublicationCleaner import PublicationInfoItemsCleaner, PublicationCleaner
        from uds.core.workers.CacheCleaner import CacheCleaner
        from uds.core.workers.DeployedServiceCleaner import DeployedServiceInfoItemsCleaner, DeployedServiceRemover
        from uds.core.workers.StatsCollector import DeployedServiceStatsCollector

        logger.info("Registering sheduled tasks")
        TaskManager.registerJob('Service Cache Updater', ServiceCacheUpdater)
        TaskManager.registerJob('User Service Info Cleaner', UserServiceInfoItemsCleaner)
        TaskManager.registerJob('User Service Cleaner', UserServiceRemover)
        TaskManager.registerJob('Publications Info Cleaner', PublicationInfoItemsCleaner)
        TaskManager.registerJob('Publication Cleaner', PublicationCleaner)
        TaskManager.registerJob('Utility Cache Cleaner', CacheCleaner)
        TaskManager.registerJob('Deployed Service Info Cleaner', DeployedServiceInfoItemsCleaner)
        TaskManager.registerJob('Deployed Service Cleaner', DeployedServiceRemover)
        TaskManager.registerJob('Deployed Service Stats', DeployedServiceStatsCollector)
    
    
    @staticmethod
    def run():
        TaskManager.keepRunning = True
        # Runs Scheduler in a separate thread and DelayedTasks here
        
        noSchedulers = GlobalConfig.SCHEDULER_THREADS.getInt()
        noDelayedTasks = GlobalConfig.DELAYED_TASKS_THREADS.getInt()
        
        threads = []
        for n in range(noSchedulers):
            thread = SchedulerThread()
            thread.start()
            threads.append(thread)
            time.sleep(0.5)
            
        for n in range(noDelayedTasks):
            thread = DelayedTaskThread()
            thread.start()
            threads.append(thread)
            time.sleep(1)
            
        signal.signal(signal.SIGTERM, TaskManager.sigTerm)
        
        
        # Debugging stuff
        #import guppy
        #from guppy.heapy import Remote
        #Remote.on()

        #gc.set_debug(gc.DEBUG_LEAK)
        while( TaskManager.keepRunning ):
            time.sleep(1)
            
        for thread in threads:
            thread.notifyTermination()

        # The join of threads will happen before termination, so its fine to just return here
        
