"""
This module contains PySAA server logic, implemented
using a Command pattern. For each possible request type exposed
there's a class implementing the correspondent logic to
process the request.

The AuthServer class provides a single interface to the API.
It decides which request class must be created to accomplish
the requested action, based on 'type' parameter
"""

import logging
import time

import pysaa.utils as utils
from pysaa.model import User, Activation, Login, Role, Permission
from pysaa.dbapi import dbconn


class PySAARequest(object):
	"""
	Base class for PySAA requests. 
	"""

	def __init__(self, **kw):
		"""
		sets internal reference to the request data
		
		Arguments:
		kw(dict) -- request data
		"""
		self.data = kw

	def do_process(self, db):
		"""
		The classes extending PySAARequest class must implement this method, with 
		the logic needed to process the request
		
		Arguments:
		db(dbapi.Db) -- Db object used to connect with database. If needed, it's 
		passed to the method through a function decorator (dbconn)
		"""

	def get_user_by_email(self, email):
		"""
		Gets user entity from the email with which the user is registered 
		
		Arguments:
		email(str) -- user email
		
		Returns: 
		model.User -- User entity if the user is registered, 
		None -- if no user is found
		
		Raises:
		PySAAError -- if there are more than one registered users with this mail
		"""
		users_list = User(self.db).list(email=email)
		if len(users_list) == 0:
			return None
		if len(users_list) > 1:
			raise PySAAError("duplicate email %s, it must be unique " % email)

		return users_list[0]


	def get_login_by_sid(self, sid):
		"""
		Retrieves login data from the session identifier
		
		Arguments:
		sid(str) -- session identifier 
		
		Returns: 
		model.Login -- Login entity
		None -- if no login have been found with this sid
		"""
		log_list = Login(self.db).list(session_id=sid)
		if len(log_list) == 0:
			return None

		return log_list[0]


class RegistrationRequest(PySAARequest):
	"""
	Contains the logic for processing a request for setting a new user
	"""

	@dbconn(in_trx=True)
	def do_process(self, db):
		email = self.data['email']
		password = self.data['pwd']

		user = self.get_user_by_email(email)

		# if this email is not registered, create new user
		if user is None:
			user = User(self.db)
			user.set(email=email, password=password, status=User.STATUS_INACTIVE, role_id=Role.ROLE_STANDARD)

		else:
			self.check_user(user)
			# user registered but activation expired
			# update user with new password and save
			user.password = password

		user.save()
		# create activation object
		act = self.new_activation(user)
		utils.send_mail(user, act)
		self.data['result'] = True
		del (self.data['pwd'])  # don't return password, not necessary
		return self.data

	def check_user(self, user):
		"""
		Checks whether the user is active or not
		
		Arguments:
		user(model.User) -- user being checked
		
		Returns: 
		bool -- True if the email is not registered
		
		Raises:
		RegistrationError -- if the user is already registered:
		  - The email belongs to an active (or blocked) user
		  - The email belongs to an inactive user, with a pending activation 
		"""
		if not user.status == User.STATUS_INACTIVE:
			# an active user has registered this email
			raise RegistrationError("user %s already registered" % user.email)

		# else: email registered but user account has not been activated
		# get activation data and check if it is still valid
		act = Activation(self.db, user.id)
		if act and (time.time() - act.created) <= settings.T_ACTIVATION:
			# there's a valid activation, but it has not been confirmed
			# if we allow to register again, anyone could change the
			#password of an inactive user, so we raise error
			raise RegistrationError("user %s already registered but not activated" % user.email)

		# if act is None: no activation found (maybe a database error?)
		# anyway allow continue and register again, if not this email
		#would be permanently blocked
		return True

	def new_activation(self, user):
		"""
		Creates and saves new activation in database for this user
		
		Arguments:
		user (model.User) -- user being activated
		
		Returns:
		model.Activation -- activation entity created
		"""
		now = int(time.time())
		# generate random activation key
		hash_id = utils.random_string(64)
		act = Activation(self.db, user.id)
		act.set(user_id=user.id, activation_id=hash_id, created=now)
		act.save()
		return act


class ActivationRequest(PySAARequest):
	"""
	Processes the requests for activating a user
	The activation being requested is identified by aid parameter
	"""

	@dbconn(in_trx=True)
	def do_process(self, db):
		aid = self.data['aid']

		# look for activation register
		act = self.get_activation_by_aid(aid)

		if act is None:
			raise ActivationError("activation link not valid")

		user = User(self.db, act.id)
		if not user:
			# error: user not found, delete activation
			act.delete()
			raise ActivationError("activation link not valid")

		if (time.time() - act.created) >= settings.T_ACTIVATION:
			# activation expired, delete entries from db
			act.delete()
			user.delete()
			raise ActivationError("activation link expired")

		# else: hash is valid, activate user
		user.status = User.STATUS_ACTIVE
		user.update()
		act.delete()  # activation not needed anymore
		self.data['result'] = True
		return self.data

	def get_activation_by_aid(self, aid):
		"""
		Gets activation data from the activation identifier
		
		Arguments:
		aid(str) -- activation identifier
		
		Returns:
		model.Activation -- activation entity if it's found
		None -- if no activation is found
		"""
		act_list = Activation(self.db).list(activation_id=aid)
		if len(act_list) == 0:
			return None
		return act_list[0]


