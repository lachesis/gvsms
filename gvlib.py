import nethandler
import json as jsonlib
import re

class LoginFailure(Exception): pass
class REFailure(Exception): pass
class SMSTooLong(Exception): pass
class InvalidDestination(Exception): pass
class InvalidType(Exception): pass

class Phone:
    def __init__(self,id,name,number):
        self.id = id
        self.name = name
        self.number = number
    def __str__(self):
        return "%s: %s (%s)" % (self.id,self.name,self.number)
    def equals(self,obj):
        if str(obj).lower() == str(self.id).lower():
            return True
        if str(obj) == self.name.lower():
            return True
        if str(obj) == self.number.lower():
            return True
        try:
            if obj.number == self.number:
                return True
        except:
            pass
        return False

class GVHandler:
    def __init__(self):
        self.MAXSMSLEN = 160
        self.net = nethandler.NetHandler()
        self.loggedin = False
        self.gvhomedata = None
        self.email = None
        self.password = None
        self.phonelist = None
        self.rnrse = None
        self.authtok = None
        self.contacts = None
    
    def setCredentials(self,email,password):
        self.email = email
        self.password = password
    
    def login(self):
        if self.loggedin: return True
        if self.authtok: return True
        #if self.rnrse: return True
        if not (self.email and self.password): raise LoginFailure("No username or password specified.")

        txt = self.net.get('https://www.google.com/accounts/ClientLogin', data={
        #txt = self.net.get('http://localhost:3131/accounts/ClientLogin', data={
                'accountType':'HOSTED_OR_GOOGLE',
                'Email':self.email,
                'Passwd':self.password,
                'service':'grandcentral',
                'source':'gvsms'
               })
        

        if re.search('(?mis)The username or password you entered is incorrect',txt):
            raise LoginFailure("Bad username or password.")
        
        self.loggedin = True
        self.authtok = filter(lambda x: x.lower().startswith('auth='), txt.strip().split('\n'))[0][5:]

    # def login(self):
    #   ''' Login to Google Voice. '''
    #   if self.loggedin: return True
    #   if self.rnrse: return True
    #   if not (self.email and self.password): raise LoginFailure("No username or password specified.")
        
    #   # Get the GALX cookie
    #   self.net.open('https://www.google.com/accounts/ServiceLogin?passive=true&service=grandcentral&ltmpl=bluebar')
        
    #   # Find it
    #   for cookie in self.net.cj:
    #       if cookie.name.upper() == 'GALX':
    #           cv = cookie.value
        
    #   # Do login
    #   txt = self.net.open('https://www.google.com/accounts/ServiceLoginAuth?service=grandcentral', data={
    #       'ltmpl' : 'bluebar',
    #       'service' : 'grandcentral',
    #       'GALX' : cv,
    #       'rmShown' : '1',
    #       'signIn' : 'Sign in',
    #       'asts' : '',
    #       'Email' : self.email,
    #       'Passwd' : self.password,
    #       'continue' : 'https://www.google.com/voice/account/signin',
    #       'PersistentCookie' : 'yes'
    #   } ).read()
        
    #   if re.search('(?mis)The username or password you entered is incorrect',txt):
    #       raise LoginFailure("Bad username or password.")
        
    #   self.loggedin = True

    def sendSMS(self,dest,msg):
        ''' Send a text 'msg' to 'dest'. '''        
        # Check message length
        if len(msg) > self.MAXSMSLEN:
            raise SMSTooLong("Your message is %d characters. Max is %d." % (len(msg),self.MAXSMSLEN))
        
        # Send the text(s)
        data = self.net.open('https://www.google.com/voice/sms/send/', data={
            '_rnr_se': self.getRnrse(),
            'phoneNumber': dest,
            'text': msg
        }, extra_headers={'Authorization':'GoogleLogin auth={0}'.format(self.authtok)}).read()
        
        # Return the status code
        return data
    
    def getAuthToken(self):
        if self.authtok:
            return self.authtok
        else:
            raise Exception("No auth token available.")

    def setAuthToken(self,token):
        self.authtok = token
        self.loggedIn = True
        
        try: 
            self.getRnrse()
        except (REFailure,nethandler.NetHandlerRetriesFailed) as e:
            self.loggedIn = False
            self.authtok = None
            raise REFailure("Regular expression failure. Cookie has probably expired.")

    def saveAuthToken(self,filename):
        if not self.authtok:
            raise Exception("No auth token available.")
        else:
            with open(filename,'w') as out:
                out.write(self.authtok)
            return True

    def loadAuthToken(self,filename):
        try:
            with open(filename,'r') as inp:
                self.authtok = inp.read().strip()
                self.loggedIn = True
            return True
        except IOError: raise

        try: self.getRnrse()
        except REFailure as e:
            raise REFailure("Regular expression failure. Cookie has probably expired.")
        
    # def saveLoginCookie(self,filename):
    #   ''' Save login cookies to a filename. '''
    #   if not self.loggedin:
    #       raise Exception("Not logged in.")
    #       return False
    #   self.net.cj.save(filename)
    #   return True
        
    # def loadLoginCookie(self,filename):
    #   ''' Load login cookies from a filename. '''
    #   try:
    #       self.net.cj.revert(filename)
    #   except IOError:
    #       raise IOError("Bad filename specified.")
        
    #   try:
    #       self.getRnrse()
    #   except REFailure,e:
    #       raise REFailure("Regular expression failure. Cookie has probably expired.")
        
    #   self.loggedin = True
    #   return True
        
    def getRnrse(self):
        if not self.rnrse:
            if not self.gvhomedata:
                # Fetch the homepage
                self.gvhomedata = self.net.get('https://www.google.com/voice/#inbox',extra_headers={'Authorization':'GoogleLogin auth={0}'.format(self.authtok)})
                
            # Go through the home page and grab the value for the hidden
            # form field "_rnr_se", which must be included when sending texts
            match = re.search('name="_rnr_se".*?value="(.*?)"', self.gvhomedata)
            if not match: raise REFailure("Couldn't get _rnr_se. Not logged in?")
            self.rnrse = match.group(1)
        
        return self.rnrse
        
    def getContacts(self):
        ''' Return a list of contacts. '''
        if not self.contacts: 
            if not self.gvhomedata:
                # Fetch the homepage
