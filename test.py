from datetime import datetime
from decimal import *

import psycopg2.sql
from pyspark.sql.types import *

s3_bucket_name = None
s3_iam_role = None
conn_config = None

# reference: https://docs.aws.amazon.com/redshift/latest/dg/c_Supported_data_types.html
query_sql = """
WITH types AS ( 
    SELECT
        CAST( 1 AS SMALLINT) AS rank_,
        CAST( 42 AS SMALLINT) AS smallint_,
        CAST( 42 AS INTEGER) AS integer_,
        CAST( 42 AS BIGINT) AS bigint_, 
        CAST( 42.42 AS DECIMAL(8,4) ) AS decimal_, CAST( 42.42 AS DECIMAL) AS default_decimal_,  
        CAST( 42.42 AS REAL ) AS real_, 
        CAST( 42.42 AS DOUBLE PRECISION) AS double_precision_,
        CAST( 'True' AS BOOLEAN) AS boolean_,
        CAST( 'char' AS CHAR(4)) AS char_,
        CAST( 'varchar' AS VARCHAR(16)) AS varchar_,
        CAST( '2019-06-06' AS DATE) AS date_),
null_types AS (
    SELECT
        CAST( 0 AS SMALLINT) AS rank_,
        CAST( NULL AS SMALLINT) AS smallint_,
        CAST( NULL AS INTEGER) AS integer_,
        CAST( NULL AS BIGINT) AS bigint_, 
        CAST( NULL AS DECIMAL(8,4) ) AS decimal_, CAST( NULL AS DECIMAL) AS default_decimal_,  
        CAST( NULL AS REAL ) AS real_, 
        CAST( NULL AS DOUBLE PRECISION) AS double_precision_,
        CAST( NULL AS BOOLEAN) AS boolean_,
        CAST( NULL AS CHAR(4)) AS char_,
        CAST( NULL AS VARCHAR(16)) AS varchar_,
        CAST( NULL AS DATE) AS date_),
all_ AS (
    SELECT * FROM null_types UNION SELECT * FROM types
)
SELECT * FROM all_ ORDER BY rank_
"""

col_sql = '{} LIMIT 0'.format(query_sql)

with psycopg2.connect(conn_config) as conn:
    cur = conn.cursor()
    cur.execute(col_sql)
    desc = cur.description

CODE_SPTYPE_DICT = {
    21: IntegerType,
    23: IntegerType,
    20: LongType,
    1700: DecimalType,
    700: FloatType,
    701: DoubleType,
    16: BooleanType,
    1042: StringType,
    1043: StringType,
    1082: DateType,
    1114: TimestampType,
    1184: TimestampType
}


def _desc_to_struct_type(desc_) -> StructType:
    def _desc_to_struct_field(d) -> StructField:
        col_name = d.name
        type_code = d.type_code
        if type_code not in CODE_SPTYPE_DICT:
            raise TypeError('unsupported type_code "{}" (column={})'.format(type_code, col_name))

        type_class = CODE_SPTYPE_DICT[type_code]
        if type_class is DecimalType:
            type_ = DecimalType(precision=d.precision, scale=d.scale)
        else:
            type_ = type_class()

        return StructField(col_name, type_, nullable=True)

    return StructType([_desc_to_struct_field(desc_) for desc_ in desc_])


schema = _desc_to_struct_type(desc)

_s3_prefix = 'dev/bjia/trinity/dummy_dataframe_{}/'.format(datetime.now().strftime('%Y%m%d%H%M%S'))
unload_sql = psycopg2.sql.SQL("""
    UNLOAD($$
        {query_sql}
    $$)
    TO 's3://{bucket}/{prefix}/'
    IAM_ROLE '{iam_role}'
    CSV
    HEADER
    PARALLEL ON
    MAXFILESIZE 10MB
    ALLOWOVERWRITE """.format(
    query_sql=query_sql,
    bucket=s3_bucket_name,
    prefix=_s3_prefix.rstrip('/'),
    iam_role=s3_iam_role))

with psycopg2.connect(conn_config) as conn:
    cur = conn.cursor()
    cur.execute(unload_sql)

print('.csv files dumped to S3: ' + _s3_prefix)

print('done')


def convert_row(row_, schema_):
    import dateutil.parser as dp

    def parse_bool(s) -> bool:
        if str(s).lower() in ['t', 'true']:
            return True
        if str(s).lower() in ['f', 'false']:
            return False
        raise ValueError('cannot convert "{}" to bool'.format(s))

    def convert_field(field):
        name = field.name
        type_ = type(field.dataType)
        original = row_[name]

        if original is None:
            converted = None
        elif type_ is IntegerType or type_ is LongType:
            converted = int(original)
        elif type_ is DecimalType:
            converted = Decimal(str(original))
        elif type_ is FloatType or type_ is DoubleType:
            converted = float(original)
        elif type_ is BooleanType:
            converted = parse_bool(original)
        elif type_ is StringType:
            converted = str(original)
        elif type_ is DateType or type_:
            converted = dp.parse(original).date()
        elif type_ is TimestampType or type_ is TimestampType:
            converted = dp.parse(original)
        else:
            raise RuntimeError('field type "{}" is not supported'.format(type_))

        return name, converted

    from collections import OrderedDict
    return OrderedDict([convert_field(f) for f in schema.fields])
    # from pyspark.sql import Row
    # return Row(**pairs)
