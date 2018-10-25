from concurrent.futures import ThreadPoolExecutor

import boto3
import psycopg2
import psycopg2.sql
from pyspark import RDD
from pyspark.sql import SparkSession, DataFrame


def load_spark_df(query_sql: str, spark: SparkSession, conn_config: str,
                  s3_iam_role: str, s3_bucket_name: str, s3_prefix: str) -> DataFrame:
    def fetch_cols(conn_):
        cols_sql = '%(query)s LIMIT 0' % {'query': query_sql}
        cur = conn_.cursor()
        cur.execute(cols_sql)
        return [desc[0] for desc in cur.description]

    with ThreadPoolExecutor(max_workers=2) as pool:
        rdd_future = pool.submit(load_rdd,
                                 query_sql, spark, conn_config,
                                 s3_iam_role, s3_bucket_name, s3_prefix)
        with psycopg2.connect(conn_config) as conn:
            cols_future = pool.submit(fetch_cols, conn)

        cols = cols_future.result()

        rdd = rdd_future.result()
        from pyspark.sql.types import StringType, StructType, StructField
        # 'StringType' does not seem to impact operations such as 'SUM'
        schema = StructType([StructField(col, StringType(), True) for col in cols])
        return spark.createDataFrame(rdd, schema)


def load_rdd(query_sql: str,
             spark: SparkSession,
             conn_config: str,
             s3_iam_role: str, s3_bucket_name: str, s3_prefix: str) -> RDD:
    if not is_s3_dir_empty(s3_bucket_name, s3_prefix):
        raise RuntimeError('refuse to unload Redshift to S3 because the "S3 dir" is NOT empty: %(p)s'
                           % {'p': s3_prefix})

    with psycopg2.connect(conn_config) as conn:
        unload_sql = psycopg2.sql.SQL("""
            UNLOAD($$
                %(query)s
            $$)
            TO 's3://%(bucket)s/%(prefix)s'
            IAM_ROLE '%(iam_role)s'
            DELIMITER ','
            ESCAPE
            PARALLEL ON
            MAXFILESIZE 25MB
            ALLOWOVERWRITE
        """ % {
            'query': query_sql,
            'bucket': s3_bucket_name,
            'prefix': s3_prefix,
            'iam_role': s3_iam_role
        })
        conn.cursor().execute(unload_sql)

        s3_keys = []
        for obj in boto3.session.Session().resource('s3').Bucket(s3_bucket_name).objects.filter(Prefix=s3_prefix):
            s3_keys.append(obj.key)

        def read_s3_obj_to_lines(s3_key: str):
            from io import StringIO
            import csv
            s3_obj = boto3.session.Session().client('s3').get_object(Bucket=s3_bucket_name, Key=s3_key)['Body']
            return list(csv.reader(StringIO(s3_obj.read().decode('utf-8')), escapechar='\\'))

        return spark.sparkContext.parallelize(s3_keys).flatMap(read_s3_obj_to_lines)


def is_s3_dir_empty(s3_bucket_name: str, s3_prefix: str):
    is_empty = True
    import boto3
    for _ in boto3.session.Session().resource('s3').Bucket(s3_bucket_name).objects.filter(Prefix=s3_prefix):
        is_empty = False
        break
    return is_empty
