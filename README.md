# trinity
Trinity is a big data platform skeleton that aims to bridge the gaps among engineer, data scientist and business analyst.

## Deployment Architecture
TBD

## Setup The Master
Prerequisite:
    `conda` is installed
    setup a ZooKeeper cluster

1. Setup Python environment via conda

    conda env create -f conda_env.yml

2. Install Python libraries

    # Make sure 'gfortran' is installed
    # May need to install the following: zlib1g-dev libssl-dev libssh2-1-dev libsm6 libxt6 libxrender1

    export AIRFLOW_GPL_UNIDECODE=yes
    source activate trinity
    pip install -r conda_requirement.txt

3. Install R libraries

    source activate trinity
    Rscript conda_r_install_packages.r

4. [optional] Install and run mesos-master with Docker

    docker run -d --net=host \
      -e MESOS_PORT=5050 \
      -e MESOS_ZK=zk://[zk_ip]:2181/trinity \
      -e MESOS_QUORUM=1 \
      -e MESOS_REGISTRY=in_memory \
      -e MESOS_LOG_DIR=/var/log/mesos \
      -e MESOS_WORK_DIR=/var/tmp/mesos \
      -v "${pwd}/mesos_master/log:/var/log/mesos" \
      -v "${pwd}/mesos_master/tmp:/var/tmp/mesos" \
      --name trinity_mesos_master \
      mesosphere/mesos-master:1.5.0

## Setup Agent Cluster
The idea is to install and run mesos-agent on agent nodes

    docker run -d --net=host --privileged \
      -e MESOS_PORT=5051 \
      -e MESOS_MASTER=zk://[zk_ip]:2181/trinity \
      -e MESOS_SWITCH_USER=0 \
      -e MESOS_CONTAINERIZERS=docker,mesos \
      -e MESOS_LOG_DIR=/var/log/mesos \
      -e MESOS_WORK_DIR=/var/tmp/mesos \
      -e MESOS_SYSTEMD_ENABLE_SUPPORT=false \
      -v "${pwd}/mesos_agent/log:/var/log/mesos" \
      -v "${pwd}/mesos_agent/tmp:/var/tmp/mesos" \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v /cgroup:/cgroup \
      -v /sys:/sys \
      -v "$(which docker):/usr/local/bin/docker" \
      --name trinity_mesos_agent \
      mesosphere/mesos-agent:1.5.0