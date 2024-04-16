FROM python:3.11-alpine

RUN pip install slack_sdk

COPY send-slack.py /send-slack.py

ENTRYPOINT ["python", "/send-slack.py"]
