# -*- coding: utf-8 -*-
'''
Created on Nov 17, 2011

@author: dkmaster
'''

from . import renamers
import logging, os

logger = logging.getLogger(__name__)

def rename(newName):
    logger.debug('Debian renamer')
    f = open('/etc/hostname', 'w')
    f.write(newName)
    f.close()
    os.system('/bin/hostname %s' % newName)
    
    # add name to "hosts"
    f = open('/etc/hosts', 'r')
    lines = f.readlines()
    f.close()
    f = open('/etc/hosts', 'w')
    f.write("127.0.1.1\t%s\n" % newName)
    for l in lines:
        if l[:9] == '127.0.1.1':
            continue
        f.write(l)
    f.close()
    
    return True
# All names in lower case
renamers['debian'] = rename
renamers['ubuntu'] = rename