class AuthenticationRequest(PySAARequest):
	"""
	Processes a login request
	User authentication is performed with email and pwd parameters
	"""

	@dbconn(in_trx=True)
	def do_process(self, db):
		email = self.data['email']
		password = self.data['pwd']

		# try to get user by email
		user = self.get_user_by_email(email)

		if user is None:
			raise AuthenticationError("user '%s' not registered" % email)

		self.check_user(user)

		attempts = 0  # number of wrong attempts
		last_ts = 0  # timestamp of the last login attempt
		lo = Login(self.db, user.id)
		# if lo.session_id:
		# the user has still a valid session, but the sid is not sent
		# maybe an error in front-end? 
		# we do nothing and continue, in order to allow a new authentication
		# and create a new session. also, the user account could be blocked
		# when he is actually logged in if a malicious user tries to login
		# with his email

		# else: if user has a login
		# there was at least one previous refused login, take the data
		if lo:
			attempts = lo.attempts
			last_ts = lo.created

		#else: check password
		if user.password == password:
			#authentication successful, register login
			lo = self.save_login(user, Login.STATUS_ACCEPTED)
			#return session identifier
			self.data['sid'] = lo.session_id
			self.data['result'] = True
			del (self.data['pwd'])  #don't return password, not necessary
			return self.data

		#else: wrong password,
		#if first attempt, dont check time, just set to 1
		if attempts == 0:
			attempts = 1

		#else: check time of previous login 
		elif (time.time() - last_ts) <= settings.T_LOGIN:
			attempts += 1
			if attempts >= settings.MAX_ATTEMPTS:
				# user blocked
				user.status = User.STATUS_BLOCKED
				user.update()
				attempts = 0  #reset counter

		#anyway save login and return false
		self.save_login(user, Login.STATUS_REFUSED, attempts)
		self.data['result'] = False
		return self.data

	def check_user(self, user):
		"""
		Checks whether the user is active or blocked
		If the user is blocked but the blocking period is expired, it's set
		as active again
		
		Arguments:
		user(model.User) -- user entity being checked
		
		Raises:
		AuthenticationError -- if the user is inactive or blocked
		"""
		# inactive users can't login until they activate their account
		if user.status == User.STATUS_INACTIVE:
			raise AuthenticationError("user '%s' registered but not activated" % user.email)

		if user.status == User.STATUS_BLOCKED:
			# if user is blocked, don't allow to continue during
			# the blocking period
			lo = Login(self.db, user.id)
			if lo and (time.time() - lo.created) <= settings.T_BLOCKED:
				raise AuthenticationError("user %s is temporally blocked, try later" % user.email)

			# else: after blocking time or login register does not exist (last_ts = 0)
			#set again active and continue the login process
			user.status = User.STATUS_ACTIVE
			user.update()

	def save_login(self, user, status, n=0):
		"""
		Creates Login entity and saves login data
		
		Arguments:
		user(model.User) -- User that attempts to log in
		status(int) - login accepted(1) or refused(0)
		n(int) - if no login is refused, number of wrong login attempts
		
		Returns:
		model.Login -- the entity containing login data
		"""
		now = int(time.time())
		sid = ""
		if status == Login.STATUS_ACCEPTED:
			# authentication successful, generate random session id
			sid = utils.random_string(64)

		lo = Login(self.db, user.id)
		lo.set(user_id=user.id, session_id=sid, status=status, attempts=n, created=now)
		lo.save()
		return lo


class AuthorizationRequest(PySAARequest):
	"""
	Processes the request for accessing to a specific resource/content
	The content requested is identified by oid parameter (object identifier)
	User must have a valid session, identified by sid parameter
	"""

	@dbconn(in_trx=False)
	def do_process(self, db):
		role = None
		sid = self.data['sid']  # session identifier
		oid = self.data['oid']  # object identifier

		if sid:
			# try to get login data
			lo = self.get_login_by_sid(sid)
			if lo is None:
				# wrong hash_id received, expired or someone try to fake?
				raise AuthenticationError("authentication expired")

			self.check_session(lo)
			# if user authenticated, get user role
			role = self.get_role_by_uid(lo.user_id)
		else:  # user no authenticated, default role
			role = Role(self.db, Role.ROLE_ANONYMOUS)

		# get objects granted to this role and its parents
		permissions = self.get_permissions_by_role(role)
		# return true if object requested is in the list of granted objects
		self.data['result'] = oid in permissions
		return self.data

	def check_session(self, lo):
		"""
		Checks if current session is valid. If it has expired, deletes it
		from database. If not, timestamp is refreshed and new sid is generated
		if the session is close to expire
		
		Arguments:
		lo(model.Login) -- Login entity 
		
		Raises:
		AuthenticationError -- if session is not valid or has expired
		"""
		if lo.status != Login.STATUS_ACCEPTED:
			# if we got here, it should never happen that the login is not accepted
			# anyway this will fix any unexpected behaviour
			lo.delete()
			raise AuthenticationError("not a valid session")

		now = time.time()
		if (now - lo.created) >= settings.T_SESSION:
			# session expired, delete login data
			lo.delete()
			raise AuthenticationError("authentication expired")

		# else: refresh login timestamp and create new session id if the
		# current session is about to expire
		if (now - lo.created) >= (settings.T_SESSION - settings.T_REFRESH):
			now = int(time.time())
			sid = utils.random_string(64)
			lo.set(session_id=sid, created=now)
			lo.save()

	def get_permissions_by_role(self, role):
		"""
		Get a list of the objects ids which a role can access to.
		Get also the permissions of the parent's role 
		
		Arguments:
		role(model.Role) -- Role entity
		
		Returns:
		list - a list with object identifiers (string)
		"""
		pe_list = Permission(self.db).list(role_id=role.id)
		oid_list = [p.object_id for p in pe_list]
		# get permissions also for the parents of this role
		role = Role(self.db, role.parent_id)
		if role.parent_id:
			oid_list.extend(self.get_permissions_by_role(role))

		return oid_list

	def get_role_by_uid(self, uid):
		"""
		Get the user's role from its user id
		
		Arguments:
		uid(int) -- user identifier
		
		Returns:
		model.Role -- Role entity 
		"""
		user = User(self.db, uid)
		return Role(self.db, user.role_id)


