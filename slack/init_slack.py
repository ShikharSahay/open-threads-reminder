import os
import time
import ssl
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()


class SlackService:
    DEFAULT_CONFIG = {
        'request_limit': 10,  # req/min
        'messages_per_call': 100,
        'max_retries': 3
    }

    def __init__(self):
        """Initialize Slack client with SSL context."""
        ssl_context = ssl.create_default_context()
        self.client = WebClient(
            token=os.getenv("BOT_AUTH_TOKEN"),
            ssl=ssl_context
        )

    def fetch_messages_within_range(
            self,
            channel_id: str,
            days: int,
            request_limit_per_minute: int = DEFAULT_CONFIG['request_limit'],
            messages_per_call: int = DEFAULT_CONFIG['messages_per_call'],
            dry_run: bool = False,
            exclude_bot_messages: bool = True,
            save_to_file: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Fetch messages from Slack channel within time range.

        Args:
            channel_id: Slack channel ID
            days: Number of days to look back
            request_limit_per_minute: API rate limit
            messages_per_call: Pagination limit
            dry_run: If True, only logs without storing
            exclude_bot_messages: Skip bot messages if True
            save_to_file: Optional filename to save results

        Returns:
            List of message dictionaries
        """
        all_messages = []
        cursor = None
        request_delay = 60 / request_limit_per_minute
        retry_count = 0

        now = datetime.now(timezone.utc)
        oldest_ts = int((now - timedelta(days=days)).timestamp())
        latest_ts = int(now.timestamp())

        print(f"Fetching messages from {channel_id} between {days} days ago and now.")
        print(f"Rate limit: {request_limit_per_minute} req/min -> {request_delay:.2f}s between calls")

        while retry_count < self.DEFAULT_CONFIG['max_retries']:
            try:
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=str(oldest_ts),
                    latest=str(latest_ts),
                    limit=messages_per_call,
                    cursor=cursor
                )

                messages = response.get('messages', [])
                if not dry_run:
                    all_messages.extend(
                        msg for msg in messages
                        if not (exclude_bot_messages and msg.get('bot_id'))
                    )

                print(f"Fetched {len(messages)} messages. Total: {len(all_messages)}")

                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break

                time.sleep(request_delay)
                retry_count = 0  # Reset on success

            except SlackApiError as e:
                retry_count += 1
                if e.response['error'] == 'not_in_channel':
                    print("Error: Bot needs to be added to channel first")
                    break
                elif e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 10))
                    print(f"Rate limit hit. Retrying after {retry_after} seconds.")
                    time.sleep(retry_after)
                else:
                    print(f"[ERROR] Slack API Error: {e.response['error']}")
                    if retry_count >= self.DEFAULT_CONFIG['max_retries']:
                        break

        if save_to_file and not dry_run:
            with open(save_to_file, 'w') as f:
                json.dump(all_messages, f, indent=2)

        return all_messages


if __name__ == "__main__":
    slack = SlackService()
    messages = slack.fetch_messages_within_range(
        channel_id="C0976QAJU3F",
        days=30,
        save_to_file='slack_messages.json'
    )
    print(f"\nFetched {len(messages)} messages total.")