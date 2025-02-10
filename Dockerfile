FROM public.ecr.aws/docker/library/python:3.11-alpine

RUN pip install slack_sdk==3.33.4 redis==5.2.0

COPY send-slack.py /send-slack.py

ENTRYPOINT ["python", "/send-slack.py"]
