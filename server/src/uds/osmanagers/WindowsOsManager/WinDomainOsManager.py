# -*- coding: utf-8 -*-

#
# Copyright (c) 2012 Virtual Cable S.L.
# All rights reserved.
#

'''
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''

from django.utils.translation import ugettext_noop as _
from uds.core.ui.UserInterface import gui
from uds.core.managers.CryptoManager import CryptoManager
from uds.core import osmanagers
from WindowsOsManager import WindowsOsManager, scrambleMsg
from uds.core.util import log
import dns.resolver
import ldap

import logging

logger = logging.getLogger(__name__)

class WinDomainOsManager(WindowsOsManager):
    typeName = _('Windows Domain OS Manager')
    typeType = 'WinDomainManager'
    typeDescription = _('Os Manager to control windows machines with domain. (Basically renames machine)')
    iconFile = 'wosmanager.png' 
    
    # Apart form data from windows os manager, we need also domain and credentials
    domain = gui.TextField(length=64, label = _('Domain'), order = 1, tooltip = _('Domain to join machines to (use FQDN form, netbios name not allowed)'), required = True)
    account = gui.TextField(length=64, label = _('Account'), order = 2, tooltip = _('Account with rights to add machines to domain'), required = True)
    password = gui.PasswordField(length=64, label = _('Password'), order = 3, tooltip = _('Password of the account'), required = True)
    ou = gui.TextField(length=64, label = _('OU'), order = 4, tooltip = _('Organizational unit where to add machines in domain (check it before using it)'))
    # Inherits base "onLogout"
    onLogout = WindowsOsManager.onLogout
    
    def __init__(self,environment, values):
        super(WinDomainOsManager, self).__init__(environment, values)
        if values != None:
            if values['domain'] == '':
                raise osmanagers.OSManager.ValidationException(_('Must provide a domain!'))
            if values['domain'].find('.') == -1:
                raise osmanagers.OSManager.ValidationException(_('Must provide domain in FQDN'))
            if values['account'] == '':
                raise osmanagers.OSManager.ValidationException(_('Must provide an account to add machines to domain!'))
            if values['account'].find('\\') != -1:
                raise osmanagers.OSManager.ValidationException(_('DOM\\USER form is not allowed!'))
            if values['password'] == '':
                raise osmanagers.OSManager.ValidationException(_('Must provide a password for the account!'))
            self._domain = values['domain']
            self._ou = values['ou']
            self._account = values['account']
            self._password = values['password']
        else:
            self._domain = ""
            self._ou = ""
            self._account = ""
            self._password = ""
        
        self._ou = self._ou.replace(' ', '')
        if self._domain != '' and self._ou != '':
            lpath = 'dc=' + ',dc='.join(self._domain.split('.'))
            if self._ou.find(lpath) == -1:
                self._ou += ',' + lpath
                
    def __getLdapError(self, e):
        logger.debug('Ldap Error: {0} {1}'.format(e, e.message))
        _str = ''
        if type(e.message) == dict:
            #_str += e.message.has_key('info') and e.message['info'] + ',' or ''
            _str += e.message.has_key('desc') and e.message['desc'] or ''
        else :
            _str += str(e)
        return _str

    def __connectLdap(self):
        '''
        Tries to connect to LDAP
        Raises an exception if not found:
            dns.resolver.NXDOMAIN
            ldap.LDAPError
        '''
        servers = reversed(sorted(dns.resolver.query('_ldap._tcp.'+self._domain, 'SRV'), key=lambda i: i.priority * 10000 + i.weight))
        
        for server in servers:

            _str = ''
            
            try:
                uri = "%s://%s:%d" % ('ldap', str(server.target)[:-1], server.port)
                logger.debug('URI: {0}'.format(uri))
                
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER) # Disable certificate check
                l = ldap.initialize(uri=uri)
                l.set_option(ldap.OPT_REFERRALS, 0)
                l.network_timeout = l.timeout = 5
                l.protocol_version = ldap.VERSION3
                    
                account = self._account
                if account.find('@') == -1:
                    account += '@' + self._domain
                
                logger.debug('Account data: {0}, {1}, {2}, {3}'.format(self._account, self._domain, account, self._password))
                
                l.simple_bind_s(who = account, cred = self._password)
        
                return l
            except ldap.LDAPError as e:
                _str = self.__getLdapError(e)
                    
        raise ldap.LDAPError(_str)

    
    def release(self, service):
        '''
        service is a db user service object
        '''
        super(WinDomainOsManager,self).release(service)
        
        try:
            l = self.__connectLdap()
        except dns.resolver.NXDOMAIN: # No domain found, log it and pass
            logger.warn('Could not find _ldap._tcp.'+self._domain)
            log.doLog(service, log.WARN, "Could not remove machine from domain (_ldap._tcp.{0} not found)".format(self._domain), log.OSMANAGER);
        except ldap.LDAPError as e:
            logger.exception('Ldap Exception caught')
            log.doLog(service, log.WARN, "Could not remove machine from domain (invalid credentials for {0})".format(self._account), log.OSMANAGER);
        
        #_filter = '(&(objectClass=computer)(sAMAccountName=%s$))' % service.friendly_name

        try:
            #  res = l.search_ext_s(base = self._ou, scope = ldap.SCOPE_SUBTREE, 
            #                       filterstr = _filter)[0]
            l.delete('cn={0},{1}'.format(service.friendly_name, self._ou))
        except:
            logger.exception('Not found: ')
        

    def check(self):
        try:
            l = self.__connectLdap()
        except ldap.LDAPError as e:
            return _('Check error: {0}').format(self.__getLdapError(e))
        except dns.resolver.NXDOMAIN:
            return [True, _('Could not find server parameters (_ldap._tcp.{0} can\'r be resolved)').format(self._domain)]
        except Exception as e:
            logger.exception('Exception ')
            return [False, str(e)]
        try:
            r = l.search_st(self._ou, ldap.SCOPE_BASE)
        except ldap.LDAPError as e:
            return _('Check error: {0}').format(self.__getLdapError(e))
            
        
        return _('Server check was successful')
        

    @staticmethod
    def test(env, data):
        logger.debug('Test invoked')
        try:
            wd = WinDomainOsManager(env, data)
            logger.debug(wd)
            try:
                l = wd.__connectLdap()
            except ldap.LDAPError as e:
                return [False, _('Could not access AD using LDAP ({0})').format(wd.__getLdapError(e))]
            
            ou = wd._ou
            if ou == '':
                ou = 'cn=Computers,dc='+',dc='.join(wd._domain.split('.'))
                
            logger.debug('Checking {0} with ou {1}'.format(wd._domain,ou))
            r = l.search_st(ou, ldap.SCOPE_BASE)
            logger.debug('Result of search: {0}'.format(r))
            
        except ldap.LDAPError:
            if wd._ou == '':
                return [False, _('The default path {0} for computers was not found!!!').format(ou)]
            else:
                return [False, _('The ou path {0} was not found!!!').format(ou)]
        except dns.resolver.NXDOMAIN:
            return [True, _('Could not check parameters (_ldap._tcp.{0} can\'r be resolved)').format(wd._domain)]
        except Exception as e:
            logger.exception('Exception ')
            return [False, str(e)]
        
        return [True, _("All parameters seems to work fine.")]

        
    def infoVal(self, service):
        return 'domain:{0}\t{1}\t{2}\t{3}\t{4}'.format( self.getName(service), self._domain, self._ou, self._account, self._password)

    def infoValue(self, service):
        return 'domain\r{0}\t{1}\t{2}\t{3}\t{4}'.format( self.getName(service), self._domain, self._ou, self._account, self._password)
        
    def marshal(self):
        base = super(WinDomainOsManager,self).marshal()
        '''
        Serializes the os manager data so we can store it in database
        '''
        return str.join( '\t', [ 'v1', self._domain, self._ou, self._account, CryptoManager.manager().encrypt(self._password), base.encode('hex') ] ) 
    
    def unmarshal(self, s):
        data = s.split('\t')
        if data[0] == 'v1':
            self._domain = data[1]
            self._ou = data[2]
            self._account = data[3]
            self._password = CryptoManager.manager().decrypt(data[4])
            super(WinDomainOsManager, self).unmarshal(data[5].decode('hex'))
        
    def valuesDict(self):
        dict = super(WinDomainOsManager,self).valuesDict()
        dict['domain'] = self._domain
        dict['ou'] = self._ou
        dict['account'] = self._account
        dict['password'] = self._password
        return dict
    
