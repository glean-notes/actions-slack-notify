FROM python:3.11

RUN pip install slack_sdk

COPY send-slack.py /send-slack.py

ENTRYPOINT ["python", "/send-slack.py"]
