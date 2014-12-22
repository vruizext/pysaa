"""
utils.py

This module contains common functionalities that are used by other classes:
Settings class and the methods random_string and send_mail
"""
import random
import smtplib
import string

from email.mime.text import MIMEText


CHARS = string.ascii_letters + string.digits


class Settings(object):
	"""
	This class provides global access to the configuration settings, 
	which are loaded from the module specified in the variable SETTINGS_MODULE
	"""

	_instance = None  # instance of this class

	def __new__(cls):
		if Settings._instance is None:
			Settings._instance = object.__new__(cls)  # create new instance
			Settings._instance.import_settings()  # import the settings

		return Settings._instance

	def import_settings(self):
		"""
		import the module where the settings are found and set this settings as
		attributes of the instance
		"""
		try:
			import importlib  # only needed here, executed only 1 time
			from pysaa import SETTINGS_MODULE

			mysettings = importlib.import_module(SETTINGS_MODULE)
		except Exception as e:
			raise ImportError("Could not import settings '%s': %s" % (SETTINGS_MODULE, e))

		for setting in dir(mysettings):
			if setting == setting.upper():  # get only attributes in uppercase
				value = getattr(mysettings, setting)
				setattr(self, setting, value)


def random_string(length):
	"""
	Creates a string of random bytes, chosen from CHARS variable
	
	Arguments:
	length(int) -- length of the string  
	
	Returns:
	str -- the random string generated
	"""
	# uses the operative system random number generator
	randrange = random.SystemRandom().randrange
	n = len(CHARS)
	offset = randrange(n)
	#get random chars from CHARS and generates a string
	return ''.join([CHARS[randrange(n) - offset] for _ in range(length)])


def send_mail(user, activation):
	"""
	Generates activation link and send it to the user using smtplib
	SMTP server settings are taken from settings object 
	
	Arguments:
	user(model.User) -- user entity
	activation(model.Activation) -- activation entity
	"""
	settings = Settings()
	# generate the link
	link = settings.BASE_URL + "/activate?aid=" + activation.activation_id
	#build a simple text message containing the link
	msg = MIMEText(link)
	msg['Subject'] = 'activation of your account'
	msg['From'] = settings.MAIL_FROM
	msg['To'] = user.email
	#connect to mail server
	server = smtplib.SMTP(settings.SMTP_SERVER)
	#login, if necessary
	server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
	#send the email
	server.sendmail(settings.MAIL_FROM, user.email, msg.as_string())
	#disconnect from smtp server
	server.quit()


if __name__ == "__main__":
	print(random_string(64))
	print(random_string(64))
	print(random_string(64))
	print(random_string(64))
	print(CHARS[-4])
	# s1 = make_hash('aaa@aaa.de', str(time.time()))
	#s2 = hashlib.md5(s1.encode('utf-8')).hexdigest()

	#print ( "%s: %s" % (s1, len(s1)))
	#print ( "%s: %s" % (s2, len(s2)))