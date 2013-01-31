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

from django.utils.translation import ugettext as _
from uds.models import Transport, DeployedService
from uds.core.transports.TransportsFactory import TransportsFactory
from uds.core.ui.UserInterface import gui
from ..util.Helpers import dictFromData
from ..auths.AdminAuth import needs_credentials
from ..util.Exceptions import FindException
from uds.core.Environment import Environment
import logging

logger = logging.getLogger(__name__)

def dictFromTransport(trans):
    return { 
        'id' : str(trans.id), 
        'name' : trans.name, 
        'comments' : trans.comments, 
        'type' : trans.data_type, 
        'typeName' : trans.getInstance().name(),
        'priority' : str(trans.priority),
        'networks' : [  t.name for t in trans.networks.all().order_by('name') ]
    }
    
    
@needs_credentials
def getTransportsTypes(credentials):
    '''
    Returns the types of services providers registered in system
    '''
    res = []
    for type in TransportsFactory.factory().providers().values():
        val = { 'name' : type.name(), 'type' : type.type(), 'description' : type.description(), 'icon' : type.icon() }
        res.append(val)
    return res

@needs_credentials
def getTransports(credentials):
    '''
    Returns the services providers managed (at database)
    '''
    res = []
    for trans in Transport.objects.order_by('priority'):
        try:
            res.append(dictFromTransport(trans))
        except Exception:
            logger.exception("At getTransports: ")
    return res


@needs_credentials
def getTransportGui(credentials, type):
    '''
    Returns the description of an gui for the specified service provider
    '''
    spType = TransportsFactory.factory().lookup(type)
    return spType.guiDescription()

@needs_credentials
def getTransport(credentials, id):
    '''
    Returns the specified service provider (at database)
    '''
    data = Transport.objects.get(pk=id)
    res = [ 
           { 'name' : 'name', 'value' : data.name },
           { 'name' : 'comments', 'value' : data.comments },
           { 'name' : 'priority', 'value' : str(data.priority) },
           { 'name' : 'positiveNet', 'value' : gui.boolToStr(data.nets_positive) },
          ]
    for key, value in data.getInstance().valuesDict().iteritems():
        valtext = 'value'
        if value.__class__ == list:
            valtext = 'values'
        val = {'name' : key, valtext : value }
        res.append(val)
    return res

@needs_credentials
def createTransport(credentials, type, data):
    '''
    Creates a new service provider with specified type and data
    It's mandatory that data contains at least 'name' and 'comments'.
    The expected structure is the same that provided at getServiceProvider
    '''
    dict = dictFromData(data)
    # First create data without serialization, then serialies data with correct environment
    sp = Transport.objects.create(name = dict['name'], comments = dict['comments'], data_type = type, 
                                  priority=int(dict['priority']), nets_positive=gui.strToBool(dict['positiveNet']) )
    sp.data = sp.getInstance(dict).serialize()
    sp.save()
    return str(sp.id)

@needs_credentials
def modifyTransport(credentials, id, data):
    '''
    Modifies an existing service provider with specified id and data
    It's mandatory that data contains at least 'name' and 'comments'.
    The expected structure is the same that provided at getServiceProvider
    '''
    trans = Transport.objects.get(pk=id)
    dict = dictFromData(data)
    sp = trans.getInstance(dict)
    trans.data = sp.serialize()
    trans.name = dict['name']
    trans.comments = dict['comments']
    trans.priority = int(dict['priority'])
    trans.nets_positive = gui.strToBool(dict['positiveNet'])
    trans.save()
    return True
    
@needs_credentials
def removeTransport(credentials, id):
    '''
    Removes from database provider with specified id
    '''
    Transport.objects.get(pk=id).delete()
    return True


# Registers XML RPC Methods
def registerTransportsFunctions(dispatcher):
    dispatcher.register_function(getTransportsTypes, 'getTransportsTypes')
    dispatcher.register_function(getTransports, 'getTransports')
    dispatcher.register_function(getTransportGui, 'getTransportGui')
    dispatcher.register_function(getTransport, 'getTransport')
    dispatcher.register_function(createTransport, 'createTransport')
    dispatcher.register_function(modifyTransport, 'modifyTransport')
    dispatcher.register_function(removeTransport, 'removeTransport')
    
