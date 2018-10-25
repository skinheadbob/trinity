import logging
import os
from configparser import ConfigParser
from threading import Lock

_ENV = os.getenv('TRINITY_ENV', 'DEV')
_ENV_LIST = ['DEV', 'QA', 'PROD']
_CP = ConfigParser()
_CP.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))
_LOCK = Lock()


def chenv(env_: str):
    with _LOCK:
        env_ = env_.upper()
        if env_ not in _ENV_LIST:
            raise ValueError('cannot set env to "%(e)s", must be one of %(l)s'
                             % {'e': env_, 'l': str(_ENV_LIST)})
        global _ENV
        _ENV = env_
        logging.info('setting env to ' + env_)


class ClassProperty(object):
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


# noinspection PyPep8Naming
class env:
    @ClassProperty
    def env(self) -> str:
        return _ENV

    @ClassProperty
    def aws_region_name(self) -> str:
        return _get('aws_region_name')

    @ClassProperty
    def aws_cluster_size(self) -> int:
        return int(_get('aws_cluster_size'))

    @ClassProperty
    def s3_bucket_name(self) -> str:
        return _get('s3_bucket_name')

    @ClassProperty
    def s3_iam_role(self) -> str:
        return _get('s3_iam_role')

    @ClassProperty
    def rs_conn_config(self) -> str:
        return _get('rs_conn_config')

    @ClassProperty
    def aws_asg_name(self) -> str:
        return _get('aws_asg_name')

    @ClassProperty
    def spark_pyspark_python(self) -> str:
        return _get('spark_pyspark_python')

    @ClassProperty
    def spark_pythonpath(self) -> str:
        return _get('spark_pythonpath')

    @ClassProperty
    def spark_master(self) -> str:
        return _get('spark_master')

    @ClassProperty
    def spark_executor_uri(self) -> str:
        return _get('spark_executor_uri')

    @ClassProperty
    def spark_sql_shuffle_partitions(self) -> int:
        return int(_get('spark_sql_shuffle_partitions'))

    @ClassProperty
    def spark_driver_memory(self) -> str:
        return _get('spark_driver_memory')

    @ClassProperty
    def spark_executor_memory(self) -> str:
        return _get('spark_executor_memory')


def _get(prop: str):
    prop = prop.lower()
    return _CP.get(_ENV, prop)
