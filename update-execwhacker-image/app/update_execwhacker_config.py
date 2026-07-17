import argparse
import logging
from typing import Optional
import yaml
import json

import boto3
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.rest import ApiException

logging.basicConfig(
    format="%(asctime)s %(levelname)s (%(lineno)d) - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)


def main(
    aws_region: str,
    config_bucket_name: str,
    aws_profile: Optional[str] = None,
):
    cm_name = "cryptnono"
    cm_namespace = "services"
    cm_select_label = "app.kubernetes.io/instance=cryptnono"
    # These labels and annotations are needed so helm knows to own the configmap if created outside the helm chart
    # These values need to match what is used within CDK
    cm_labels = {
        "app.kubernetes.io/instance": "cryptnono",
        "app.kubernetes.io/managed-by": "Helm",
    }
    cm_annotations = {
        "meta.helm.sh/release-name": "cryptnono",
        "meta.helm.sh/release-namespace": "services",
    }

    try:
        k8s_config.load_incluster_config()
    except Exception:
        k8s_config.load_config()
    k8s_api = k8s_client.CoreV1Api()

    if aws_profile:
        session = boto3.Session(region_name=aws_region, profile_name=aws_profile)
    else:
        session = boto3.Session(region_name=aws_region)

    try:
        s3 = session.client("s3", region_name=aws_region)

        # List all json files in bucket
        print(f"Checking for bucket '{config_bucket_name}'")
        bucket_objects: list = s3.list_objects_v2(Bucket=config_bucket_name).get(
            "Contents"
        )

        configmap_data = {}

        if not bucket_objects:
            print(
                f"No objects found in bucket '{config_bucket_name}'. Will use default noop config found in helm config."
            )
        else:
            config_dict_agg = {"bannedCommandStrings": [], "allowedCommandPatterns": []}

            # Cycle through all json and yaml files, reading contents and adding to configmap
            # Max size of configmap is 1 MiB
            for bucket_object in bucket_objects:
                config_name: str = bucket_object["Key"]
                response = s3.get_object(Bucket=config_bucket_name, Key=config_name)
                config_content: str = response["Body"].read().decode("utf-8")

                # Only add files that are json or yaml and contain the right format
                if config_name.endswith(".json"):
                    print(f"Add to configmap content from json file '{config_name}'")
                    config_dict: dict = json.loads(config_content)

                elif config_name.endswith(".yaml") or config_name.endswith(".yml"):
                    print(f"Add to configmap content from yaml file '{config_name}'")
                    config_dict: dict = yaml.safe_load(config_content)

                else:
                    continue

                config_dict_agg["bannedCommandStrings"] += config_dict.get(
                    "bannedCommandStrings", []
                )
                config_dict_agg["allowedCommandPatterns"] += config_dict.get(
                    "allowedCommandPatterns", []
                )

            # Note that the execwhacker assumes that the config section all start with 'execwhacker-'
            #   and end with '.json' and are defined in the execwhacker helm config.
            #   So we will need to put all the configs contents into one big json file.
            # If the helm config has a config section that does not exist, exec wahcker will crash. So make
            #   sure that defaults are also listed here.
            configmap_data = {
                "execwhacker-noop.json": json.dumps(
                    {"bannedCommandStrings": ["thisisabannedstring"]}
                ),
                "execwhacker-data.json": json.dumps(config_dict_agg),
            }

        try:
            configmap = k8s_api.read_namespaced_config_map(
                name=cm_name, namespace=cm_namespace
            )
            configmap.data = configmap_data

        except ApiException as e:
            if e.status == 404:
                # If the configmap gets deleted accidently, create one.
                print("Configmap doesn't exist. Create one...")

                body = k8s_client.V1ConfigMap()
                body.metadata = k8s_client.V1ObjectMeta(
                    name=cm_name, labels=cm_labels, annotations=cm_annotations
                )
                body.data = configmap_data
                k8s_api.create_namespaced_config_map(cm_namespace, body)

                configmap = k8s_api.read_namespaced_config_map(
                    name=cm_name, namespace=cm_namespace
                )

            else:
                raise

        k8s_api.patch_namespaced_config_map(
            name=cm_name, namespace=cm_namespace, body=configmap
        )

        # All cryptnono sidecar pods will need to be respawned to get the latest configmaps
        pods = k8s_api.list_namespaced_pod(
            namespace=cm_namespace, label_selector=cm_select_label
        )

        for pod in pods.items:
            pod_name = pod.metadata.name
            k8s_api.delete_namespaced_pod(namespace=cm_namespace, name=pod_name)

    except Exception as e:
        print(e)

    finally:
        print("Done with extraConfig::9_cryptnono.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update cryptnono execwhacker configmap from AWS Secrets Manager"
    )
    parser.add_argument(
        "--aws-region",
        help="AWS region of the cluster",
        dest="aws_region",
        required=True,
    )
    parser.add_argument(
        "--config-bucket-name",
        help="Name of the S3 bucket that contains execwhacker configs",
        dest="config_bucket_name",
        required=True,
    )
    parser.add_argument(
        "--aws-profile",
        help="AWS profile",
        dest="aws_profile",
        required=False,
    )
    args = vars(parser.parse_args())
    main(**args)
