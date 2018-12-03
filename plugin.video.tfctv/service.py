#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import SocketServer,re,shutil,threading,urllib,urllib2,ssl,cookielib
import xbmc,xbmcaddon

from SimpleHTTPServer import SimpleHTTPRequestHandler
from urlparse import urlparse, parse_qsl
from resources import config
from resources.lib.libraries import control

class ProxyHandler(SimpleHTTPRequestHandler):

    _cj = cookielib.LWPCookieJar()
    _user_agent = config.userAgents['default']
            
    def do_GET(self):
        xbmc.log('Requested : %s' % (self.path), level=xbmc.LOGDEBUG)
        if '/healthcheck' in self.path:
            self.send_response(200)
        else:
            query = self.getQueryParameters(self.path)
            if ('url' in query):
            
                requestHeaders = []
                requestHeaders.append(('User-Agent', self._user_agent))            
                res = self.urlopen(query.get('url'), headers=requestHeaders)
                
                if (res.get('status')):
                    proxyUrlFormat = control.setting('proxyStreamingUrl')
                    content = re.sub(r'(http[^\s"]+)', lambda x: proxyUrlFormat % (control.setting('proxyHost'), control.setting('proxyPort'), urllib.quote(x.group(0))), res.get('body'))
                    
                    self.send_response(res.get('status'))
                    for header, value in res.get('headers').items():
                        if (header.lower() == 'content-length'):
                            value = len(content)
                        if (header.lower() == 'set-cookie'):
                            netloc = urlparse(proxyUrlFormat).netloc
                            host = netloc.split(':')[0] if ':' in netloc else netloc
                            value = re.sub(r'path=[^;]+; domain=.+', 'path=/; domain=%s' % (host), value)
                        if (header.lower() in ('server', 'set-cookie')):
                            continue
                        self.send_header(header, value)
                    self.end_headers()
                    self.wfile.write(content)
                    self.wfile.close()
                else:
                    self.send_error(522)
            else:
                self.send_error(400)
                        
    def urlopen(self, url, params = {}, headers = []):        
        res = {}
        opener = urllib2.build_opener(urllib2.HTTPRedirectHandler(), urllib2.HTTPCookieProcessor(self._cj))
        opener.addheaders = headers
        requestTimeOut = int(xbmcaddon.Addon().getSetting('requestTimeOut')) if xbmcaddon.Addon().getSetting('requestTimeOut') != '' else 20
        response = None
        
        try:
            if params:
                data_encoded = urllib.urlencode(params)
                response = opener.open(url, data_encoded, timeout = requestTimeOut)
            else:
                response = opener.open(url, timeout = requestTimeOut)
                
            res['body'] = response.read() if response else ''
            res['status'] = response.getcode()
            res['headers'] = response.info()
            res['url'] = response.geturl()
        except (urllib2.URLError, ssl.SSLError) as e:
            message = '%s : %s' % (e, url)
            xbmc.log(message, level=xbmc.LOGERROR)
        
        return res
        
    def getQueryParameters(self, url):
        qparam = {}
        query = url.split('?')[1] if (len(url.split('?')) > 1) else None 
        if query:
            qparam = dict(parse_qsl(query.replace('?','')))
        return qparam 
        
if __name__ == "__main__":
    httpPort = int(control.setting('proxyPort'))
    server = SocketServer.TCPServer(('', httpPort), ProxyHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    xbmc.log('[%s] Service: starting HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGNOTICE)
    
    monitor = xbmc.Monitor()

    # XBMC loop
    while not monitor.waitForAbort(10):
        pass

    server.shutdown()
    server_thread.join()
    xbmc.log('[%s] - Service: stopping HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGNOTICE)