#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
# A python module that creates a database access context based on the deplyment
# environment.
#
# The context is a dictionary that contains all the required fields to make
# a database connection.
#
#
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from os import environ as env

# Keys to the context map
SCHEMA_NAME = 'schema_name'
DB_NAME = 'db_name'
USER_NAME = 'user_name'
ADMIN_NAME = 'admin_name'
CONTEXT_NAME = 'context_name'

# The possible connections
POSTGRES = 'postgres'
REF_POSTGRES = 'ref_postgres'
POSTGRES_DB = 'postgres_db'
REF_POSTGRES_DB = 'ref_postgres_db'
DB_ADMIN = 'db_admin'
REF_DB_ADMIN = 'ref_db_admin'
DB_USER = 'db_user'
REF_DB_USER = 'ref_db_user'


# deployment = env.get("DEPLOYMENT")
deployment = "unit"

# The geo db deployment for this container
geo_db_port = env.get("AIRSPACE_DB_SERVICE_PORT")
geo_db_hostname = env.get("AIRSPACE_DB_SERVICE_HOST")

# Local test settings for geo db
# geo_db_port = "31700"
# geo_db_hostname = "192.168.0.12"

# The ref db deployment for this container
ref_db_port = env.get("REFERENCE_DB_SERVICE_PORT")
ref_db_hostname = env.get("REFERENCE_DB_SERVICE_HOST")

# Local test settings for ref db
# ref_db_port = "31700"
# ref_db_hostname = "192.168.0.12"


username = deployment + '_user'
adminname = deployment + '_admin'
dbname = deployment + '_data'
user_db_password = env.get('USER_DB_PASSWORD')
admin_db_password = env.get('ADMIN_DB_PASSWORD')
postgres_db_password = env.get('POSTGRES_DB_PASSWORD')


# Context contains the connection string and connection details for the
# database.
CONTEXT = {'context_name': deployment,
           'user_name': username,
           'admin_name': adminname,
           'schema_name': deployment,
           'db_name': deployment + '_data',
           # GEO DB CONNECTIONS
           'connect_str_postgres': "dbname='postgres' " +
                                   "user='postgres' " +
                                   "host=" + geo_db_hostname +
                                   " port=" + geo_db_port +
                                   " password=" + "password",
           'connect_str_postgres_db': "dbname=" + dbname +
                                      " user='postgres' " +
                                      "host=" + geo_db_hostname +
                                      " port=" + geo_db_port +
                                      " password=" + "password",
           'connect_str_db_admin': "dbname=" + dbname +
                                   " user=" + adminname +
                                   " host=" + geo_db_hostname +
                                   " port=" + geo_db_port +
                                   " password=" + "password",
           'connect_str_db_user': "dbname=" + dbname +
                                  " user=" + username +
                                  " host=" + geo_db_hostname +
                                  " port=" + geo_db_port +
                                  " password=" + "password",
           # REF DB CONNECTIONS
           'connect_str_ref_postgres': "dbname='postgres' " +
                                  "user='postgres' " +
                                  "host=" + ref_db_hostname +
                                  " port=" + ref_db_port +
                                  " password=" + "password",
           'connect_str_ref_postgres_db': "dbname=" + dbname +
                                  " user='postgres' " +
                                  "host=" + ref_db_hostname +
                                  " port=" + ref_db_port +
                                  " password=" + "password",
           'connect_str_ref_db_admin': "dbname=" + dbname +
                                  " user=" + adminname +
                                  " host=" + ref_db_hostname +
                                  " port=" + ref_db_port +
                                  " password=" + "password",
           'connect_str_ref_db_user': "dbname=" + dbname +
                                   " user=" + username +
                                   " host=" + ref_db_hostname +
                                   " port=" + ref_db_port +
                                   " password=" + "password"}


def get_connection(CONTEXT, connectionType):
    """
    Create a valid connection.
    """
    if connectionType in {POSTGRES, POSTGRES_DB, DB_ADMIN, DB_USER, REF_POSTGRES, REF_POSTGRES_DB, REF_DB_ADMIN, REF_DB_USER}:
        connectionString = CONTEXT["connect_str_" + connectionType]
        connection = psycopg2.connect(connectionString)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return connection
    else:
        return None
