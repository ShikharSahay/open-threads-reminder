from slack.client import SlackClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta
from utils import setup_logger


class SlackFetcher:
    def __init__(self):
        self.client = SlackClient().get_client()
        self.logger = setup_logger("SlackFetcher")

    def fetch_parent_messages(self, channel_id, days=90):
        self.logger.info(f"Fetching parent messages from channel {channel_id} for past {days} days")
        messages = []
        oldest = (datetime.now() - timedelta(days=days)).timestamp()
        has_more = True
        cursor = None

        try:
            while has_more:
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=oldest,
                    limit=200,
                    cursor=cursor
                )
                for msg in response.get("messages", []):
                    if "thread_ts" not in msg:
                        messages.append(msg)

                has_more = response.get("has_more", False)
                cursor = response.get("response_metadata", {}).get("next_cursor")
        except SlackApiError as e:
            self.logger.error(f"Failed to fetch parent messages: {e.response['error']}")

        self.logger.info(f"Fetched {len(messages)} parent messages.")
        return messages

    def fetch_replies(self, channel_id, thread_ts):
        try:
            self.logger.debug(f"Fetching replies for thread_ts={thread_ts}")
            response = self.client.conversations_replies(channel=channel_id, ts=thread_ts)
            return response.get("messages", [])
        except SlackApiError as e:
            self.logger.error(f"Failed to fetch replies for thread {thread_ts}: {e.response['error']}")
            return []

    def fetch_all_threads(self, channel_id, days=90):
        full_threads = []
        self.logger.info(f"Getting all threads for channel {channel_id}.")
        parent_messages = self.fetch_parent_messages(channel_id, days=days)

        for msg in parent_messages:
            thread_ts = msg["ts"]
            full_convo = self.fetch_replies(channel_id, thread_ts)
            full_threads.append({
                "thread_ts": thread_ts,
                "messages": full_convo
            })

        self.logger.info(f"Got {len(full_threads)} complete threads.")
        return full_threads
