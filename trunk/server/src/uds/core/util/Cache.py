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
from uds.models import Cache as dbCache, getSqlDatetime
from datetime import datetime, timedelta
import hashlib
import logging
import cPickle

logger = logging.getLogger(__name__)

class Cache(object):
    DEFAULT_VALIDITY = 60
    CODEC = 'base64'  # Can be zip, hez, bzip, base64, uuencoded
    
    def __init__(self, owner):
        self._owner = owner
        
    
    def __getKey(self, key):
        import os
        h = hashlib.md5()
        h.update(self._owner + key)
        return h.hexdigest()
    
    def get(self,skey, defValue = None):
        now = getSqlDatetime()
        #logger.debug('Requesting key "%s" for cache "%s"' % (skey, self._owner,))
        try:
            key = self.__getKey(skey)
            c = dbCache.objects.get(pk=key)
            expired = now > c.created + timedelta(seconds = c.validity)
            if expired:
                return defValue
            val = cPickle.loads(c.value.decode(Cache.CODEC))
            return val
        except dbCache.DoesNotExist:
            logger.debug('key not found')
            return defValue
        
    def remove(self,skey):
        #logger.debug('Removing key "%s" for uService "%s"' % (skey, self._owner))
        try:
            key = self.__getKey(skey)
            dbCache.objects.get(pk=key).delete()
        except dbCache.DoesNotExist:
            logger.debug('key not found')
    
    @transaction.autocommit
    def put(self, skey, value, validity = None):
        #logger.debug('Saving key "%s" for cache "%s"' % (skey, self._owner,))
        if validity == None:
            validity = Cache.DEFAULT_VALIDITY
        key = self.__getKey(skey)
        value = cPickle.dumps(value).encode(Cache.CODEC)
        now = getSqlDatetime()
        try:
            dbCache.objects.create( owner = self._owner, key = key, value = value, created = now, validity = validity )
        except Exception:
            # Already exists, modify it
            c = dbCache.objects.get(pk=key)
            c.owner = self._owner
            c.key = key
            c.value = value
            c.created = datetime.now()
            c.validity = validity
            c.save()
            
    @transaction.autocommit
    def refresh(self, skey):
        #logger.debug('Refreshing key "%s" for cache "%s"' % (skey, self._owner,))
        try:
            key = self.__getKey(skey)
            c = dbCache.objects.get(pk=key)
            c.created = getSqlDatetime()
            c.save()
        except dbCache.DoesNotExist:
            logger.debug('Can\'t refresh cache key %s because it don\'t exists' % skey)
            return
        
    @staticmethod
    def purge():
        dbCache.objects.all().delete()
        
    @staticmethod
    def cleanUp():
        dbCache.cleanUp()

    @staticmethod
    def delete(owner = None):
        #logger.info("Deleting cache items")
        if owner == None:
            objects = dbCache.objects.all()
        else:
            objects = dbCache.objects.filter(owner=owner)
        objects.delete()
    
