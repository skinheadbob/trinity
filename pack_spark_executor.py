import os
import shutil
import tarfile

import requests

# change working directory to 'here'
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# FIXME 'PYSPARK_PYTHON' needs to be more flexible
spark_env_conf = os.linesep.join([
    'export PYSPARK_PYTHON=/root/trinity/conda/envs/trinity/bin/python',
    'export PYTHONPATH=$SPARK_HOME/py_modules:$PYTHONPATH'
])

base_dir = 'build'
SPARK_VER = '2.3.2'

if not os.path.exists(base_dir):
    os.makedirs(base_dir)

spark_tmpl_url = 'http://apache.tt.co.kr/spark/spark-%(spark_ver)s/spark-%(spark_ver)s-bin-hadoop2.7.tgz' \
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

print('unpacking template spark package...')
spark_tmpl_dir = spark_tmpl_path[:-4]
shutil.rmtree(spark_tmpl_dir, ignore_errors=True)
with tarfile.open(spark_tmpl_path, 'r') as t:
    t.extractall(path=base_dir)

print('copying my python modules to spark package...')
py_module_dir = spark_tmpl_dir + '/' + 'py_modules'
os.mkdir(py_module_dir)
exclude_dirs = ['tests', 'build']
to_cp_dir_list = list(
    filter(lambda d: (d not in exclude_dirs) and (not d.startswith('.')),
           next(os.walk('.'))[1]))
for to_cp_dir in to_cp_dir_list:
    shutil.copytree(to_cp_dir, py_module_dir + '/' + to_cp_dir)

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
