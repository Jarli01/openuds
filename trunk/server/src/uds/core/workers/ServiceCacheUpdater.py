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
from uds.core.util.Config import GlobalConfig
from uds.core.util.State import State
from uds.core.managers.UserServiceManager import UserServiceManager
from uds.core.services.Exceptions import MaxServicesReachedException
from uds.models import DeployedService
from uds.core import services
from uds.core.jobs.Job import Job
import logging

logger = logging.getLogger(__name__)

            
class ServiceCacheUpdater(Job):
    '''
    Cache updater is responsible of keeping up to date the cache for different deployed services configurations requested
    We only process items that are "cacheables", to speed up process we will use the fact that initialServices = preparedServices = maxServices = 0
    if cache is not needed.
    This is included as a scheduled task that will run every X seconds, and scheduler will keep it so it will be only executed by one backend at a time
    '''
    frecuency = GlobalConfig.CACHE_CHECK_DELAY.getInt() # Request run cache manager every configured seconds. If config value is changed, it will be used at next reload
    
    def __init__(self, environment):
        super(ServiceCacheUpdater,self).__init__(environment)
        
    @staticmethod
    def calcProportion(max, actual):
        return actual * 10000 / max

    def bestDeployedServiceNeedingCacheUpdate(self):
        # State filter for cached and inAssigned objects
        # First we get all deployed services that could need cache generation
        DeployedService.objects.update()
        # We start filtering out the deployed services that do not need caching at all.
        whichNeedsCaching = DeployedService.objects.filter(Q(initial_srvs__gt=0) | Q(cache_l1_srvs__gt=0)).filter(max_srvs__gt=0,state=State.ACTIVE)
        
        # We will get the one that proportionally needs more cache
        selected = None
        cachedL1, cachedL2, assigned = 0,0,0
        toCacheL1 = False # Mark for prefering update L1 cache before L2 cache
        prop = ServiceCacheUpdater.calcProportion(1,1)
        for ds in whichNeedsCaching:
            ds.userServices.update() # Cleans cached queries
            # If this deployedService don't have a publication active and needs it, ignore it
            if ds.activePublication() == None and ds.service.getInstance().publicationType is not None:
                logger.debug('Needs publication but do not have one, cache test ignored')
                continue
            # If it has any running publication, do not generate cache anymore
            if ds.publications.filter(state=State.PREPARING).count() > 0:
                logger.debug('Stopped cache generation for deployed service with publication running: {0}'.format(ds))
                continue
            
            # Get data related to actual state of cache
            inCacheL1 = ds.cachedUserServices().filter(UserServiceManager.getCacheStateFilter(services.UserDeployment.L1_CACHE)).count()
            inCacheL2 = ds.cachedUserServices().filter(UserServiceManager.getCacheStateFilter(services.UserDeployment.L2_CACHE)).count()
            inAssigned = ds.assignedUserServices().filter(UserServiceManager.getStateFilter()).count()
            # if we bypasses max cache, we will reduce it in first place. This is so because this will free resources on service provider
            logger.debug("Examining {0} with {1} in cache L1 and {2} in cache L2, {3} inAssigned".format(
                        ds, inCacheL1, inCacheL2, inAssigned))
            totalL1Assigned = inCacheL1 + inAssigned
            # We have more than we want
            if totalL1Assigned > ds.max_srvs:
                logger.debug('We have more services than max configured')
                cachedL1, cachedL2, assigned = inCacheL1, inCacheL2, inAssigned
                selected = ds
                break
            # We have more in L1 cache than needed
            if totalL1Assigned > ds.initial_srvs and inCacheL1 > ds.cache_l1_srvs:
                logger.debug('We have more services in cache L1 than configured')
                cachedL1, cachedL2, assigned = inCacheL1, inCacheL2, inAssigned
                selected = ds
                break
            
            # If we have more in L2 cache than needed, decrease L2 cache, but int this case, we continue checking cause L2 cache removal 
            # has less priority than l1 creations or removals, but higher. In this case, we will simply take last l2 oversized found and reduce it 
            if inCacheL2 > ds.cache_l2_srvs:
                if toCacheL1 == False:
                    logger.debug('We have more services in L2 cache than configured, decreasing it')
                    cachedL1, cachedL2, assigned = inCacheL1, inCacheL2, inAssigned
                    selected = ds
                    prop = ServiceCacheUpdater.calcProportion(1,0)

            # If this service don't allows more starting user services, continue
            if UserServiceManager.manager().canInitiateServiceFromDeployedService(ds) is False:
                logger.debug('This provider has the max allowed starting services running: {0}'.format(ds))
                continue

            # If wee need to grow l2 cache, annotate it
            # Whe check this before checking the total, because the l2 cache is independent of max services or l1 cache.
            # It reflects a value that must be keeped in cache for futre fast use.
            if inCacheL2 < ds.cache_l2_srvs:
                p = ServiceCacheUpdater.calcProportion(ds.cache_l2_srvs, inCacheL2)
                if p < prop and toCacheL1 == False:
                    logger.debug("Found best for cache until now comparing cache L2: {0}, {1} < {2}".format(ds, p, prop))
                    cachedL1, cachedL2, assigned = inCacheL1, inCacheL2, inAssigned
                    selected = ds
                    prop = p
            
            # We skip it if already at max
            if totalL1Assigned == ds.max_srvs:
                continue;
            
            if totalL1Assigned < ds.initial_srvs:
                p = ServiceCacheUpdater.calcProportion(ds.initial_srvs, totalL1Assigned)
                if p < prop or toCacheL1 == False:
                    logger.debug("Found best for cache until now comparing initial: {0}, {1} < {2}".format(ds, p, prop))
                    toCacheL1 = True
                    cachedL1, cachedL2, assigned = inCacheL1, inCacheL2, inAssigned
                    selected = ds
                    prop = p
            if inCacheL1 < ds.cache_l1_srvs:
                p = ServiceCacheUpdater.calcProportion(ds.cache_l1_srvs, inCacheL1)
                if p < prop or toCacheL1 == False:
                    logger.debug("Found best for cache until now comparing prepared: {0}, {1} < {2}".format(ds, p, prop))
                    toCacheL1 = True
                    selected = ds
                    cachedL1, cachedL2, assigned = inCacheL1, inCacheL2, inAssigned
                    prop = p
                
        # We also return calculated values so we can reuse then
        return selected, cachedL1, cachedL2, assigned
    
    @transaction.autocommit
    def growL1Cache(self, ds, cacheL1, cacheL2, assigned):
        '''
        This method tries to enlarge L1 cache.
        
        If for some reason the number of deployed services (Counting all, ACTIVE
        and PREPARING, assigned, L1 and L2) is over max allowed service deployments,
        this method will not grow the L1 cache
        '''
        logger.debug("Growing L1 cache creating a new service for {0}".format(ds))
        # First, we try to assign from L2 cache
        if cacheL2 > 0:
            cache = ds.cachedUserServices().select_for_update().filter(UserServiceManager.getCacheStateFilter(services.UserDeployment.L2_CACHE)).order_by('creation_date')[0]
            cache.moveToLevel(services.UserDeployment.L1_CACHE)
        else:
            try:
                UserServiceManager.manager().createCacheFor(ds.activePublication(), services.UserDeployment.L1_CACHE)
            except MaxServicesReachedException as e:
                logger.error(str(e))
                # TODO: When alerts are ready, notify this
        
    @transaction.autocommit
    def growL2Cache(self, ds, cacheL1, cacheL2, assigned):
        '''
        Tries to grow L2 cache of service.
        
        If for some reason the number of deployed services (Counting all, ACTIVE
        and PREPARING, assigned, L1 and L2) is over max allowed service deployments,
        this method will not grow the L1 cache
        '''
        logger.debug("Growing L2 cache creating a new service for {0}".format(ds))
        try:
            UserServiceManager.manager().createCacheFor(ds.activePublication(), services.UserDeployment.L2_CACHE)
        except MaxServicesReachedException as e:
            logger.error(str(e))
            # TODO: When alerts are ready, notify this
            
    def reduceL1Cache(self, ds, cacheL1, cacheL2, assigned):
        logger.debug("Reducing L1 cache erasing a service in cache for {0}".format(ds))
        # We will try to destroy the newest cacheL1 element that is USABLE if the deployer can't cancel a new service creation
        cacheItems = ds.cachedUserServices().filter(UserServiceManager.getCacheStateFilter(services.UserDeployment.L1_CACHE)).order_by('-creation_date')
        if len(cacheItems) == 0:
            logger.debug('There is more services than configured, but could not reduce cache cause its already empty')
            return
        
        if cacheL2 < ds.cache_l2_srvs:
            cacheItems[0].moveToLevel(services.UserDeployment.L2_CACHE)
        else:
            # TODO: Look first for non finished cache items and cancel them
            cache = cacheItems[0]
            cache.removeOrCancel()
                
    def reduceL2Cache(self, ds, cacheL1, cacheL2, assigned):
        logger.debug("Reducing L2 cache erasing a service in cache for {0}".format(ds))
        if cacheL2 > 0:
            cacheItems = ds.cachedUserServices().filter(UserServiceManager.getCacheStateFilter(services.UserDeployment.L2_CACHE)).order_by('creation_date')
            # TODO: Look first for non finished cache items and cancel them
            cache = cacheItems[0]
            cache.removeOrCancel()
        
    def run(self):
        logger.debug('Starting cache checking')
        # We need to get
        ds, cacheL1, cacheL2, assigned = self.bestDeployedServiceNeedingCacheUpdate()
        # We have cache to update??
        if ds == None:
            logger.debug('Cache up to date')
            return 
        logger.debug("Updating cache for {0}".format(ds))
        totalL1Assigned = cacheL1 + assigned
        
        # We try first to reduce cache before tring to increase it.
        # This means that if there is excesive number of user deployments
        # for L1 or L2 cache, this will be reduced untill they have good numbers.
        # This is so because service can have limited the number of services and,
        # if we try to increase cache before having reduced whatever needed
        # first, the service will get lock until someone removes something.
        if totalL1Assigned > ds.max_srvs:
            self.reduceL1Cache(ds, cacheL1, cacheL2, assigned)
        elif totalL1Assigned > ds.initial_srvs and cacheL1 > ds.cache_l1_srvs:
            self.reduceL1Cache(ds, cacheL1, cacheL2, assigned)
        elif cacheL2 > ds.cache_l2_srvs: # We have excesives L2 items
            self.reduceL2Cache(ds, cacheL1, cacheL2, assigned)
        elif totalL1Assigned < ds.max_srvs and (totalL1Assigned < ds.initial_srvs or cacheL1 < ds.cache_l1_srvs): # We need more services
            self.growL1Cache(ds, cacheL1, cacheL2, assigned)       
        elif cacheL2 < ds.cache_l2_srvs: # We need more L2 items
            self.growL2Cache(ds, cacheL1, cacheL2, assigned)
        else:
            logger.info("We have more services than max requested for {0}, but can't erase any of then cause all of them are already assigned".format(ds))
