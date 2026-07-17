FROM public.ecr.aws/docker/library/python:3.12

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install --no-install-recommends -y python3-pip \
    && python3 -m pip install --no-cache-dir \
    boto3==1.43.50 \
    requests==2.34.2 \
    kubernetes==34.1.0 \
    escapism==1.1.0 \
    && rm -rf /var/lib/apt/lists/*

COPY ./app/update_execwhacker_config.py /app/update_execwhacker_config.py
