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

from django.db import transaction
from django.db.models import Q
from uds.models import DelayedTask as dbDelayedTask
from uds.core.util.Decorators import retryOnException
from ..Environment import Environment
from socket import gethostname
from pickle import loads, dumps
from datetime import datetime, timedelta
import threading, time
import logging

logger = logging.getLogger(__name__)

class DelayedTaskThread(threading.Thread):
    def __init__(self, taskInstance):
        super(DelayedTaskThread,self).__init__()
        self._taskInstance = taskInstance
        
    def run(self):
        try:
            self._taskInstance.execute()
        except Exception, e:
            logger.debug("Exception in thread {0}: {1}".format(e.__class__, e))

class DelayedTaskRunner(object):
    CODEC = 'base64'  # Can be zip, hez, bzip, base64, uuencoded
    # How often tasks r checked
    granularity = 2
    
    # to keep singleton DelayedTaskRunner
    _runner = None
    
    def __init__(self):
        logger.debug("Initializing delayed task runner")
        self._hostname = gethostname()
        self._keepRunning = True
    
    def notifyTermination(self):
        self._keepRunning = False
    
    @staticmethod
    def runner():
        if DelayedTaskRunner._runner  == None:
            DelayedTaskRunner._runner = DelayedTaskRunner()
        return DelayedTaskRunner._runner

    @transaction.commit_manually
    def executeOneDelayedTask(self):
        now = datetime.now()
        filt = Q(execution_time__lt=now) | Q(insert_date__gt=now)
        # If next execution is before now or last execution is in the future (clock changed on this server, we take that task as executable)
        taskInstance = None
        try:
            task = dbDelayedTask.objects.select_for_update().filter(filt).order_by('execution_time')[0]
            task.delete()
            transaction.commit()
            taskInstance = loads(task.instance.decode(self.CODEC))
        except Exception:
            # No task waiting, nice
            transaction.rollback()
        
        if taskInstance != None:
            env = Environment.getEnvForType(taskInstance.__class__)
            taskInstance.setEnv(env)
            DelayedTaskThread(taskInstance).start()

    @transaction.commit_on_success
    def __insert(self, instance, delay, tag):
        now = datetime.now()
        exec_time = now + timedelta(seconds = delay)
        cls = instance.__class__
        dbDelayedTask.objects.create(type = str(cls.__module__ + '.' + cls.__name__), instance = dumps(instance).encode(self.CODEC), 
                                         insert_date = now, execution_delay = delay, execution_time = exec_time, tag = tag)

    def insert(self, instance, delay, tag = ''):
        retries = 3
        while retries > 0:
            retries -= 1
            try:
                self.__insert(instance, delay, tag)
                break
            except Exception, e:
                logger.info('Exception inserting a delayed task {0}: {1}'.format(str(e.__class__), e))
        # If retries == 0, this is a big error
        if retries == 0:
            logger.error("Could not insert delayed task!!!! {0} {1} {2}".format(instance, delay, tag))
            return False
        return True
            
    @transaction.commit_on_success
    def remove(self, tag):
        try:
            dbDelayedTask.objects.select_for_update().filter(tag=tag).delete()
        except Exception as e:
            logger.exception('Exception removing a delayed task {0}: {1}'.format(str(e.__class__), e))
            
    @transaction.commit_on_success
    def checkExists(self, tag):
        number = 0
        try:
            number = dbDelayedTask.objects.filter(tag=tag).count()
        except Exception as e:
            logger.error('Exception looking for a delayed task tag {0}'.format(tag))
        return number > 0

    def run(self):
        logger.debug("At loop")
        while self._keepRunning:
            try:
                time.sleep(self.granularity)
                self.executeOneDelayedTask()
            except Exception, e:
                logger.error('Unexpected exception at run loop {0}: {1}'.format(e.__class__, e))
