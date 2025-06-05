from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import sys
import urllib.request
import redis
import time

DEFAULT_REDIS_EXPIRE = 604800  # 7 days

channels_list = {}


def redis_instance() -> redis.client.Redis:
    return redis.Redis(host=os.getenv("REDIS_HOST", "redis-master.redis"), port=6379, decode_responses=True)  # type: ignore


def update_redis_slack_channel_cache(redis_client: redis.client.Redis, channel_name: str, channel_id: str):
    redis_client.hset("slack_channel_ids", channel_id, channel_name)
    redis_client.hset("slack_channel_ids", channel_name, channel_id)


def get_channel_id_from_redis(redis_client: redis.client.Redis, slack_channel_id: str):
    return redis_client.hget("slack_channel_ids", slack_channel_id)


def fetch_channels(
    slack_client: WebClient,
    next_cursor: str = "",
):
    try:
        result = slack_client.conversations_list(
            exclude_archived=True,
            limit=500,
            types="public_channel,private_channel",
            cursor=next_cursor,
        )
        time.sleep(0.5)

        return result["response_metadata"]["next_cursor"], result["channels"]
    except SlackApiError as e:
        print(f"Slack error: {e}")


def get_channel_id_from_slack(slack_client: WebClient, redis_client: redis.client.Redis, channel_name: str):
    next_cursor = ""
    while True:
        next_cursor, channels = fetch_channels(slack_client, next_cursor)
        for channel in channels:
            update_redis_slack_channel_cache(redis_client, channel["name"], channel["id"])
            if channel["name"] == channel_name:
                return channel["id"]

        if not next_cursor:
            print("End of conversation list and not found channel. Does the channel exist? Breaking.")
            break


def get_slack_channel_id(slack_client: WebClient, channel_id: str):
    slack_channel = None
    try:
        redis_client = redis_instance()
        slack_channel = get_channel_id_from_redis(redis_client, channel_id)
    except Exception as e:
        print("Unable to get channel from redis. Fetching from slack.")
        print(e)

    if not slack_channel:
        slack_channel = get_channel_id_from_slack(slack_client, redis_client, channel_id)

    return slack_channel


def validate_vars():
    MANDATORY_ENV_VARS = [
        "SLACK_CHANNEL",
        "MESSAGE_CONTENT",
        "PIPELINE_NAME",
        "SLACK_BOT_TOKEN",
    ]
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            raise EnvironmentError("Error. Env var {} is not set and is required to run.".format(var))


def main():
    validate_vars()

    slack_channel = os.environ["SLACK_CHANNEL"]
    message_content = os.environ["MESSAGE_CONTENT"].replace(r"\n", "\n")
    pipeline_name = os.environ["PIPELINE_NAME"]
    slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
    slack_icon = os.getenv(
        "SLACK_BOT_ICON",
        "https://avatars.slack-edge.com/2021-11-25/2761902347286_e28cd3f1518d297d034b_512.png",
    )

    try:
        slack_client = WebClient(token=slack_bot_token)
        channel_id = get_slack_channel_id(slack_client, slack_channel)

        # Send the slack message, if it fails an exception will fire
        slack_client.chat_postMessage(
            channel=channel_id,
            text=message_content,
            username=pipeline_name,
            icon_url=slack_icon,
            unfurl_links=True,
            unfurl_media=True,
        )

        image_path = os.getenv("IMAGE_PATH")
        if image_path:
            with open(image_path, "rb") as f:
                data = f.read()
                print("Getting upload URL")
                upload_response = slack_client.files_getUploadURLExternal(filename="image", length=len(data))
                print("Uploading image")
                request = urllib.request.Request(url=upload_response["upload_url"], data=data, method="POST")
                urllib.request.urlopen(request)
                print("Completing upload")
                slack_client.files_completeUploadExternal(
                    files=[{"id": upload_response["file_id"], "title": "image"}],
                    channel_id=channel_id,
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
