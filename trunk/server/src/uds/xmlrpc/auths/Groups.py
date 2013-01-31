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

from uds.models import Group, Authenticator, State
from django.db import IntegrityError
from ..util.Exceptions import DuplicateEntryException, InsertException
from uds.core.auths.Exceptions import AuthenticatorException
from AdminAuth import needs_credentials
import logging

logger = logging.getLogger(__name__)

def dictFromGroup(grp):
    state = True if grp.state == State.ACTIVE else False
    return { 'idParent' : str(grp.manager.id), 'nameParent': grp.manager.name,  'id' : str(grp.id), 'name' : grp.name, 
                    'comments' : grp.comments, 'active' :  state }

def getRealGroups(idParent):
    auth = Authenticator.objects.get(pk=idParent)
    res = []
    for grp in auth.groups.order_by('name'):
        try:
            res.append(dictFromGroup(grp))
        except Exception, e:
            logger.debug(e)
    return res

@needs_credentials
def getGroups(credentials, idParent):
    '''
    Returns the groups contained at idParent authenticator
    '''
    return getRealGroups(idParent)

@needs_credentials
def getGroup(__, id_):
    '''
    '''
    grp = Group.objects.get(pk=id_)
    return dictFromGroup(grp)

@needs_credentials
def createGroup(credentials, grp):
    '''
    Creates a new group associated with an authenticator
    '''
    auth = Authenticator.objects.get(pk=grp['idParent'])
    state = State.ACTIVE if grp['active'] == True else State.INACTIVE
    try:
        authInstance = auth.getInstance()
        authInstance.createGroup(grp) # Remenber, this throws an exception if there is an error
        auth.groups.create(name = grp['name'], comments = grp['comments'], state = state)
    except IntegrityError:
        raise DuplicateEntryException(grp['name'])
    except AuthenticatorException, e:
        logger.debug(e)
        raise InsertException(str(e))
    return True

@needs_credentials
def removeGroups(credentials, ids):
    '''
    Deletes a group
    '''
    Group.objects.filter(id__in=ids).delete()
    return True
    
@needs_credentials
def changeGroupsState(credentials, ids, newState):
    '''
    Changes the state of the specified group
    '''
    state = State.ACTIVE if newState == True else State.INACTIVE
    Group.objects.filter(id__in=ids).update(state = state)
    return True

# Registers XML RPC Methods
def registerGroupsFunctions(dispatcher):
    dispatcher.register_function(getGroups, 'getGroups')
    dispatcher.register_function(getGroup, 'getGroup')
    dispatcher.register_function(createGroup, 'createGroup')
    dispatcher.register_function(removeGroups, 'removeGroups')
    dispatcher.register_function(changeGroupsState, 'changeGroupsState')
    