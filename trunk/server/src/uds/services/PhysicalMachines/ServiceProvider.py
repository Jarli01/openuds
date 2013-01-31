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
from uds.core.ui.UserInterface import gui
from uds.core import services


class PhysicalMachinesProvider(services.ServiceProvider):
    # No extra data needed

    # What services do we offer?
    offers = []
    typeName = 'Physical Machines Provider'
    typeType = 'PhysicalMachinesServiceProvider'
    typeDescription = 'Provides connection to Virtual Center Services'
    iconFile = 'provider.png' 

    from IPMachinesService import IPMachinesService
    offers = [IPMachinesService]

    def __init__(self, environment, values = None):
        '''
        Initializes the Physical Machines Service Provider
        @param values: a dictionary with the required values, that are the ones declared for gui 
        '''
        super(PhysicalMachinesProvider, self).__init__(environment, values)
    
    def marshal(self):
        '''
        Serializes the service provider data so we can store it in database
        '''
        return str.join( '\t', [ 'v1' ] ) 
    
    def unmarshal(self, str):
        data = str.split('\t')
        if data[0] == 'v1':
            pass
        
    def __str__(self):
        return "Physical Machines Provider: " +  self.marshal()
