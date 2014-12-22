"""
This module contains configuration settings used by PySAA
"""

# lifetime of activation links
T_ACTIVATION = 60 * 60 * 24  # 24 h

#maximum number of consecutive wrong login attempts
MAX_ATTEMPTS = 5

#minimum time between two wrong login attempts
#if the time elapsed is lower than this, the attempts counter will be increased
T_LOGIN = 5  # seconds

#time period that an account remains blocked after 
#the maximum number of attempts is reached
T_BLOCKED = 60 * 15  # 15 minutes

#session identifier maximum lifetime
T_SESSION = 60 * 60 * 2  #2h

#if remaining session lifetime is lower than this value
#then a new session id is generated
T_REFRESH = 60 * 5  #5 minutes

#database connection settings
DATABASE = {'class': 'MySqlDb',  #db adapter class
            'config': {  #MySQL specific paramters
                         'host': 'localhost',  #host
                         'port': 3306,  #port
                         'db': 'pyauthdb',  #database name
                         'user': 'root',
                         'passwd': '1979',
            }
}

#front-end url that receives user requests
BASE_URL = "http://www.mydomain.de"

#mail server 
SMTP_SERVER = "smtp.mydomain.de"

#account used to connect to the smtp server
SMTP_USER = "user"

SMTP_PASSWORD = "pass"

#email address, used as the sender address
MAIL_FROM = "dummy@mydomain.de"



