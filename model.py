"""
model.py

This module implements a ORM layer for mapping data from app domain to database
All the entities descend from EntityBase, which has the common logic
necessary to implement CRUD functionality

Each entity must specify the next class properties:
 table: name of the table where the Entity data is persisted
 id: name of the primary key of the table
 columns: tuple containing the names of the columns except the id column

"""

from pysaa import dbapi


class EntityBase(object):
	"""
	This is the generic class for model entities
	Contains common logic that generates the SQL statements to get / persist
	the entities from / to database
	"""

	def __init__(self, db, id=None):
		"""
		Initializes all columns to None values, and then tries to
		get values from database, if id is specified in the arguments
		
		Arguments:
		db (dbapi.Db)-- Database adapter object
		id -- object unique id (primary key)
		"""
		self._db = db

		# if id is passed, try to get the entity
		if id:
			self.get(id)
		else:
			# set values to None
			self.id = None
			for k in self.columns:
				setattr(self, k, None)

	def __str__(self):
		"""
		stringfy object, concatenates column:value pairs
		
		Returns:
		str -- contains columns:values of this entity
		"""
		st = ["id: %s" % self.id]
		for k in self.columns:
			st.append("%s: %s" % (k, getattr(self, k, "")))
		return self.__class__.__name__ + ": {" + ", ".join(st) + " }"

	def __bool__(self):
		"""
		Is this object empty? 
		Returns:
		bool -- True if any value is set, False if no value is set
		"""
		for k in self.columns:
			if getattr(self, k, None):
				return True
		return False

	def get(self, id):
		"""
		Retrieve object from database and save values in this instance
		
		Arguments:
		id -- entity identifier (primary key)
		
		Raises:
		dbapi.DbError -- if any error happens while reading from database or 
		if there's more than one entity for the given id
		"""
		sql = "select * from %s where %s = {0}" % (
		self.table, self.table_id)
		try:
			self._db.execute_sql(sql, id)
		except dbapi.DbError as e:
			raise e

		# if no errors, get result
		result = self._db.get_result()

		# if len(result) == 0:
		# entity is not stored in database, do nothing,
		# an empty object will be returned 

		if len(result) > 1:
			# there must be only one entity for a unique id
			raise dbapi.DbError("not a singular entity <class %s> id = %s" %
								(self.__class__, id))

		if len(result) == 1:
			self.id = id  # set id
			self.set(**result[0])  # set values from result

	def set(self, **kw):
		"""
		Set values from a dictionary in this object
		
		Arguments:
		kw -- dictionary containing values to be set
		
		Raises:
		dbapi.DbError -- if a wrong column name is specified in the dictionary
		"""
		for k, v in kw.items():
			if not (k in self.columns):
				raise dbapi.DbError("unknown column: %s" % k)
			setattr(self, k, v)

	def save(self):
		"""
		Store this object in database. If self.id is not set, that means 
		this is a new object, then insert it. If it's set, then update
		
		Returns:
		bool -- True if the object is saved without errors
		
		Raises:
		dbapi.DbError -- if any error happens while saving the object
		"""
		if self.id:
			return self.update()
		return self.insert()

	def insert(self):
		"""
		Insert this object in database. If no errors, get the the id returned 
		and set its value
		
		Returns:
		bool -- True if the object has been inserted
		
		Raises:
		dbapi.DbError -- if any error happens while writing in database
		"""
		cols = []  # column names
		nvals = []
		vals = {}  # value for each column

		# id = getattr(self, self.table_id, None)
		# if id:
		# cols.append(self.table_id)
		# vals.append(id)

		for k in self.columns:
			# id column should be set when id is not autonumeric
			v = getattr(self, k, None)
			if not v is None:  #don't insert null values
				cols.append(k)
				nvals.append("{%s}" % k)  #{column}
				vals[k] = v

		cols = ", ".join(cols)  #colum_1, column_2,...column_n
		nvals = ", ".join(nvals)  #{column_1}, {column_2},...{column_n}
		sql = "insert into %s (%s) values(%s)" % (
		self.table, cols, nvals)

		try:
			self._db.execute_sql(sql, vals)
		except dbapi.DbError as e:
			raise e

		#if no errors, get the id of this object
		#if it's autonumeric get lastrowid, or get table_id value 
		self.id = self._db.get_lastrowid() or getattr(self, self.table_id)
		return True

	def update(self):
		"""
		Updates entity values in database. 
		
		Returns:
		bool -- True if the object has been updated
		
		Raises:
		DbError -- if the entity is not in database or there's more than
		one entity with the same id or any other error happens while updating
		"""
		cols = []  # column being updated
		vals = {}  # values being updated
		for k in self.columns:
			v = getattr(self, k, None)
			if not v is None:  # don't update null values
				# generate replacement fields: column_name = {column_name}
				cols.append("%s={%s}" % (k, k))
				vals[k] = v
		cols = ", ".join(cols)  # column_1={column_1}, column_2={column_2},...
		# generate sql with the replacement fields 
		sql = "update %s set %s where %s = %s" % (
		self.table,
		cols,
		self.table_id,
		self.id)
		try:
			self._db.execute_sql(sql, vals)
		except dbapi.DbError as e:
			raise e

		if self._db.get_row_count() == 0:
			raise dbapi.DbError("update entity %s id = %s not stored in database" %
								(self.__class__, self.id))

		if self._db.get_row_count() != 1:
			raise dbapi.DbError("update entity %s id = %s not a singular entity" %
								(self.__class__, self.id))

		return True

	def delete(self):
		"""
		Delete this entity 
		
		Returns:
		True if the object has been deleted
		
		Raises:
		DbError -- if the entity is not in database or there's more than
		one entity with the same id or any other error happens while deleting
		"""
		sql = "delete from %s where %s = %s" % (
		self.table, self.table_id, self.id)
		try:
			self._db.execute_sql(sql)
		except dbapi.DbError as e:
			raise e

		if self._db.get_row_count() == 0:
			raise dbapi.DbError("delete entity %s id = %s not stored in database" %
								(self.__class__, id))

		if self._db.get_row_count() != 1:
			raise dbapi.DbError("delete entity %s id = %s not a singular entity" %
								(self.__class__, id))

		return True

	def list(self, order=None, sort=None, **kw):
		"""
		Makes a custom query. Finds the entities with the given criterions
		
		Arguments:
		kw -- column:value pairs used to filter the query
		order -- sort the result by this column, must be one of the columns given in kw
		sort -- 'asc' ascending or 'desc' descending order
		
		Returns:
		list -- A list containing the entities that match the specified criterions
		"""
		sql = "select * from %s" % self.table

		orderby = ""
		if not order is None:
			if sort is None or sort.lower() != "asc":
				sort = "desc"
			orderby = "order by %s %s" % (order, sort)
		if len(kw):
			filter = []
			for k in kw.keys():
				if not (k in self.columns):
					raise dbapi.DbError("unknown column: %s" % k)
				filter.append("%s={%s}" % (k, k))  # column_name={column_name}
			where = " where " + " and ".join(filter)
			sql += where  # append where condition

		sql += orderby  # append order by

		try:
			self._db.execute_sql(sql, kw)
		except dbapi.DbError as e:
			raise e

		result = self._db.get_result()
		# build list of entities from result
		entities = []
		for row in result:
			entity = self.__class__(self._db)
			entity.set(**row)
			entity.id = row[self.table_id]
			entities.append(entity)

		return entities


