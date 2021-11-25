from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import sys

channels_list = {}

def fetch_channels(client: WebClient, next_cursor: str = ""):
    try:
        result = client.conversations_list(
            exclude_archived=True,
            limit=500,
            types="public_channel,private_channel",
            cursor=next_cursor,
        )
        for channel in result["channels"]:
            channels_list[channel["name"]] = channel["id"]
        return result
    except SlackApiError as e:
        print(f"Slack error: {e}")


def validate_vars():
    MANDATORY_ENV_VARS = ["SLACK_CHANNEL", "MESSAGE_CONTENT", "PIPELINE_NAME", "SLACK_BOT_TOKEN"]
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            raise EnvironmentError("Error. Env var {} is not set and is required to run.".format(var))


def main():
    validate_vars()

    slack_channel = os.environ["SLACK_CHANNEL"]
    message_content = os.environ["MESSAGE_CONTENT"]
    pipeline_name = os.environ["PIPELINE_NAME"]
    slack_bot_token = os.environ["SLACK_BOT_TOKEN"]

    try:
        client = WebClient(token=slack_bot_token)

        # Get the channel ID from the name
        next_cursor = fetch_channels(client)["response_metadata"]["next_cursor"]
        while next_cursor:
            next_cursor = fetch_channels(client, next_cursor)["response_metadata"][
                "next_cursor"
            ]

        channel_id = channels_list[slack_channel]

        # Send the slack message, if it fails an exception will fire
        client.chat_postMessage(
            channel=channel_id, text=message_content, username=pipeline_name
        )
        print("Message sent.")
    except SlackApiError as e:
        print(f"Error posting message: {e}")
        sys.exit(1)
    except KeyError:
        print(
            f"Channel {slack_channel} not found. If it a private channel: Mention @Github_Actions & invite them to the channel first"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
