"""
This package implements a Simple Authentication / Authorization API (PySAA) using Python 3

The package contains these modules:
dbapi -- manages database access logic
model -- contains the classes that represent data model
server -- implements the logic of PySAA
settings -- contains configuration settings
utils -- common utilities
"""
SETTINGS_MODULE = "pysaa.settings"

__all__ = ["server", "model", "dbapi", "utils", "settings"]