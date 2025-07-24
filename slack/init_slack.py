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
        'request_limit': 10,
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

    def fetch_thread_replies(
            self,
            channel_id: str,
            thread_ts: str,
            request_limit_per_minute: int = DEFAULT_CONFIG['request_limit'],
            messages_per_call: int = DEFAULT_CONFIG['messages_per_call'],
            exclude_bot_messages: bool = True
    ) -> List[Dict[str, any]]:
        """
        Fetch all replies from a thread (identified by thread_ts) in a channel.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp (parent message ts)
            request_limit_per_minute: API rate limit
            messages_per_call: Max messages per API call
            exclude_bot_messages: Whether to exclude bot replies

        Returns:
            List of message dicts in the thread (excluding parent by default)
        """
        all_replies = []
        cursor = None
        request_delay = 60 / request_limit_per_minute
        reply = ""
        while True:
            try:
                response = self.client.conversations_replies(
                    channel=channel_id,
                    ts=thread_ts,
                    cursor=cursor,
                    limit=messages_per_call
                )
                messages = response.get('messages', [])
                reply = ""
                single_line = "\n-----------------------------\n"
                for message in messages:
                    if message['type'] == 'message':
                        reply = reply + single_line + "[User: " + message['user'] + "]" + ":" + message['text']

                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break

                time.sleep(request_delay)

            except SlackApiError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 10))
                    print(f"Rate limited on thread fetch. Sleeping {retry_after}s...")
                    time.sleep(retry_after)
                else:
                    reply = "[Unable to fetch replies]"
                    print(f"[ERROR] Failed to fetch replies for {thread_ts}: {e.response['error']}")
                    break
        
        return reply

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

            dict:
                - user: user
                - thread_ts: ts
                - reply_count: int
                - latest_reply: int

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

                for message in messages:
                    if message['type'] == "message":
                        all_messages.append(
                            {
                                "user": message['user'],
                                "thread_ts": message['ts'],
                                "reply_count": message.get('reply_count', 0),
                                "latest_reply": message.get('latest_reply', None),
                                "channel_id": channel_id
                            }
                        )

                print(f"Fetched {len(messages)} messages. Total: {len(all_messages)}")

                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break

                time.sleep(request_delay)
                retry_count = 0

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

        return all_messages

    def post_reply_to_thread(
            self,
            channel_id: str,
            thread_ts: str,
            message_text: str
    ):
        """
        Posts a reply in a Slack thread, tagging specified users.

        Args:
            channel_id: Channel to post in
            thread_ts: Parent thread timestamp
            message_text: Message content (can include context)
        
        Returns:
            Message ts of the reply, or None on failure
        """
        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=message_text,
                thread_ts=thread_ts
            )
            print(f"Posted reply to thread {thread_ts}")
            return response['ts']
        except SlackApiError as e:
            print(f"[ERROR] Failed to post message: {e.response['error']}")
            return None
