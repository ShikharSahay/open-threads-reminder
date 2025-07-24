from slack.client import SlackClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta
from utils import setup_logger

class SlackFetcher:
    def __init__(self):
        self.client = SlackClient().get_client()
        self.logger = setup_logger("SlackFetcher")

    def fetch_replies(self, channel_id, thread_ts):
        try:
            self.logger.debug(f"Fetching replies for thread_ts={thread_ts}")
            response = self.client.conversations_replies(channel=channel_id, ts=thread_ts)
            return response.get("messages", [])
        except SlackApiError as e:
            self.logger.error(f"Failed to fetch replies for thread {thread_ts}: {e.response['error']}")
            return []

    def fetch_full_threads(self, channel_id, days=90):
        self.logger.info(f"Scanning all messages from channel {channel_id} for past {days} days")
        oldest = (datetime.now() - timedelta(days=days)).timestamp()
        has_more = True
        cursor = None
        thread_ts_set = set()
        full_threads = []

        try:
            while has_more:
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=oldest,
                    limit=200,
                    cursor=cursor
                )
                for msg in response.get("messages", []):
                    ts = msg.get("ts")
                    thread_ts = msg.get("thread_ts", ts)

                    # Skip if we've already processed this thread
                    if thread_ts in thread_ts_set:
                        continue

                    thread_msgs = self.fetch_replies(channel_id, thread_ts)
                    if thread_msgs:
                        full_threads.append({
                            "thread_ts": thread_ts,
                            "messages": thread_msgs
                        })
                        thread_ts_set.add(thread_ts)

                has_more = response.get("has_more", False)
                cursor = response.get("response_metadata", {}).get("next_cursor")
        except SlackApiError as e:
            self.logger.error(f"Failed to fetch messages: {e.response['error']}")

        self.logger.info(f"Collected {len(full_threads)} threads from channel {channel_id}")
        return full_threads
