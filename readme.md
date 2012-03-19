#Google Voice command line tool
Send SMS or make calls from the command line.
  
Features:  
1. Google contact lookup  
2. Login cookie storage  
3. Split messages automatically on 140 character boundaries  
4. JSON config file  
  
Usage: `gv [-c config_file] sms [destination] [message]`  
Usage: `gv [-c config_file] call [destination] [phone to ring]`  
e.g. `gv sms "John Smith" "Be there any minute, man."`  
  
Make sure you have a json config file at the default path ($HOME/.gv.conf)  
Login token from client login can be cached. If you create a config file like the following:  
`{"username":"email@domain.com","password":"google password","token":""}`  
and then send a message, the program will log in and save the token. You can then remove your password from the file.  
  
I may create a more elegant interface for this in the future.  
  
Enjoy!  
