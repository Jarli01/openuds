# -*- coding: utf-8 -*-

#
# Copyright (c) 2012 Virtual Cable S.L.
# All rights reserved.
#

'''
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''

from django.utils.translation import ugettext_noop as _
from uds.core.osmanagers.OSManagersFactory import OSManagersFactory
from uds.core.managers.DownloadsManager import DownloadsManager
from WindowsOsManager import WindowsOsManager
from WinDomainOsManager import WinDomainOsManager
from WinRandomPassOsManager import WinRandomPassManager
import os.path, sys

OSManagersFactory.factory().insert(WindowsOsManager)
OSManagersFactory.factory().insert(WinDomainOsManager)
OSManagersFactory.factory().insert(WinRandomPassManager)

DownloadsManager.manager().registerDownloadable('UDSActorSetup.exe', 
                                                _('UDS Actor for windows machines <b>(Important!! Requires .net framework 3.5 sp1)</b>'),
                                                os.path.dirname(sys.modules[__package__].__file__) + '/files/UDSActorSetup.exe', 
                                                'application/x-msdos-program')
