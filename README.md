# Trinity
Trinity is a big data platform skeleton that aims to bridge the gaps among engineer, data scientist and business analyst.

## Deployment Architecture
TBD

## Setup The Master
Prerequisite: `python` is installed on The Master and there is a `ZooKeeper` standing by with IP=[zk_ip];

Pack Spark executor package for Mesos agents

    python pack_spark_executor.py

Build Docker image trinity_base

    docker build --rm -f Dockerfile.base -t trinity_base:latest .

Build Docker image trinity_master
    
    docker build --rm -f Dockerfile.master -t trinity_master:latest .
    
Build Docker image trinity_nginx
    
    docker build --rm -f Dockerfile.nginx -t trinity_nginx:latest .

Build Docker image trinity_zeppelin

    docker build --rm -f Dockerfile.zeppelin -t trinity_zeppelin:latest .

    
Docker run trinity_master

    docker run -d --net=host \
          -e MESOS_PORT=5050 \
          -e MESOS_ZK=zk://[zk_ip]:2181/trinity \
          -e MESOS_QUORUM=1 \
          -e MESOS_REGISTRY=in_memory \
          -e MESOS_LOG_DIR=/var/log/mesos \
          -e MESOS_WORK_DIR=/var/tmp/mesos \
          --name trinity_master \
          trinity_master
          
Docker run trinity_nginx

    docker run -d --net=host \
      --name trinity_nginx \
      trinity_nginx
      
Docker run trinity_zeppelin

    docker run -d --net=host \
      --name trinity_zeppelin \
      trinity_zeppelin
              
## Setup Agent Cluster
Build Docker image trinity_base

    docker build --rm -f Dockerfile.base -t trinity_base:latest .

Build Docker image trinity_agent

    docker build --rm -f Dockerfile.agent -t trinity_agent:latest .

Docker run trinity_agent

    docker run -d --net=host --privileged \
      -e MESOS_PORT=5051 \
      -e MESOS_MASTER=zk://[zk_ip]:2181/trinity \
      -e MESOS_SWITCH_USER=0 \
      -e MESOS_CONTAINERIZERS=docker,mesos \
      -e MESOS_LOG_DIR=/var/log/mesos \
      -e MESOS_WORK_DIR=/var/tmp/mesos \
      -e MESOS_SYSTEMD_ENABLE_SUPPORT=false \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v /cgroup:/cgroup \
      -v /sys:/sys \
      -v "$(which docker):/usr/local/bin/docker" \
      --name trinity_agent \
      trinity_agent
      
## Setup Zeppelin
Follow link `http://[master_ip]:8080/#/interpreter` to open Zeppelin interpreter config page.
Make the following changes on interpreter `spark`,

    master                  mesos://zk://[zk_ip]:2181/trinity
    spark.executor.uri      http://[master_ip]/spark-2.3.1-bin-hadoop2.7.tgz
    zeppelin.pyspark.python	/root/trinity/conda/envs/trinity/bin/python
