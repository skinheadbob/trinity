import logging
import math
import os
import time

import boto3
from pyspark.sql import SparkSession


def get_asg_inservice_instance_count(asg_name: str, region_name: str) -> int:
    client = boto3.client('autoscaling', region_name=region_name)
    asg = client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])['AutoScalingGroups'][0]
    return sum([1 for inst in asg['Instances'] if inst['LifecycleState'] == 'InService'])


def adjust_ec2_asg(asg_name: str, region_name: str, desired_capacity: int,
                   check_interval_sec: int = 15,
                   ten_inst_timeout_sec: int = 30):
    aws_client = boto3.client('autoscaling', region_name=region_name)
    aws_client.update_auto_scaling_group(AutoScalingGroupName=asg_name,
                                         DesiredCapacity=desired_capacity,
                                         MinSize=0,
                                         MaxSize=desired_capacity)
    current_capacity = get_asg_inservice_instance_count(asg_name, region_name)
    adjust_capacity = abs(desired_capacity - current_capacity)
    timeout_sec = ten_inst_timeout_sec * math.ceil(abs(adjust_capacity) / 10)
    max_trial = int(math.ceil(timeout_sec / check_interval_sec))
    for trial in range(0, max_trial + 1):
        inservice_instance_count = get_asg_inservice_instance_count(asg_name, region_name)
        if inservice_instance_count != desired_capacity:
            time.sleep(check_interval_sec)
        else:
            return
    logging.warning('Failed to adjust the capacity of asg "%(g)s" from %(f)d to %(t)d in %(s)d seconds'
                    % {'g': asg_name, 'f': current_capacity, 't': desired_capacity, 's': timeout_sec})


def wait_on_nodes_to_join_spark_cluster(spark, desired_cluster_size: int,
                                        timeout_sec: int, check_interval_sec: int = 3):
    max_trials = int(math.ceil(timeout_sec / check_interval_sec))
    for trial in range(0, max_trials + 1):
        current_size = get_spark_worker_node_count(spark)
        if current_size != desired_cluster_size:
            time.sleep(check_interval_sec)
        else:
            return
    logging.warning('Failed to bring %(d)d nodes to Spark cluster in %(s)d seconds, current cluster size: %(c)d'
                    % {'d': desired_cluster_size, 's': timeout_sec, 'c': get_spark_worker_node_count(spark)})


def get_spark_worker_node_count(spark):
    # noinspection PyProtectedMember
    return spark.sparkContext._jsc.sc().getExecutorMemoryStatus().size() - 1


def setup_spark_session() -> SparkSession:
    from envconfig.env import env

    asg_name = env.aws_asg_name
    region_name = env.aws_region_name
    cluster_size = env.aws_cluster_size
    adjust_ec2_asg(asg_name, region_name, cluster_size)

    os.environ['PYSPARK_PYTHON'] = env.spark_pyspark_python
    os.environ['PYTHONPATH'] = env.spark_pythonpath

    spark = SparkSession.builder \
        .master(env.spark_master) \
        .appName('Trinity %(e)s' % {'e': env.env}) \
        .config('spark.executor.uri', env.spark_executor_uri) \
        .config('spark.sql.shuffle.partitions', env.spark_sql_shuffle_partitions) \
        .config('spark.driver.memory', env.spark_driver_memory) \
        .config('spark.executor.memory', env.spark_executor_memory) \
        .getOrCreate()

    wait_on_nodes_to_join_spark_cluster(spark, env.aws_cluster_size, env.aws_cluster_size * 10)

    return spark


def prep_notebook(spark, aws_cluster_size: int = None, aws_asg_name: str = None, aws_region_name: str = None,
                  setup_spark_cluster_timeout_sec: int = None):
    from envconfig.env import env

    if aws_cluster_size is None:
        aws_cluster_size = env.aws_cluster_size
    if aws_asg_name is None:
        aws_asg_name = env.aws_asg_name
    if aws_region_name is None:
        aws_region_name = env.aws_region_name

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.info('Adjusting AWS autoscaling group "%(g)s" capacity to %(c)d ...'
                 % {'g': aws_asg_name, 'c': aws_cluster_size})
    adjust_ec2_asg(aws_asg_name, aws_region_name, aws_cluster_size)

    logging.info('Waiting for workers to join Spark cluster ...')
    if setup_spark_cluster_timeout_sec is None:
        setup_spark_cluster_timeout_sec = aws_cluster_size * 20
    wait_on_nodes_to_join_spark_cluster(spark, aws_cluster_size, setup_spark_cluster_timeout_sec)

    logging.info('Notebook and Spark cluster are standing by')


def shutdown_notebook(aws_asg_name: str = None, aws_region_name: str = None):
    from envconfig.env import env

    if aws_asg_name is None:
        aws_asg_name = env.aws_asg_name
    if aws_region_name is None:
        aws_region_name = env.aws_region_name

    logging.info('Shutting down AWS autoscaling group "%(g)s" by adjusting capacity to 0'
                 % {'g': aws_asg_name})
    adjust_ec2_asg(aws_asg_name, aws_region_name, 0)
