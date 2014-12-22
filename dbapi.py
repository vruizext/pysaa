"""
dbapi.py

This module provides a database access API, hiding database
specific implementation details
"""

import importlib
import logging

from pysaa.utils import Settings


def dbconn(in_trx=False):
	"""
	Decorator function, provides database connection to the function. 
	
	Arguments:
	in_trx(bool) -- If in_trx is True the function is called inside a database 
	transaction. If a DbError exception is raised while executing the
	function, the transaction is rolled back. If not, it's committed.
	"""

	def _dbconn(func):
		def _dbconn_(self, *args, **kw):
			db = DbFactory().get_db()
			self.db = db
			if in_trx:  # Don't allow nested transactions
				db.rollback()  # rollback previous transactions

			try:
				ret = func(self, db, *args, **kw)
				db.commit()
			except DbError as e:
				print(e)
				logging.exception("database error: ", e)
				if in_trx:
					db.rollback()
				ret = False
			finally:
				db.close_cursor()
				db.close_connection()
			return ret

		return _dbconn_

	return _dbconn


def get_class(class_name):
	"""
	Returns class object from the class name and the module name 
	
	Arguments:
	class_name(str) -- class that is searched

	Returns:
	class -- class object with the requested class
	"""
	import sys

	return getattr(sys.modules[__name__], class_name, None)


class DbFactory(object):
	"""
	Factory object, creates instances of Db objects on demand
	"""

	_instance = None

	def __new__(cls):
		if DbFactory._instance is None:
			settings = Settings()
			if len(settings.DATABASE) == 0:
				raise DbError("database settings not found")
			# create DbFactory instance
			DbFactory._instance = object.__new__(cls)
			#get database settings
			DbFactory._instance._config = settings.DATABASE['config']
			#get concrete Db class to be created
			DbFactory._instance._db_class = get_class(settings.DATABASE['class'])
			#import db module
			DbFactory._instance.get_db_module

		return DbFactory._instance

	def get_db(self):
		"""
		Create new instance of DB adapter class
		Specific db_class created is injected from settings module
		
		Returns:
		Db -- instance of the concrete Db class
		"""
		try:  # create db instance
			db = self._db_class(**self._config)
			#set reference to db module
			db._db = self._db_module
		except Exception as e:
			raise DbError("Could not create class '%s': %s" %
			              (self._db_class, e))
			db = None

		return db

	@property
	def get_db_module(self):
		"""
		Import module used for connecting with database
		Database module name to be loaded must be specified in the db_class
		
		Returns:
		module -- A reference to the imported module, if it could be imported. 
		None -- if the module could not be imported
		"""

		try:
			self._db_module = importlib.import_module(self._db_class._module)
		except ImportError as e:
			self._db_module = None
			raise DbError("Could not import module '%s'" %
			              self._db_class._module)(e)

		return self._db_module


class Db(object):
	"""
	Database adapter class, which provides access to database
	using Python DB API 2.0
	"""

	def __init__(self, **kw):
		"""
		init db class and create connection
		"""
		self._conn = None  # connection object
		self._cursor = None  # cursor object
		self._config = kw  # database connection settings
		self._cursor_class = None  # cursor class

	def get_connection(self):
		"""
		Returns the connection object. If there's no connection, 
		first tries to connect 
		
		Returns:
		Connection -- the connection to database. 
		"""
		if self._conn is None:
			self._conn = self._db.connect(**self._config)
			# alias to access database specific errors (DB API 2.0)
			self.exceptions = self._conn
		return self._conn

	def close_connection(self):
		"""
		Closes current database connection if it exists
		"""
		self._conn.close()
		self._conn = None

	def get_cursor(self):
		"""
		Returns a cursor. Keeps the object reference, in order to reuse it
		
		Returns:
		Cursor -- a database cursor
		"""
		if self._cursor is None:
			self._cursor = self.get_connection().cursor(self._cursor_class)
		return self._cursor

	def close_cursor(self):
		"""
		Closes cursor, if it exists and it's still open
		"""
		self._cursor.close()
		self._cursor = None

	def execute_sql(self, sql, *args):
		"""
		Executes sql statement
		
		Arguments:
		sql(string) -- the sql statement to be executed
		args (dict or list) -- args contains the replacement values, 
		if sql statement is a prepared statement
		"""
		try:
			self.get_cursor()
			self._cursor.execute(sql, *args)
		except self.exceptions.Error as e:
			logging.debug("sql: ", sql)
			raise DbError("Error executing sql statement: %s" % sql)(e)

	def get_result(self):
		"""
		Returns:
		list -- results of last SQL query
		"""
		return self._cursor.fetchall()

	def get_row_count(self):
		"""
		Returns:
		int -- number of rows affected by the last SQL statement
		"""
		return self._cursor.rowcount

	def get_lastrowid(self):
		"""
		Returns:
		ID of the row inserted in the last SQL statement
		"""
		return self._cursor.lastrowid

	def commit(self):
		"""
		Commits current database transaction
		"""
		self._conn.commit()

	def rollback(self):
		"""
		Rolls back current database transaction
		"""
		self._conn.rollback()


class MySqlDb(Db):
	"""
	MySQL specific database adapter. Uses module MySQLdb
	"""

	_module = 'MySQLdb'  # module name

	def __init__(self, **kw):
		"""
		Specific implementation, uses DictCursor to get results rows as dictionaries
		"""
		super().__init__(**kw)
		try:
			cursors = importlib.import_module('MySQLdb.cursors')
			self._cursor_class = getattr(cursors, 'DictCursor')
		except Exception as e:
			raise DbError("couldn't load DictCursor: %s" % e)


class SQLiteDb(Db):
	"""
	MySQL specific database adapter. Uses module sqlite3
	"""

	_module = 'sqlite3'

	def get_connection(self):
		"""
		Specific implementation for sqlite3
		Transform rows with integer keys to dictionaries
		"""
		Db.get_connection(self)
		self._conn.row_factory = self._db.Row


class DbError(Exception):
	"""
	Wraps  exceptions coming from database
	"""


if __name__ == "__main__":
	logging.basicConfig(filename='pysaa.log', level=logging.DEBUG)
	logging.debug("testing dbapi.py")
	try:
		db = DbFactory().get_db()
		sql = "select * from users"
		db.get_cursor()
		db.execute_sql(sql)
		logging.debug("sql: %s" % sql)
		list = db.get_result()
		[logging.debug(u) for u in list]
	except Exception as e:
		logging.exception("exception ", e)
	finally:
		db.close_cursor()
		db.close_connection()