#               self.gvhomedata = self.net.open('http://localhost:3131/voice/#inbox',extra_headers={'Authorization':'GoogleLogin auth={0}'.format(self.authtok)}).read()
                self.gvhomedata = self.net.open('https://www.google.com/voice/#inbox',extra_headers={'Authorization':'GoogleLogin auth={0}'.format(self.authtok)}).read()
            
            self.contacts = []
            
            m = re.search(r"'contacts': (\{.*?\}),\n",self.gvhomedata)
            json = jsonlib.loads( m.group(1) )
            
            for key in json:
                c = json[key]
                if c['contactId'] != '0':
                    self.contacts.append( Contact(c) )
            
        return self.contacts

    def setPhoneEnableStatus(self,phoneId,status):
        txt = self.net.open('https://www.google.com/voice/settings/editDefaultForwarding/',{'phoneId':phoneId,'enabled':status and 1 or 0,'_rnr_se':self.rnrse},extra_headers={'Authorization':'GoogleLogin auth={0}'.format(self.authtok)}).read()
        json = jsonlib.loads(txt)
        return json['ok']
        
    def getPhoneList(self):
        ''' Return a list of phones with name and number. '''
        if not self.phonelist: 
            if not self.gvhomedata:
                # Fetch the homepage
                self.gvhomedata = self.net.open('https://www.google.com/voice/#inbox',extra_headers={'Authorization':'GoogleLogin auth={0}'.format(self.authtok)}).read()
            
            self.phonelist = []
            
            m = re.search(r"'phones': (\{.*?\}),\n",self.gvhomedata)
            json = jsonlib.loads( m.group(1) )
            
            for key in json:
                p = json[key]
                self.phonelist.append( Phone(p['id'], p['name'], p['phoneNumber']) )
            
        return self.phonelist
 
    # def togglePhone(self,phone,setStatus=None):
    #   if setStatus == None: # Toggle
    #       setStatus = not self.getPhoneStatus(phone)

    #   if setStatus in (True,1,'on','enabled','enable'):
    #       status = 1
    #   elif setStatus in (False,0,'off','disabled','disable'):
    #       status = 0

    #   id = phone.id
    #   self.net.open('',data={
    #           'phoneId':id,
    #           'enabled':status,
    #           '_rnr_se':self.getRnrse()
    #   }).read()
    
    def isNumber(self,input):
        if re.match(r'[\d\-\(\)\+]+',input):
            return True
        return False
    
    def matchContact(self,input):
        ''' Compare 'input' against contacts. '''
        list = []
        for k in self.getContacts():
            if k.equals(input):
                list.append(k)
        
        if len(list) == 0:
            raise InvalidDestination("The input %s doesn't correspond to a valid contact." % (input,))
        elif len(list) > 1:
            raise InvalidDestination("The input %s corresponds to multiple contacts." % (input,))
        
        return list[0]
    
    def getNumber(self,input,type='p'): # type = Primary
        ''' Try to get a valid number by matching an input against the contacts list. '''
        if self.isNumber(input):
            return [ Number(phoneNumber = input) ]
        else:
            return self.matchContact(input).getNumber(type)
    
    def placeCall(self,dest,src):
        ''' Place a call to 'dest' ringing 'src'. '''
        data = self.net.open('https://www.google.com/voice/call/connect/', data={
            '_rnr_se': self.getRnrse(),
            'outgoingNumber': dest,
            'forwardingNumber': src,
            'subscriberNumber': 'undefined',
            'remember':'0'
        }, extra_headers={'Authorization':'GoogleLogin auth={0}'.format(self.authtok)}).read()
        
        return data

