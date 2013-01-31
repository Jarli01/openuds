# -*- coding: utf-8 -*-

#
# Copyright (c) 2013 Virtual Cable S.L.
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

from uds.models import Log
from uds.core.util import log
from uds.core.util.Config import GlobalConfig
import logging

logger = logging.getLogger(__name__)

OT_USERSERVICE, OT_PUBLICATION, OT_DEPLOYED_SERVICE, OT_SERVICE, OT_PROVIDER, OT_USER, OT_GROUP, OT_AUTHENTICATOR = xrange(8)

class LogManager(object):
    '''
    Manager for logging (at database) events
    '''
    _manager = None
    
    def __init__(self):
        pass
    
    @staticmethod
    def manager():
        if LogManager._manager == None:
            LogManager._manager = LogManager()
        return LogManager._manager
    
    
    # User Service log section
    def __logUserService(self, userService, level, message, source):
        '''
        Logs a message associated to an user service
        '''
        from uds.models import getSqlDatetime
        
        
        qs = Log.objects.filter(owner_id = userService.id, owner_type = OT_USERSERVICE)
        # First, ensure we do not have more than requested logs, and we can put one more log item
        if qs.count() >= GlobalConfig.MAX_LOGS_PER_ELEMENT.getInt():
            for i in qs.order_by('-created',)[GlobalConfig.MAX_LOGS_PER_ELEMENT.getInt()-1:]: i.delete()
            
        # now, we add new log
        Log.objects.create(owner_type = OT_USERSERVICE, owner_id = userService.id, created = getSqlDatetime(), source = source, level = level, data = message)
        
    def __getUserServiceLogs(self, userService, limit):
        '''
        Get all logs associated with an user service, ordered by date
        '''
        qs = Log.objects.filter(owner_id = userService.id, owner_type = OT_USERSERVICE)
        return [{'date': x.created, 'level': x.level, 'source': x.source, 'message': x.data} for x in qs.order_by('created')][:limit]

    
    def doLog(self, wichObject, level, message, source = log.UNKNOWN):
        '''
        Do the logging for the requested object.
        
        If the object provided do not accepts associated loggin, it simply ignores the request
        '''
        from uds.models import UserService
        
        if type(level) is not int:
            level = log.logLevelFromStr(level)
        
        if type(wichObject) is UserService:
            self.__logUserService(wichObject, level, message, source)
        else:
            logger.debug('Requested doLog for a type of object not covered: {0}'.format(wichObject))
            
        
    def getLogs(self, wichObject, limit = GlobalConfig.MAX_LOGS_PER_ELEMENT.getInt()):
        from uds.models import UserService
        
        if type(wichObject) is UserService:
            return self.__getUserServiceLogs(wichObject, limit)
        else:
            logger.debug('Requested getLogs for a type of object not covered: {0}'.format(wichObject))
