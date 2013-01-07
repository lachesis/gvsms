#!/usr/bin/python2.7
from nethandler import NetHandlerRetriesFailed
import re,sys,time,os
from argparse import ArgumentParser
import getpass
import json
from gvlib import *
from nethandler import NetHandlerRetriesFailed

def choosePhone(input=''):
    if input:
        print "Getting phone list."
    if not input:
        s = "Phone List:\n" + '\n'.join( [str(p) for p in gv.getPhoneList()] )
        input = get(s + "\nChoose a phone to ring: ").lower()
    for p in gv.getPhoneList():
        if p.equals(input):
            return p
    raise Exception("Invalid phone.")

def chkStatus(status):
    if status == '{"ok":true,"data":{"code":0}}':
        alert( "Success." )
        return True
    else:
        alert( "Failure. Details: %s" % (status,) )
        return False

def alert(message):
    print message

def get(prompt):
    return raw_input(prompt)

CONFIG_PATH = os.path.join(os.environ['HOME'],'.gv.conf')

def common(args,config):
    # Create GVHandler object
    gv = GVHandler()

    # Load auth token if available
    try:
        if config.get('token',None):
            gv.setAuthToken(config.get('token',None))
    except (REFailure,NetHandlerRetriesFailed): gv.loggedIn = False

    # Login if we still need to
    if not gv.loggedIn:
        username = config.get('username',None)
        password = config.get('password',None)
        token = config.get('token', None)
        if not (username and (password or token)):
            alert( 'You cannot log in without a username and password.' )
            sys.exit(1)
        if not re.match(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b',username): # Invalid username
            alert( 'You specified %s, which is not a valid email address. Perhaps you forgot the "@gmail.com"?' % (username,) )
            sys.exit(1)

        gv.setCredentials(username,password)
        gv.login()

    # Save login token
    try:
        if config.get('token',None) is not None:
            config['token'] = gv.getAuthToken()
    except:
        print 'exe2'
        raise

    return gv

def send_sms(args,config):
#    print "GVSMS v0.6"
#    print "By Eric Swanson"
#    print

    gv = common(args,config)

    dest = args.destination
    msg = args.message
    if dest == None:
        dest = get("Destination number: ")
    if msg == None:
        msg = get("Message to send (end with newline): ")

    # Compare against contacts
    pn = gv.getNumber(dest)[0] # TODO: Alert when more than one number is returned.
    if pn.name:
        print "Looked up contact: %s (%s)" % (pn.name,pn)
        if not pn.isType('mobile'):
            print "Warning: We're trying to send a text to a %s number!" % (pn.phoneType,)
    dest = pn.phoneNumber

    # Send the SMS
    print "Sending '%s' to %s." % (msg,dest)
    try:
        status = gv.sendSMS(dest,msg)
        status = chkStatus(status)
    except SMSTooLong: # Break the message into shorter ones
        msglist = []
        while len(msg) > 0:
            # Choose slice size
            slice = gv.MAXSMSLEN
            if len(msg) < slice:
                slice = len(msg)

            # Append to list
            msglist.append(msg[:slice].strip())

            # Remove from string
            msg = msg[slice:]

        # Ask user: should we still send?
        inp = get("Split into {0} messages [Y,n]? ".format(len(msglist)))
        if inp.lower() in ('n','q'):
            raise

        status = True
        for i,msg in enumerate(msglist):
            print "Message {0}:".format(i),
            status = status and chkStatus(gv.sendSMS(dest,msg))
        return status

def make_call(args,config):
#    print "GVDial v0.6"
#    print "By Eric Swanson"
#    print

    gv = common(args,config)

    dest = args.destination
    src = args.source
    if dest == None:
        dest = get("Number to call: ")
    if src == None:
        src = get("Phone to ring (blank for a menu): ")

    # Compare against contacts
    pn = gv.getNumber(dest)[0] # TODO: Alert when more than one number is returned.
    if pn.name:
        print "Looked up contact: %s (%s)" % (pn.name,pn)
    dest = pn.phoneNumber

    if not src: # Prompt for source phone
        tp = choosePhone()
    else:
        tp = choosePhone(src)

    # Place the call
    print "Calling %s using phone %s." % (dest,tp)
    return chkStatus(gv.placeCall(dest,tp.number))

try:
    if __name__ == '__main__':
        parser = ArgumentParser()
#        parser.add_argument("-u","--user",action="store",dest="username",help="Specify a username (full email address).")
#        parser.add_argument("-p","--password",action="store",dest="password",help="Specify a password.")
#        parser.add_argument("-s","--save-login",action="store",dest="savelogin",help="Save login cookies to a file.")
#        parser.add_argument("-l","--load-login",action="store",dest="loadlogin",help="Load login cookies to a file.")
        parser.add_argument("-c","--config",action="store",dest="configpath",default=CONFIG_PATH,help="Config path. Default: $default")

        sub_parsers = parser.add_subparsers()

        sms_parser = sub_parsers.add_parser("sms")
        sms_parser.add_argument("destination",nargs="?",help="Destination number or contact.")
        sms_parser.add_argument("message",nargs="?",help="Message to send.")
        sms_parser.set_defaults(func=send_sms)

        call_parser = sub_parsers.add_parser("call")
        call_parser.add_argument("destination",nargs="?",help="Destination number or contact.")
        call_parser.add_argument("source",nargs="?",help="Phone to ring.")
        call_parser.set_defaults(func=make_call)

        args = parser.parse_args()

        config = {}
        try:
            with open(args.configpath,'r') as inp:
                config = json.load(inp)
        except Exception as e:
            print "Warning: cannot load config file ({0}: {1})".format(type(e),str(e))

        args.func(args,config)

        try:
            with open(args.configpath,'w') as out:
                json.dump(config,out)
        except Exception as e:
            print "Warning: cannot load config file ({0}: {1})".format(type(e),str(e))

except KeyboardInterrupt:
    print "Keyboard interrupt."
    sys.exit(1)