class Number:
    def __init__(self,obj=None,name=None,phoneNumber=None):
        self.phoneNumber = phoneNumber
        self.name = name
        self.displayNumber = None
        self.phoneType = None
        if obj:
            try:
                self.phoneNumber = obj['phoneNumber']
                self.displayNumber = obj['displayNumber']
                self.phoneType = obj['phoneType']
            except KeyError,e:
                #print "Key error in %s (%s)." % (self.phoneNumber,e)
                pass
    
    def isType(self,type='m'):
        ''' Check if a number is of a designated type. '''
        if not isinstance(self.phoneType,basestring) or not isinstance(type,basestring):
            return False
        
        if type.lower() in ('m','cell','mobile'):
            ttype = 'mobile'
        elif type.lower() in ('h','home'):
            ttype = 'home'
        elif type.lower() in ('w','work'):
            ttype = 'work'
        else:
            raise InvalidType("Invalid type definition '%s'." % (type,))
            
        if self.phoneType.lower() == ttype:
            return True
        return False
    
    def __str__(self):
        return "%s %s" % (self.displayNumber and self.displayNumber or self.phoneNumber,self.phoneType)
        
class Contact:
    def __init__(self,json):
        #self.id = int(json['contactId'])
        self.name = json['name']
        self.primaryNumber = Number(name = self.name)
        self.primaryNumber.phoneNumber = json['phoneNumber']
        self.primaryNumber.displayNumber = json['displayNumber']
        self.primaryNumber.phoneType = json['phoneTypeName']
        self.numbers = [ Number(obj=k,name=self.name) for k in json['numbers'] ]
        
    def getNumber(self,type='m'):
        ''' Return a list of numbers of type 'type'. '''
        if type.lower() in ('p','prim','primary'):
            return [self.primaryNumber]
        else:
            list = []
            for number in self.numbers:
                if number.isType('m'):
                    list.append(number)
            return list
    
    def equals(self,other):
        # Allow case insensitivity
        if isinstance(other,basestring): # string
            other = other.lower()
            
        # Name check
        if self.name and self.name.lower() == other:
            return True
        
        # First or last name check
        if self.name and other in self.name.lower().split(' '):
            return True
        
        # Phone number check
        for number in self.numbers:
            if number.phoneNumber == other:
                return True
        
        # Fall through
        return False
    
    def __str__(self):
        return "%s: (%s) [%s]" % (self.name, self.primaryNumber, ', '.join( [str(k) for k in self.numbers] ))
        
