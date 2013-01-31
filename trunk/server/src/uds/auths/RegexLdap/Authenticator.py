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
from django.utils.translation import ugettext_noop as _
from uds.core.ui.UserInterface import gui
from uds.core.auths import Authenticator
import ldap, re

import logging
from uds.core.auths.Exceptions import AuthenticatorException

logger = logging.getLogger(__name__)

LDAP_RESULT_LIMIT = 50

class RegexLdap(Authenticator):
    
    host = gui.TextField(length=64, label = _('Host'), order = 1, tooltip = _('VMWare VC Server IP or Hostname'), required = True)
    port = gui.NumericField(length=5, label = _('Port'), defvalue = '389', order = 2, tooltip = _('Ldap port (389 for non ssl, 636 for ssl normally'), required = True)
    ssl = gui.CheckBoxField(label = _('Use SSL'), order = 3, tooltip = _('If checked, will use a ssl connection to ldap (if port is 389, will use in fact port 636)'))
    username = gui.TextField(length=64, label = _('Ldap User'), order = 4, tooltip = _('Username with read privileges on the base selected'), required = True)
    password = gui.PasswordField(lenth=32, label = _('Password'), order = 5, tooltip = _('Password of the ldap user'), required = True)
    timeout = gui.NumericField(length=3, label = _('Timeout'), defvalue = '10', order = 6, tooltip = _('Timeout in seconds of connection to LDAP'), required = True)
    ldapBase = gui.TextField(length=64, label = _('Base'), order = 7, tooltip = _('Common search base (used for "users" and "groups"'), required = True)
    userClass = gui.TextField(length=64, label = _('User class'), defvalue = 'posixAccount', order = 8, tooltip = _('Class for LDAP users (normally posixAccount)'), required = True)
    userIdAttr = gui.TextField(length=64, label = _('User Id Attr'), defvalue = 'uid', order = 9, tooltip = _('Attribute that contains the user id'), required = True)
    userNameAttr = gui.TextField(length=64, label = _('User Name Attr'), defvalue = 'uid', order = 10, tooltip = _('Attributes that contains the user name (list of comma separated values)'), required = True)
    groupNameAttr = gui.TextField(length=64, label = _('Group Name Attr'), defvalue = 'cn', order = 11, tooltip = _('Attribute that contains the group name'), required = True)
    regex = gui.TextField(length=64, label = _('Regular Exp. for groups'), defvalue = '^(.*)', order = 12, tooltip = _('Regular Expression to extract the group name'), required = True)

    typeName = _('Regex LDAP Authenticator') 
    typeType = 'RegexLdapAuthenticator'
    typeDescription = _('Regular Expressions LDAP authenticator')
    iconFile = 'auth.png' 

    # If it has and external source where to get "new" users (groups must be declared inside UDS)
    isExternalSource = True
    # If we need to enter the password for this user
    needsPassword = False
    # Label for username field
    userNameLabel = _('Username')
    # Label for group field
    groupNameLabel = _("Group")
    # Label for password field
    passwordLabel = _("Password")

    def __init__(self, dbAuth, environment, values = None):
        super(RegexLdap, self).__init__(dbAuth, environment, values)
        if values != None:
            self._host = values['host']
            self._port = values['port']
            self._ssl = gui.strToBool(values['ssl'])
            self._username = values['username']
            self._password = values['password']
            self._timeout = values['timeout']
            self._ldapBase = values['ldapBase']
            self._userClass = values['userClass']
            self._userIdAttr = values['userIdAttr']
            self._groupNameAttr = values['groupNameAttr']
            self._regex = values['regex']
            self._userNameAttr = values['userNameAttr']
            try:
                re.search(self._regex, '')
            except:
                raise Authenticator.ValidationException(_('Invalid regular expression'))
        else:
            self._host = None
            self._port = None
            self._ssl = None
            self._username = None
            self._password = None
            self._timeout = None
            self._ldapBase = None
            self._userClass = None
            self._userIdAttr = None
            self._groupNameAttr = None
            self._regex = None
            self._userNameAttr = None
        self._connection = None
            
    def valuesDict(self):
        return { 'host' : self._host, 'port' : self._port, 'ssl' : gui.boolToStr(self._ssl),
                'username' : self._username, 'password' : self._password, 'timeout' : self._timeout,
                'ldapBase' : self._ldapBase, 'userClass' : self._userClass, 
                'userIdAttr' : self._userIdAttr, 'groupNameAttr' : self._groupNameAttr, 'regex' : self._regex,
                'userNameAttr' : self._userNameAttr
                  }

    def __str__(self):
        return "Ldap Auth: {0}:{1}@{2}:{3}, base = {4}, userClass = {5}, userIdAttr = {6}, groupNameAttr = {7}, reg.ex. = {8}, userName attr = {9}".format(
                self._username, self._password, self._host, self._port, self._ldapBase, self._userClass, self._userIdAttr, self._groupNameAttr, self._regex,
                self._userNameAttr)
    
    def marshal(self):
        return str.join('\t', ['v1', 
                self._host, self._port, gui.boolToStr(self._ssl), self._username, self._password, self._timeout,
                self._ldapBase, self._userClass, self._userIdAttr, self._groupNameAttr, self._regex, self._userNameAttr ])
    
    def unmarshal(self, val):
        data = val.split('\t')
        if data[0] == 'v1':
            logger.debug("Data: {0}".format(data[1:]))
            self._host, self._port, self._ssl, self._username, self._password, self._timeout, self._ldapBase, self._userClass, self._userIdAttr, self._groupNameAttr, self._regex, self._userNameAttr = data[1:]
            self._ssl = gui.strToBool(self._ssl)    
        
    def __connection(self, username = None, password = None):
        if self._connection is None or username is not None: # We want this method also to check credentials
            l = None
            cache = False
            try:
                #ldap.set_option(ldap.OPT_DEBUG_LEVEL, 9)
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
                schema = self._ssl and 'ldaps' or 'ldap'
                port =  self._port != '389' and ':' + self._port or '' 
                uri = "%s://%s%s" % (schema, self._host, port)
                logger.debug('Ldap uri: {0}'.format(uri))
                l = ldap.initialize(uri=uri)
                l.network_timeout = l.timeout = int(self._timeout)
                l.protocol_version = ldap.VERSION3
                
                if username is None:
                    cache = True
                    username = self._username
                    password = self._password
                    
                l.simple_bind_s(who = username, cred = password)
            except ldap.LDAPError, e:
                str_ = _('Ldap connection error: ')
                if type(e.message) == dict:
                    str_ += e.message.has_key('info') and e.message['info'] + ',' or ''
                    str_ += e.message.has_key('desc') and e.message['desc'] or ''
                else :
                    str_ += str(e)
                raise Exception(str_)
            if cache is True:
                self._connection = l
            else:
                return l # Do not cache nor overwrite "global" connection
        return self._connection
    
    def __getUser(self, username):
        try:
            con = self.__connection()
            filter = '(&(objectClass=%s)(%s=%s))' % (self._userClass, self._userIdAttr, username)
            attrlist = self._userNameAttr.split(',') + [self._userIdAttr, self._groupNameAttr]
            logger.debug('Getuser filter: {0}, attr list: {1}'.format(filter, attrlist))
            res = con.search_ext_s(base = self._ldapBase, scope = ldap.SCOPE_SUBTREE, 
                             filterstr = filter, attrlist = attrlist, sizelimit = LDAP_RESULT_LIMIT)[0]
            usr = dict(( k, '' ) for k in attrlist)
            usr.update(res[1])
            usr.update( {'dn' : res[0], '_id' : username })
            logger.debug('Usr: {0}'.format(usr))
            return usr
        except Exception:
            logger.exception('Exception:')
            return None
        
    def __getGroups(self, usr):
        grps = usr[self._groupNameAttr]
        if type(grps) is not list:
            grps = [grps]
        logger.debug("Groups: {0}".format(grps))
        logger.debug("Re: {0}".format(self._regex))
        regex = self._regex
        if regex.find('(') == -1:
            regex = '(' + regex + ')'        
        rg = re.compile(self._regex)
        res = []
        for g in grps:
            ma = rg.search(g)
            if ma is not None:
                for m in ma.groups():
                    res.append(m)
        logger.debug('Res: {0}'.format(res))
        return res
        
    def __getUserRealName(self, usr):
        return ' '.join([ (type(usr.get(id_, '')) is list and ' '.join(( str(k) for k in usr.get(id_, ''))) or str(usr.get(id_, ''))) for id_ in self._userNameAttr.split(',') ]).strip()
            
    def authenticate(self, username, credentials, groupsManager):
        '''
        Must authenticate the user.
        We can have to different situations here:
           1.- The authenticator is external source, what means that users may be unknown to system before callig this
           2.- The authenticator isn't external source, what means that users have been manually added to system and are known before this call
        We receive the username, the credentials used (normally password, but can be a public key or something related to pk) and a group manager.
        The group manager is responsible for letting know the authenticator which groups we currently has active. 
        @see: uds.core.auths.GroupsManager
        '''
        try:
            # Locate the user at LDAP 
            usr = self.__getUser(username)
            
            if usr is None:
                return False
            
            # Let's see first if it credentials are fine
            self.__connection(usr['dn'], credentials) # Will raise an exception if it can't connect
            
            groupsManager.validate(self.__getGroups(usr))
                
            return True
            
        except Exception:
            return False
            
    def createUser(self, usrData):
        '''
        We must override this method in authenticators not based on external sources (i.e. database users, text file users, etc..)
        External sources already has the user  cause they are managed externally, so, it can at most test if the users exists on external source
        before accepting it.
        Groups are only used in case of internal users (non external sources) that must know to witch groups this user belongs to
        @param usrData: Contains data received from user directly, that is, a dictionary with at least: name, realName, comments, state & password 
        @return:  Raises an exception (AuthException) it things didn't went fine 
        '''
        res = self.__getUser(usrData['name'])
        if res is None:
            raise AuthenticatorException(_('Username not found'))
        # Fills back realName field
        usrData['realName'] = self.__getUserRealName(res)


    def getRealName(self, username):
        '''
        Tries to get the real name of an user
        '''
        res = self.__getUser(username)
        if res is None:
            return username
        return self.__getUserRealName(res)
        
    def modifyUser(self, usrData):
        '''
        We must override this method in authenticators not based on external sources (i.e. database users, text file users, etc..)
        Modify user has no reason on external sources, so it will never be used (probably)
        Groups are only used in case of internal users (non external sources) that must know to witch groups this user belongs to
        @param usrData: Contains data received from user directly, that is, a dictionary with at least: name, realName, comments, state & password 
        @return:  Raises an exception it things doesn't go fine 
        '''
        return self.createUser(usrData)
            
    def createGroup(self, groupData):
        '''
        We must override this method in authenticators not based on external sources (i.e. database users, text file users, etc..)
        External sources already has its own groups and, at most, it can check if it exists on external source before accepting it
        Groups are only used in case of internal users (non external sources) that must know to witch groups this user belongs to
        @params groupData: a dict that has, at least, name, comments and active
        @return:  Raises an exception it things doesn't go fine 
        '''
        pass
        
            
    def getGroups(self, username, groupsManager):
        '''
        Looks for the real groups to which the specified user belongs
        Updates groups manager with valid groups
        Remember to override it in derived authentication if needed (external auths will need this, for internal authenticators this is never used)
        '''
        user = self.__getUser(username)
        if user is None:
            raise AuthenticatorException(_('Username not found'))
        groups = self.__getGroups(user)
        for g in groups:
            gg = groupsManager.validate(g)
        
    def searchUsers(self, pattern):
        try:
            con = self.__connection()
            res = []
            for r in con.search_ext_s(base = self._ldapBase, scope = ldap.SCOPE_SUBTREE, filterstr = '(&(objectClass=%s)(%s=%s*))' % (self._userClass, self._userIdAttr, pattern), sizelimit=LDAP_RESULT_LIMIT):
                usrId = r[1].get(self._userIdAttr, '')
                usrId = type(usrId) == list and usrId[0] or usrId
                res.append( { 'id' :   usrId, 
                              'name' : self.__getUserRealName(r[1])  } )
            return res
        except Exception, e:
            logger.exception("Exception: ")
            raise AuthenticatorException(_('Too many results, be more specific'))
            
    @staticmethod
    def test(env, data):
        try:
            auth = RegexLdap(None, env, data)
            return auth.testConnection()
        except Exception, e:
            logger.error("Exception found testing Simple LDAP auth {0}: {1}".format(e.__class__, e))
            return [False, "Error testing connection"]
        
    def testConnection(self):
        try:
            con = self.__connection()
        except Exception, e:
            return [False, str(e)]
        
        try:
            con.search_s(base = self._ldapBase, scope = ldap.SCOPE_BASE)
        except Exception:
            return [False, _('Ldap search base is incorrect')]

        try:
            if len(con.search_ext_s(base = self._ldapBase, scope = ldap.SCOPE_SUBTREE, filterstr = '(objectClass=%s)' % self._userClass, sizelimit=1)) == 1:
                raise Exception()
            return [False, _('Ldap user class seems to be incorrect (no user found by that class)')]
        except Exception, e:
            # If found 1 or more, all right
            pass

        try:
            if len(con.search_ext_s(base = self._ldapBase, scope = ldap.SCOPE_SUBTREE, filterstr = '(objectClass=%s)' % self._groupClass, sizelimit=1)) == 1:
                raise Exception()
            return [False, _('Ldap group class seems to be incorrect (no group found by that class)')]
        except Exception, e:
            # If found 1 or more, all right
            pass

        try:
            if len(con.search_ext_s(base = self._ldapBase, scope = ldap.SCOPE_SUBTREE, filterstr = '(%s=*)' % self._userIdAttr, sizelimit=1)) == 1:
                raise Exception()
            return [False, _('Ldap user id attribute seems to be incorrect (no user found by that attribute)')]
        except Exception, e:
            # If found 1 or more, all right
            pass
        
        try:
            if self._groupNameAttr == 'dn':
                raise Exception() # Can't search entries by dn, so this is not possible and dn is always retrieved
            if len(con.search_ext_s(base = self._ldapBase, scope = ldap.SCOPE_SUBTREE, filterstr = '(%s=*)' % self._groupNameAttr, sizelimit=1)) == 1:
                raise Exception()
            return [False, _('Ldap group id attribute seems to be incorrect (no group found by that attribute)')]
        except Exception, e:
            # If found 1 or more, all right
            pass
        
        # Now test objectclass and attribute of users
        try:
            if len(con.search_ext_s(base = self._ldapBase, scope = ldap.SCOPE_SUBTREE, filterstr = '(&(objectClass=%s)(%s=*))' % (self._userClass, self._userIdAttr), sizelimit=1)) == 1:
                raise Exception()
            return [False, _('Ldap user class or user id attr is probably wrong (can\'t find any user with both conditions)')]
        except Exception as e:
            # If found 1 or more, all right
            pass
            
        # Now try to test regular expression to see if it matches anything (
        try:
            # Check the existence of at least a () grouping
            # Check validity of regular expression (try to compile it)
            # this only right now
            pass
        except Exception as e:
            pass
            
        
        return [True, _("Connection params seem correct, test was succesfully executed")]
    