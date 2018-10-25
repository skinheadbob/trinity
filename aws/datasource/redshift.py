from abc import abstractmethod

import pandas as pd
import pandas.io.sql as sqlio
import psycopg2
from pyspark.sql import DataFrame, SparkSession

import aws.rsutil as util
from datasource.query import Query
from datasource.spec import Mode


class SqlQuery(Query):
    def __init__(self,
                 mode: Mode,
                 conn_config: str,

                 spark: SparkSession = None,
                 s3_iam_role: str = None,
                 s3_bucket_name: str = None,
                 s3_prefix: str = None):
        super().__init__(mode)

        self._conn_config = conn_config

        self._spark = spark
        self._s3_iam_role = s3_iam_role
        self._s3_bucket_name = s3_bucket_name
        self._s3_prefix = s3_prefix

    def _load_spark_df(self) -> DataFrame:
        if not self.can_load_spark_df:
            raise RuntimeError('cannot load Spark dataframe, are Spark/S3 parameters passed in constructor?')

        query_sql = self.query_sql
        spark = self._spark
        conn_config = self._conn_config
        s3_iam_role = self._s3_iam_role
        s3_bucket_name = self._s3_bucket_name
        s3_prefix = self.s3_prefix

        return util.load_spark_df(query_sql, spark, conn_config,
                                  s3_iam_role, s3_bucket_name, s3_prefix)

    def _load_pandas_df(self) -> pd.DataFrame:
        query_sql = self.query_sql
        conn_config = self._conn_config

        with psycopg2.connect(conn_config) as conn:
            to_ret = sqlio.read_sql_query(query_sql, conn)
            return to_ret

    @property
    @abstractmethod
    def query_sql(self) -> str:
        pass

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def s3_prefix(self) -> str:
        return self._s3_prefix.rstrip('/') + '/'

    @property
    def can_load_spark_df(self):
        return self._spark is not None \
               and self._s3_iam_role is not None \
               and self._s3_bucket_name is not None \
               and self._s3_prefix is not None


class RandomSqlQuery(SqlQuery):
    def __init__(self,
                 query_sql: str,
                 mode: Mode,
                 conn_config: str,

                 spark: SparkSession = None,
                 s3_iam_role: str = None,
                 s3_bucket_name: str = None,
                 s3_prefix: str = None):
        super().__init__(mode, conn_config, spark, s3_iam_role, s3_bucket_name, s3_prefix)
        self._query_sql = query_sql

    @property
    def query_sql(self) -> str:
        return self._query_sql
