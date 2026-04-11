import os
from configparser import ConfigParser

config_filepath = f"{os.path.dirname(os.path.realpath(__file__))}/compiler.properties"
if not os.path.exists(config_filepath):
    raise Exception(f"Config file {config_filepath} not found")

config = ConfigParser()
config.read(config_filepath)

DB_HOST = config.get("db", "host")
DB_NAME = config.get("db", "name")
DB_USER = config.get("db", "user")
DB_PASSWORD = config.get("db", "password")
DB_PORT = config.get("db", "port")

SOURCE_SCHEMA = config.get("schema", "source")
TEST_SCHEMA = config.get("schema", "test")

DEFAULT_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "log")