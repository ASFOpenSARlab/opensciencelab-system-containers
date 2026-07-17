FROM public.ecr.aws/docker/library/python:3.12

RUN apt update && \
    apt install -y python3-pip && \
    python3 -m pip install \
    boto3 \
    requests \
    kubernetes==34.1.0 \
    opensarlab-backend==1.0.4 \
    escapism

COPY ./app/update_execwhacker_config.py /app/update_execwhacker_config.py