class User(EntityBase):
	STATUS_INACTIVE = 0
	STATUS_ACTIVE = 1
	STATUS_BLOCKED = 2

	table = 'users'
	table_id = 'user_id'
	columns = ('user_id', 'email', 'password', 'status', 'role_id')


class Activation(EntityBase):
	table = 'activations'
	table_id = 'user_id'
	columns = ('user_id', 'activation_id', 'created')


class Login(EntityBase):
	STATUS_REFUSED = 0
	STATUS_ACCEPTED = 1

	table = 'logins'
	table_id = 'user_id'
	columns = ('user_id', 'session_id', 'status', 'attempts', 'created')


class Permission(EntityBase):
	table = 'permissions'
	table_id = 'permission_id'
	columns = ('permission_id', 'role_id', 'object_id')


class Role(EntityBase):
	ROLE_ANONYMOUS = 1
	ROLE_STANDARD = 2
	ROLE_EXTENDED = 3

	table = 'roles'
	table_id = 'role_id'
	columns = ('role_id', 'parent_id')  # add name/description? actually we don't need it


if __name__ == "__main__":
	import logging

	logging.basicConfig(filename='pysaa.log', level=logging.DEBUG)
	logging.debug("testing model.py")
	try:
		db = dbapi.DbFactory().get_db()
		user = User(db)
		user.set(email="aaaa@test.tt", password="xxxxx", status=User.STATUS_INACTIVE, role_id=Role.ROLE_STANDARD)
		user.save()
		db.commit()
		logging.debug(user)

		act = Activation(db)
		act.set(user_id=user.id, activation_id="ooooo", created=123456789)
		act.save()
		db.commit()
		logging.debug(act)

		acl = act.list(activation_id="ooooo")
		act = acl[0]
		act.delete()
		db.commit()

		acl = act.list(activation_id="ooooo")
		logging.debug(acl)
		db.commit()

		log = Login(db)
		log.set(user_id=user.id, session_id="abcdefghijkl", status=log.STATUS_ACCEPTED, attempts=0, created=12345662)
		log.save()
		logging.debug(log)

		log.session_id = "000000000000aaaaaaaaaaaaaaaa"
		log.created = 87237333
		log.save()
		db.commit()
	except Exception as e:
		logging.exception("error", e)
	finally:
		logging.debug("testing finished...")
		db.commit()
		db.close_cursor()
		db.close_connection()
	