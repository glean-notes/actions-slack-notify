FROM python:3.7

ADD send-slack.py /send-slack.py

RUN pip install slack_sdk

ENTRYPOINT ["python", "/send-slack.py"]