class LogoutRequest(PySAARequest):
	"""
	Processes the request for a logout
	Session being closed it's identified by sid parameter
	"""

	@dbconn(in_trx=True)
	def do_process(self, db):
		# try to get login data from the id
		sid = self.data['sid']  # session identifier
		lo = self.get_login_by_sid(sid)
		# if user is logged in, delete login
		if lo and lo.status == Login.STATUS_ACCEPTED:
			lo.delete()
			self.data['result'] = True
			return self.data

		# else: user is not authenticated or invalid sid
		raise PySAAError("user not authenticated or authentication expired")


class DefaultRequest(PySAARequest):
	def do_process(self):
		raise PySAAError("Unrecognized Request type: %s" % self.data['type'])


class PySAAError(Exception):
	"""
	Generic Exception related to PySAA requests
	"""


class RegistrationError(PySAAError):
	"""
	Exception raised if any error happens during a Registration request
	"""


class ActivationError(PySAAError):
	"""
	Exception raised if any error happens while processing an activation
	"""


class AuthenticationError(PySAAError):
	"""
	Exceptions related to users authentication
	"""

# map from request type to AuthRequest subclasses
REQUEST_CLASSES = {
	'register': RegistrationRequest,
	'activate': ActivationRequest,
	'login': AuthenticationRequest,
	'authorize': AuthorizationRequest,
	'logout': LogoutRequest,
	'default': DefaultRequest
}


class PySAAServer(object):
	"""	
	This class provides a single interface to the API. Acts as a front
	controller, since it decides which request class must be created to 
	accomplish the requested action, based on 'type' parameter
	"""

	def handle_request(self, **data):
		"""
		Handle the request and returns result
		
		Params:
		data(dict) -- dictionary containing request parameters, could be some of these
			data['email'] -- user email
			data['pwd'] -- password (md5 hash)
			data['aid'] -- activation identifier
			data['sid'] -- session identifier
			data['oid'] -- object (resource being requested) identifier
		
		Returns:
		dict -- response contains the request parameters, and some more data that the 
		front-end could need 
			response['error'] -- error message, if there's any error processing the request
			response['result'] -- contains the result of the request
			response['email'] -- user email			
			response['aid'] -- activation identifier
			responde['sid'] -- session identifier
		"""
		# get the class from the request type
		request_class = REQUEST_CLASSES.get(data['type'], REQUEST_CLASSES['default'])
		# create instance
		request = request_class(**data)
		# process the request and return the result
		try:
			response = request.do_process()
		except PySAAError as e:
			# if any error, set result to False and set error info
			response['error'] = str(e)
			response['result'] = False

		return response


settings = utils.Settings()

if __name__ == "__main__":

	request_1 = {'type': 'register', 'email': 'mail1@test.de', 'pwd': 'xxxxxx'}

	request_2 = {'type': 'activate', 'aid': 'b5730c54e13b29feda4bcb171573e683b3712dfdc80a9b08e6bc991cb1d23fe5'}

	request_3 = {'type': 'login', 'email': 'mail1@test.de', 'pwd': 'xxxxxx1'}

	request_4 = {'type': 'authorize', 'oid': 'home',
				 'sid': '19adcecb55286e7d8f46df69e70ebcfef3297e9eff8e435bcf06d987fd4d6f44'}

	request_5 = {'type': 'logout', 'sid': '19adcecb55286e7d8f46df69e70ebcfef3297e9eff8e435bcf06d987fd4d6f44'}

	logging.basicConfig(filename='pysaa.log', level=logging.DEBUG)
	server = PySAAServer()
	logging.debug("server created")

	try:
		resp = server.handle_request(**request_3)
	except Exception as e:
		logging.exception("error processing the request: ", e)
		resp = False

	logging.debug("end...")
