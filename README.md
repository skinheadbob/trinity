# trinity
Trinity is a big data platform skeleton that aims to bridge the gaps among engineer, data scientist and business analyst.

## Deployment Architecture
TBD

## Setup The Master
Prerequisite: `conda` is installed

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