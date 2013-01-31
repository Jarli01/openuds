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

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from uds.core.auths.auth import getIp, webLogin, webLogout, webLoginRequired, authenticate, webPassword, authenticateViaCallback
from uds.models import Authenticator, DeployedService, Transport, UserService, Network
from uds.web.forms.LoginForm import LoginForm
from uds.core.managers.UserServiceManager import UserServiceManager
from uds.core.managers.UserPrefsManager import UserPrefsManager
from uds.core.managers.DownloadsManager import DownloadsManager
from uds.core.util.Config import GlobalConfig
from uds.core.util.Cache import Cache
from uds.core.util import OsDetector
from transformers import transformId, scrambleId
import errors
import logging
import random
import string

logger = logging.getLogger(__name__)
authLogger = logging.getLogger('__authLog')

def __authLog(request, authenticator, userName, java, os, log):
    '''
    Logs authentication
    '''
    javaStr = java and 'Java' or 'No Java'
    authLogger.info('|'.join([authenticator.name, userName, javaStr, os['OS'], log, request.META['HTTP_USER_AGENT']]))

def login(request):
    #request.session.set_expiry(GlobalConfig.USER_SESSION_LENGTH.getInt()) 
    if request.method == 'POST':
        if request.COOKIES.has_key('uds') is False:
            return errors.errorView(request, errors.COOKIES_NEEDED) # We need cookies to keep session data
        form = LoginForm(request.POST)
        if form.is_valid():
            java = form.cleaned_data['java'] == 'y'
            os = OsDetector.getOsFromUA(request.META['HTTP_USER_AGENT'])
            authenticator = Authenticator.objects.get(pk=form.cleaned_data['authenticator'])
            userName = form.cleaned_data['user']
            
            cache = Cache('auth')
            cacheKey = str(authenticator.id) + userName
            tries = cache.get(cacheKey)
            if tries is None:
                tries = 0
            if tries >= GlobalConfig.MAX_LOGIN_TRIES.getInt():
                form.add_form_error('Too many authentication errors. User temporarily  blocked.')
                __authLog(request, authenticator, userName, java, os, 'Temporarily blocked')
            else:
                user = authenticate(userName, form.cleaned_data['password'], authenticator )
                    
                if user is None:
                    logger.debug("Invalid credentials for user {0}".format(userName))
                    tries += 1
                    cache.put(cacheKey, tries, GlobalConfig.LOGIN_BLOCK.getInt())
                    form.add_form_error('Invalid credentials')
                    __authLog(request, authenticator, userName, java, os, 'Invalid credentials')
                else:
                    cache.remove(cacheKey) # Valid login, remove cached tries
                    response = HttpResponseRedirect(reverse('uds.web.views.index'))
                    webLogin(request, response, user, form.cleaned_data['password'])
                    # Add the "java supported" flag to session
                    request.session['java'] = java
                    request.session['OS'] = os
                    logger.debug('Navigator supports java? {0}'.format(java))
                    __authLog(request, authenticator, user.name, java, os, 'Logged in')
                    return response
    else:
        form = LoginForm()
        
    response = render_to_response('uds/login.html', { 'form' : form, 'customHtml' : GlobalConfig.CUSTOM_HTML_LOGIN.get(True) }, 
                                  context_instance=RequestContext(request))
    if request.COOKIES.has_key('uds') is False:
        response.set_cookie('uds', ''.join(random.choice(string.letters + string.digits) for _ in xrange(32)))
    return response    

def customAuth(request, idAuth):
    res = ''
    try:
        getIp(request)
        a = Authenticator.objects.get(pk=idAuth).getInstance()
        res = a.getHtml(request)
        if res is None:
            res = ''
    except Exception:
        logger.exception('customAuth')
        res = 'error'
    return HttpResponse(res, content_type = 'text/html')

@webLoginRequired
def logout(request):
    return webLogout(request, request.user.logout())

