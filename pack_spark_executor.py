import os
import requests
import shutil
import tarfile

# change working directory to 'here'
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# FIXME 'PYSPARK_PYTHON' needs to be more flexible
spark_env_conf = os.linesep.join([
    'export PYSPARK_PYTHON=/root/trinity/conda/envs/trinity/bin/python',
    'export PYTHONPATH=$SPARK_HOME/py_modules:$PYTHONPATH'
])

base_dir = 'build'
SPARK_VER = '2.4.3'
AWS_SDK_VER = '1.7.4'

if not os.path.exists(base_dir):
    os.makedirs(base_dir)

spark_tmpl_url = 'http://apache.mirror.cdnetworks.com/spark/spark-%(spark_ver)s/spark-%(spark_ver)s-bin-hadoop2.7.tgz' \
                 % {'spark_ver': SPARK_VER}

spark_tmpl_name = spark_tmpl_url.split('/')[-1]
spark_tmpl_path = base_dir + '/' + spark_tmpl_name

print('downloading template spark package...')
if not os.path.exists(spark_tmpl_path):
    r = requests.get(spark_tmpl_url, stream=True)
    with open(spark_tmpl_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

aws_java_sdk_jar_url = \
    'http://central.maven.org/maven2/com/amazonaws/aws-java-sdk/%(aws_sdk_ver)s/aws-java-sdk-%(aws_sdk_ver)s.jar' \
    % {'aws_sdk_ver': AWS_SDK_VER}
aws_java_sdk_jar_path = base_dir + '/' + aws_java_sdk_jar_url.split('/')[-1]
print('downloading aws-java-sdk jar...')
if not os.path.exists(aws_java_sdk_jar_path):
    r = requests.get(aws_java_sdk_jar_url, stream=True)
    with open(aws_java_sdk_jar_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

hadoop_aws_jar_url = \
    'http://central.maven.org/maven2/org/apache/hadoop/hadoop-aws/2.7.3/hadoop-aws-2.7.3.jar'
hadoop_aws_jar_path = base_dir + '/' + hadoop_aws_jar_url.split('/')[-1]
print('downloading hadoop-aws jar...')
if not os.path.exists(hadoop_aws_jar_path):
    r = requests.get(hadoop_aws_jar_url, stream=True)
    with open(hadoop_aws_jar_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

print('unpacking template spark package...')
spark_tmpl_dir = spark_tmpl_path[:-4]
shutil.rmtree(spark_tmpl_dir, ignore_errors=True)
with tarfile.open(spark_tmpl_path, 'r') as t:
    def is_within_directory(directory, target):
        
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
    
        prefix = os.path.commonprefix([abs_directory, abs_target])
        
        return prefix == abs_directory
    
    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
    
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            if not is_within_directory(path, member_path):
                raise Exception("Attempted Path Traversal in Tar File")
    
        tar.extractall(path, members, numeric_owner=numeric_owner) 
        
    
    safe_extract(t, path=base_dir)

print('copying my python modules to spark package...')
py_module_dir = spark_tmpl_dir + '/' + 'py_modules'
os.mkdir(py_module_dir)
exclude_dirs = ['tests', 'build', 'docker_volume']
to_cp_dir_list = list(
    filter(lambda d: (d not in exclude_dirs) and (not d.startswith('.')),
           next(os.walk('.'))[1]))
for to_cp_dir in to_cp_dir_list:
    shutil.copytree(to_cp_dir, py_module_dir + '/' + to_cp_dir)

print('copying additional jars to spark package...')
add_jar_paths = [aws_java_sdk_jar_path, hadoop_aws_jar_path]
jar_dir = spark_tmpl_dir + '/' + 'jars/'
for j in add_jar_paths:
    shutil.copy(j, jar_dir)

print('writing spark-env.sh...')
shutil.copy(spark_tmpl_dir + '/conf/spark-env.sh.template', spark_tmpl_dir + '/conf/spark-env.sh')
with open(spark_tmpl_dir + '/conf/spark-env.sh', 'a') as f:
    f.write(spark_env_conf)

print('clearing output directory...')
output_dir = base_dir + '/output'
shutil.rmtree(output_dir, ignore_errors=True)
os.mkdir(output_dir)

print('packing output spark executor...')
output_spark_tmpl_dir = output_dir + '/' + os.path.basename(spark_tmpl_dir)
shutil.move(spark_tmpl_dir, output_spark_tmpl_dir)
output_spark_pack_path = output_dir + '/' + spark_tmpl_name
with tarfile.open(output_spark_pack_path, 'w:gz') as t:
    t.add(output_spark_tmpl_dir, arcname=os.path.basename(output_spark_tmpl_dir), recursive=True)

print('done')
