import time,hashlib,os,re,socket

havegzip = True
try:
    import gzip
except ImportError: 
    havegzip = False

try:
    from httplib import IncompleteRead
    import urlparse
    import StringIO
    from urllib import urlencode
    import urllib2
except ImportError: # Python 3
    from http.client import IncompleteRead
    import urllib.parse as urlparse
    import io as StringIO
    from urllib.parse import urlencode
    import urllib.request as urllib2

NoMechanize = False
try:
    import mechanize
except ImportError:
    NoMechanize = True

class Error404(Exception): pass
class NetHandlerRetriesFailed(Exception): pass

class NetHandler:
    ''' Deal with the internets. '''
    def __init__(self,fast=False,gzip=True,keepalive=False,cookies=None):
        self.oldproxy = None
        self.fast = fast
        self.gzip = havegzip and gzip and fast
        self.keepalive = keepalive and fast
        if cookies is None: cookies = not self.fast
        self.cookies = cookies

        if NoMechanize and not self.fast:
            raise Exception("NetHandler MUST be in fast mode when mechanize is not installed.")
        
        if fast:
            handlers = []
            if self.cookies:
                self.cj = mechanize.LWPCookieJar()
                handlers.append(urllib2.HTTPCookieProcessor(self.cj))
            self.br = urllib2.build_opener(*handlers)
        else:
            self.br = mechanize.Browser()
            self.br.set_handle_robots(False)
            if self.cookies:
                self.cj = mechanize.LWPCookieJar()
                self.br.set_cookiejar(self.cj)

        self.setUserAgent()
    
    def setUserAgent(self,ua='Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6'):
        self.br.addheaders = [
            ('User-Agent',ua),
            ('Accept','text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5'),
            ('Accept-Language','en-us,en;q=0.5'),
            ('Accept-Charset','ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
        ]
        
    def setHeaders(self,list=None):
        print("Setting headers.")
        self.br.addheaders = list
        if list == None:
            self.setUserAgent() # Default headers
    
    def clearCookies(self):
        if self.fast: return False # TODO
        self.cj.clear()

    def clone(self): 
        ''' Create a new NetHandler with the same cookies, headers, and other settings. '''
        net = NetHandler(fast=self.fast,gzip=self.gzip,keepalive=self.keepalive)
        net.br.addheaders = self.br.addheaders
        
        if not self.fast:
            net.cj = mechanize.LWPCookieJar()
            net.cj._cookies = self.cj._cookies
            net.br.set_cookiejar(net.cj)
    
    def open(self,url,data=None,referer=None,extra_headers={},num=0):
        ''' Open method with data, referer, and retry support. '''
        RETRIES = 1
        
        # Hash postdata
        if data and isinstance(data,dict):
            data = urlencode(data)
        
        try:
            # Make request
            req = urllib2.Request(url)
            if referer:
                req.add_header("Referer",referer)
            for header,val in extra_headers.iteritems():
                req.add_header(header,val)
            if self.fast and self.gzip:
                req.add_header('Accept-Encoding','gzip')
            obj = self.br.open(req,data)
            
            # Return object
            return obj
        except (urllib2.URLError,socket.timeout,IncompleteRead) as e:
            # Skip error on a 404. Configure this!
            if str(e).find('HTTP Error 404') != -1:
                raise Error404("404 Error.")
            else:
                # Retry if necessary
                if num <= RETRIES:
                    time.sleep(2*num)
                    return self.open(url,data=data,referer=referer,extra_headers=extra_headers,num=num+1)
                else:
                    raise NetHandlerRetriesFailed(str(e))
        except MemoryError:
            raise # Todo: Fix this somehow!?
    
    def __read(self,resp,*args,**kwargs):
        num = 0
        RETRIES = 10
        while 1:
            num += 1
            try:
                data = resp.read(*args,**kwargs)
            except socket.error as e:
                if num > RETRIES: raise
                print 'socket.error:',e
                time.sleep(2*num)
            else:
                break
        return data            

    def get(self,url,data=None,referer=None,extra_headers={}):
        ''' Simple wrapper function to return the contents of a URL. '''
        retry = 0
        while 1:
            try:
                usock = self.open(url,data=data,referer=referer,extra_headers=extra_headers)
                data = self.__read(usock)
                if self.fast and self.gzip and usock.headers.get('content-encoding', None) == 'gzip':
                    data = gzip.GzipFile(fileobj=StringIO.StringIO(data)).read()
                return data
            except IncompleteRead: 
                if retry > 5: raise
                retry += 1
                time.sleep(2)
#            except: raise
            else: break
                
    def setProxy(self,proxy):
        ''' Set the correct proxy, and notify if necessary. '''
        if self.fast: return False # TODO
        if self.oldproxy != proxy:
            if proxy:
                print("Setting proxy '%s'." % (proxy,))
                self.br.set_proxies({"http": proxy})
                self.oldproxy = proxy
            else:
                print("Disabling proxy.")
                self.br.set_proxies({})
                self.oldproxy = None
                
    def makeCookie(self,domain,name,value,expires=time.time()+7*24*3600):
        from cookielib import Cookie
        cookie = Cookie(
            0, # Version
            name,
            value,
            None, # Port
            False, # Port_Specified
            domain,
            False, # Domain_Specified
            False, # Domain_Intial_Dot
            '/',
            False, # Path_Specified
            False, # Secure
            expires, # Expires
            False, # Discard
            None, # Comment
            None, # Comment URL
            None # Rest
        )
        return cookie
        
    def guessFilename(self,url):
        ''' Return the filename a call to saveURL would have produced. '''
        o = urlparse.urlparse(url)
        tup = o.path.split('/')
        if len(tup) > 1:
            filename = tup.pop()
        else:
            filename = 'index.html'
        return filename
        
    def saveURL(self,url,filename=None,referer=None,path=None,extension=None,directory=None,list=False,postdata=None,catch404=True,overwrite=False,skip_if_exists=False):
        ''' Fetch a url and save its contents to filename. 
        Set overwrite true to allow overwriting.
        Set list true to return the url and exit instead of actually downloading.
        Set catch404 false to allow 404 errors to fall through.
        Set referer to add a referer header
        The path argument is handled by .format(md5 = MD5SUM, base = FILENAME)
        BEWARE! Using MD5 in the name requires downloading the whole file into RAM
        '''
        chunkSize = 2048 # Chunk size in KB
        
        if list:
            return url
        
        if not filename:
            filename = self.guessFilename(url)
        
        try:
            # Open URL
            resp = self.open(url,data=postdata,referer=referer)
            data = None
                
            # Handle path input format
            if path:
                # Must download the full file to use MD5 in the name
                if path.find('{md5}') != -1:
                    data = self.__read(resp)
                    path = path.format(md5=hashlib.md5(data).hexdigest())
                filename = path.format(base=filename)
       
            # Prevent overwriting for non-unique names
            if not overwrite:
                filename = getUniqueFilename(filename)
            
            if extension:
                filename = '{0}.{1}'.format(os.path.splitext(filename)[0],extension)
            if directory:
                filename = os.path.join(directory,filename)

            if skip_if_exists and os.path.exists(filename):
                return filename

            # Read from server and write
            with open(filename,'wb') as file:
                if not data:
                    while True:
                        chunk = self.__read(resp,chunkSize)
                        if not chunk: break
                        file.write(chunk)
                else:
                    file.write(data)
            
            return filename
        except Error404:
            if catch404:
                return "404 on %s. Skipping." % (url,)
            else:
                raise
            
def getUniqueFilename(filename):
    while os.path.exists(filename):
        number = 2
        base,ext = os.path.splitext(filename)
        m = re.match(r'(.*?) \((\d+)\)',base)
        if m:
            number = int(m.group(2)) + 1
            base = m.group(1)
        filename = "{0} ({1:d}){2}".format(base,number,ext)
    return filename