@webLoginRequired
def index(request):
    # Session data
    os = request.session['OS']
    java = request.session['java']
    
    # We look for services for this authenticator groups. User is logged in in just 1 authenticator, so his groups must coincide with those assigned to ds
    groups = request.user.groups.all()
    availServices = DeployedService.getDeployedServicesForGroups(groups)
    availUserServices = UserService.getUserAssignedServices(request.user)
    
    # Information for administrators
    nets = ''
    validTrans = ''
    
    if request.user.isStaff():
        nets = ','.join( [ n.name for n in Network.networksFor(request.ip) ])
        tt = []
        for t in Transport.objects.all():
            if t.validForIp(request.ip):
                tt.append(t.name)
        validTrans = ','.join(tt)


    # Extract required data to show to user
    services = []
    # Select assigned user services
    for svr in availUserServices:
        trans = []
        for t in svr.transports.all().order_by('priority'):
            if t.validForIp(request.ip):
                trans.append({ 'id' : scrambleId(request, t.id), 'name' : t.name, 'needsJava' : t.getType().needsJava })
        services.append( {'id' : scrambleId(request, 'a' + str(svr['id'])), 'name': svr['name'], 'transports' : trans } )
        
    # Now generic user service
    for svr in availServices:
        trans = []
        for t in svr.transports.all().order_by('priority'):
            if t.validForIp(request.ip):
                typeTrans = t.getType()
                if typeTrans.supportsOs(os['OS']):
                    trans.append({ 'id' : scrambleId(request, t.id), 'name' : t.name, 'needsJava' : typeTrans.needsJava  })
        services.append( {'id' : scrambleId(request, 'd' + str(svr.id)), 'name': svr.name, 'transports' : trans } )
        
    logger.debug('Services: {0}'.format(services))
    
    if len(services) == 1 and GlobalConfig.AUTORUN_SERVICE.get() == '1' and len(services[0]['transports']) > 0:
        if request.session.get('autorunDone', '0') == '0':
            request.session['autorunDone'] = '1'
            return HttpResponseRedirect( 
                     reverse('uds.web.views.service', kwargs={ 'idService': services[0]['id'],
                                                        'idTransport' : services[0]['transports'][0]['id'] } 
                             ) 
                   )
            
    
    return render_to_response('uds/index.html', 
                              {'services' : services, 'java' : java, 'ip' : request.ip, 'nets' : nets,
                                'transports' : validTrans }, 
                              context_instance=RequestContext(request))

@webLoginRequired
def prefs(request):
    if request.method == 'POST':
        UserPrefsManager.manager().processRequestForUserPreferences(request.user, request.POST)
        return HttpResponseRedirect(reverse('uds.web.views.index'))
    prefs_form = UserPrefsManager().manager().getHtmlForUserPreferences(request.user)
    return render_to_response('uds/prefs.html', {'prefs_form' : prefs_form }, context_instance=RequestContext(request))
    

@webLoginRequired
@transformId
def service(request, idService, idTransport):
    kind, idService = idService[0], idService[1:]
    try:
        logger.debug('Kind of service: {0}, idService: {1}'.format(kind, idService))
        if kind == 'a': # This is an assigned service
            ads = UserService.objects.get(pk=idService)
        else:
            ds = DeployedService.objects.get(pk=idService)
            # We first do a sanity check for this, if the user has access to this service
            # If it fails, will raise an exception
            ds.validateUser(request.user)
            # Now we have to locate an instance of the service, so we can assign it to user.
            ads = UserServiceManager.manager().getAssignationForUser(ds, request.user)
        logger.debug('Found service: {0}'.format(ads))
        trans = Transport.objects.get(pk=idTransport)
        # Test if the service is ready
        if ads.isReady():
            logger.debug('Ads is Ready')
            # If ready, show transport for this service, if also ready ofc
            iads = ads.getInstance()
            ip = iads.getIp()
            if ip is not None:
                itrans = trans.getInstance()
                if itrans.isAvailableFor(ip):
                    transport = itrans.renderForHtml(ads, scrambleId(request, ads.id), scrambleId(request, trans.id), ip, request.session['OS'], request.user, webPassword(request))
                    return render_to_response('uds/show_transport.html', {'transport' : transport, 'nolang' : True }, context_instance=RequestContext(request))
                else:
                    logger.debug('Transport is not ready for user service {0}'.format(ads))
            else:
                logger.debug('Ip not available from user service {0}'.format(ads))
        # Not ready, show message and return to this page in a while
        return render_to_response('uds/service_not_ready.html', context_instance=RequestContext(request))
    except Exception, e:
        logger.exception("Exception")
        return errors.exceptionView(request, e)
    
@webLoginRequired
@transformId
def transcomp(request, idTransport, componentId):
    try:
        # We got translated first id
        trans = Transport.objects.get(pk=idTransport)
        itrans = trans.getInstance()
        res = itrans.getHtmlComponent(scrambleId(request, trans.id), request.session['OS'], componentId)
        response = HttpResponse(res[1], mimetype=res[0])
        response['Content-Length'] = len(res[1])
        return response
    except Exception, e:
        return errors.exceptionView(request, e)

@webLoginRequired
@transformId
def sernotify(request, idUserService, notification):
    try:
        if notification == 'hostname':
            hostname = request.GET.get('hostname', None)
            ip = request.GET.get('ip', None)
            if ip is not None and hostname is not None:
                us = UserService.objects.get(pk=idUserService)
                us.setConnectionSource(ip, hostname)
            else:
                return HttpResponse('Invalid request!', 'text/plain')
        elif notification == "log":
            message = request.GET.get('message', None)
            level = request.GET.get('level', None)
            if message is not None and level is not None:
                from uds.core.util import log
                from uds.core.managers import logManager
                
                us = UserService.objects.get(pk=idUserService)
                logManager().doLog(us, level, message, log.TRANSPORT)
            else:
                return HttpResponse('Invalid request!', 'text/plain')
    except Exception as e:
        logger.exception("Exception")
        return errors.errorView(request, e)
    return HttpResponse('ok', mimetype='text/plain')
    

@transformId
def transportIcon(request, idTrans):
    try:
        icon = Transport.objects.get(pk=idTrans).getInstance().icon(False)
        return HttpResponse(icon, mimetype='image/png')
    except Exception:
        return HttpResponseRedirect('/static/img/unknown.png')

@transformId
def error(request, idError):
    return render_to_response('uds/error.html', {'errorString' : errors.errorString(idError)  }, context_instance=RequestContext(request))

@csrf_exempt
def authCallback(request, authName):
    '''
    This url is provided so external SSO authenticators can get an url for
    redirecting back the users.
    
    This will invoke authCallback of the requested idAuth and, if this represents
    an authenticator that has an authCallback 
    '''
    from uds.core import auths
    try:
        authenticator = Authenticator.objects.get(name=authName)
        params = request.GET.copy()
        params.update(request.POST)
        params['_request'] = request
        
        logger.debug('Auth callback for {0} with params {1}'.format(authenticator, params.keys()))
        
        user = authenticateViaCallback(authenticator, params)

        os = OsDetector.getOsFromUA(request.META['HTTP_USER_AGENT'])
                
        if user is None:
            __authLog(request, authenticator, '{0}'.format(params), False, os, 'Invalid at auth callback')
            raise auths.Exceptions.InvalidUserException()

        # Redirect to main page through java detection process, so UDS know the availability of java
        response = render_to_response('uds/detectJava.html', { 'idAuth' : scrambleId(request, authenticator.id)}, 
                                      context_instance=RequestContext(request))
                
        webLogin(request, response, user, '') # Password is unavailable in this case
        request.session['OS'] = os
        # Now we render an intermediate page, so we get Java support from user
        # It will only detect java, and them redirect to Java
        
        return response
    except auths.Exceptions.Redirect as e:
        return HttpResponseRedirect(request.build_absolute_uri(str(e)))
    except Exception as e:
        logger.exception('authCallback')
        return errors.exceptionView(request, e)
        
@csrf_exempt
def authInfo(request, authName):
    '''
    This url is provided so authenticators can provide info (such as SAML metadata)
    
    This will invoke getInfo on requested authName. The search of the authenticator is done
    by name, so it's easier to access from external sources
    '''
    from uds.core import auths
    try:
        authenticator = Authenticator.objects.get(name=authName)
        authInstance = authenticator.getInstance()
        if authInstance.getInfo == auths.Authenticator.getInfo:
            raise Exception() # This authenticator do not provides info
        
        params = request.GET.copy()
        params['_request'] = request
        
        info = authInstance.getInfo(params)
        
        if info is None:
            raise Exception() # This auth do not provides info
        
        if type(info) is list or type(info) is tuple:
            return HttpResponse(info[0], content_type = info[1])
            
        return HttpResponse(info)
    except Exception:
        return HttpResponse(_('Authenticator do not provides information'))
    
    

@webLoginRequired
@transformId
def authJava(request, idAuth, hasJava):
    request.session['java'] = hasJava == 'y'
    try:
        authenticator = Authenticator.objects.get(pk=idAuth)
        os = request.session['OS'] 
        __authLog(request, authenticator, request.user.name, request.session['java'], os, 'Logged in')
        return HttpResponseRedirect(reverse('uds.web.views.index'))
        
    except Exception as e:
        return errors.exceptionView(request, e)

@webLoginRequired
def download(request, idDownload):
    '''
    Downloadables management
    '''
    if request.user.isStaff() is False:
        return HttpResponseForbidden();
    
    if idDownload == '':
        files = [ { 'id' : key, 'name' : val['name'], 'comment' : _(val['comment']) } for key, val in DownloadsManager.manager().getDownloadables().items() ]
        logger.debug('Files: {0}'.format(files))
        return render_to_response('uds/downloads.html', { 'files' : files }, context_instance=RequestContext(request))
    
    return DownloadsManager.manager().send(request, idDownload)
