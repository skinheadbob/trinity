# trinity
Trinity is a big data platform skeleton that aims to bridge the gaps among engineer, data scientist and business analyst.

## Deployment Architecture
TBD

## Setup The Master
Prerequisite:
    `conda` is installed;
    `ZooKeeper` is standing by

Setup Python environment via conda

    conda env create -f conda_env.yml

Install Python libraries

    # Make sure 'gfortran' is installed
    # May need to install the following: zlib1g-dev libssl-dev libssh2-1-dev libsm6 libxt6 libxrender1


    export AIRFLOW_GPL_UNIDECODE=yes
    source activate trinity
    pip install -r conda_requirement.txt

Install R libraries

    source activate trinity
    Rscript conda_r_install_packages.r
    
Build Docker image trinity_master
    
    docker build -f Dockerfile.master -t trinity_master:latest .

[optional] Docker run trinity_master

    docker run -d --net=host \
          -e MESOS_PORT=5050 \
          -e MESOS_ZK=zk://[zk_ip]:2181/trinity \
          -e MESOS_QUORUM=1 \
          -e MESOS_REGISTRY=in_memory \
          -e MESOS_LOG_DIR=/var/log/mesos \
          -e MESOS_WORK_DIR=/var/tmp/mesos \
          --name trinity_master \
          trinity_master


## Setup Agent Cluster
Build Docker image trinity_agent

    docker build -f Dockerfile.agent -t trinity_agent:latest .

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