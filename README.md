# opensciencelab-system-containers

## jupyterhub-image

A customized [JupyterHub](https://jupyterhub.readthedocs.io/) image used by
[OpenScienceLab](https://opensciencelab.asf.alaska.edu/) deployments.

The intended customizations are system libaries not specfic to any one cluster.
Lab specific files for clusters are injected via CDK at cluster build time.

## update-execwhacker-image

An image to update the configmap used by [cryptnono](https://github.com/cryptnono/cryptnono)
from wihtin [OpenScienceLab](https://opensciencelab.asf.alaska.edu/) deployments.

Various cryptnono configurations are stored in an AWS S3 bucket.
The main script within the image pulls the configs from S3 and updates the cryptnono kubernetes configmap.
If the configmap doesn't exists, one is created.
