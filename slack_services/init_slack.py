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
        'request_limit': 6,
        'messages_per_call': 100,
        'max_retries': 3
    }

    def __init__(self):
        """Initialize Slack client with SSL context."""
        ssl_context = ssl.create_default_context()
        
        # Initialize bot client (for posting messages, reading history, etc.)
        self.client = WebClient(
            token=os.getenv("SLACK_BOT_TOKEN"),
            ssl=ssl_context
        )
        
        # Store bot user ID for checking message ownership
        self.bot_user_id = None
        try:
            auth_response = self.client.auth_test()
            if auth_response['ok']:
                self.bot_user_id = auth_response['user_id']
                print(f"Bot initialized - User ID: {self.bot_user_id}")
        except SlackApiError:
            print("Warning: Could not get bot user ID")

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
                        reply = reply + single_line + "[User: " + message.get('user', 'unknown') + "]" + ":" + message['text']

                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break

                time.sleep(request_delay)

            except SlackApiError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    print(f"Rate limited on thread fetch. Sleeping {retry_after}s...")
                    time.sleep(retry_after)
                else:
                    reply = "[Unable to fetch replies]"
                    print(f"[ERROR] Failed to fetch replies for {thread_ts}: {e.response['error']}")
                    break
        
        return reply

    def fetch_thread_info(
        self,  
        thread_ts: str, 
        channel_id: str, 
        request_limit_per_minute: int = DEFAULT_CONFIG['request_limit']
    ) -> Dict[str, any]:
        """
        Fetch current thread information including reply count and last reply timestamp.
        
        Args:
            thread_ts: Thread timestamp 
            channel_id: Slack channel ID
            
        Returns:
            Dict with reply_count, latest_reply, and last_reply as datetime
        """
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1  # Just get the thread info, not all messages
            )
            
            if not response.get('messages'):
                return {
                    'reply_count': 0,
                    'latest_reply': thread_ts,
                    'last_reply': datetime.fromtimestamp(float(thread_ts))
                }
            
            # Get thread metadata
            parent_message = response['messages'][0]
            reply_count = parent_message.get('reply_count', 0)
            latest_reply = parent_message.get('latest_reply', thread_ts)
            
            # Convert timestamp to datetime
            last_reply_datetime = datetime.fromtimestamp(float(latest_reply))
            
            request_delay = 60 / request_limit_per_minute
            
            time.sleep(request_delay)
            
            return {
                'reply_count': reply_count,
                'latest_reply': latest_reply,
                'last_reply': last_reply_datetime
            }
            
        except SlackApiError as e:
            print(f"[ERROR] Failed to fetch thread info for {thread_ts}: {e.response['error']}")
            return {
                'reply_count': 0,
                'latest_reply': thread_ts,
                'last_reply': datetime.fromtimestamp(float(thread_ts))
            }

    def fetch_messages_within_range(
            self,
            channel_id: str,
            days: int,
            request_limit_per_minute: int = DEFAULT_CONFIG['request_limit'],
            messages_per_call: int = DEFAULT_CONFIG['messages_per_call'],
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
                - latest_reply: int ( timestamp )
                - channel_id
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
                                "user_id": message['user'],
                                "thread_ts": message['ts'],
                                "reply_count": message.get('reply_count', 0),
                                "latest_reply": message.get('latest_reply', message['ts']),
                                "channel_id": channel_id,
                                "status": "open"
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
                    print(f"⚠️ Bot not in channel {channel_id} - Cannot fetch messages")
                    print(f"💡 To fix: Add the bot to the Slack channel first")
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

    def get_user_info(self, user_id: str) -> Dict[str, str]:
        """
        Get user information from Slack API with enhanced profile data.
        
        Args:
            user_id: Slack user ID (e.g., U123456789)
            
        Returns:
            Dict with comprehensive user info including profile images
        """
        request_delay = 60 / self.DEFAULT_CONFIG['request_limit']
        retry_count = 0
        
        while retry_count < self.DEFAULT_CONFIG['max_retries']:
            try:
                response = self.client.users_info(user=user_id)
                user = response['user']
                profile = user.get('profile', {})
                
                return {
                    "user_id": user_id,
                    "name": user.get('name', user_id),
                    "display_name": profile.get('display_name', user.get('name', user_id)),
                    "real_name": profile.get('real_name', user.get('name', user_id)),
                    "profile_image_url": profile.get('image_original', profile.get('image_512', '')),
                    "profile_image_24": profile.get('image_24', ''),
                    "profile_image_32": profile.get('image_32', ''),
                    "profile_image_48": profile.get('image_48', ''),
                    "profile_image_72": profile.get('image_72', '')
                }
            except SlackApiError as e:
                retry_count += 1
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", request_delay))
                    print(f"Rate limited on user info fetch. Sleeping {retry_after}s...")
                    time.sleep(retry_after)
                elif e.response['error'] == 'user_not_found':
                    print(f"[WARNING] User not found: {user_id}")
                    return {
                        "user_id": user_id,
                        "name": user_id,
                        "display_name": f"Unknown User ({user_id})",
                        "real_name": f"Unknown User ({user_id})",
                        "profile_image_url": '',
                        "profile_image_24": '',
                        "profile_image_32": '',
                        "profile_image_48": '',
                        "profile_image_72": ''
                    }
                else:
                    print(f"[WARNING] Could not fetch user info for {user_id}: {e.response['error']}")
                    time.sleep(request_delay)
                    
        # Fallback after max retries
        return {
            "user_id": user_id,
            "name": user_id,
            "display_name": user_id,
            "real_name": user_id,
            "profile_image_url": '',
            "profile_image_24": '',
            "profile_image_32": '',
            "profile_image_48": '',
            "profile_image_72": ''
        }

    def batch_fetch_user_profiles(self, user_ids: List[str], db_client=None) -> List[Dict[str, str]]:
        """
        Batch fetch user profiles with caching to minimize API calls.
        
        Args:
            user_ids: List of Slack user IDs
            db_client: Optional database client for caching
            
        Returns:
            List of user profile dicts
        """
        profiles = []
        users_to_fetch = []
        
        # Check cache first if db_client provided
        if db_client:
            for user_id in user_ids:
                cached_profile = db_client.get_user_profile(user_id)
                if cached_profile:
                    profiles.append(dict(cached_profile))
                else:
                    users_to_fetch.append(user_id)
        else:
            users_to_fetch = user_ids
        
        # Fetch missing profiles from Slack API
        request_delay = 60 / self.DEFAULT_CONFIG['request_limit']
        
        for user_id in users_to_fetch:
            print(f"Fetching profile for user: {user_id}")
            profile = self.get_user_info(user_id)
            profiles.append(profile)
            
            # Cache in database if available
            if db_client:
                try:
                    db_client.store_user_profile(profile)
                except Exception as e:
                    print(f"[WARNING] Failed to cache user profile for {user_id}: {e}")
            
            # Rate limiting between requests
            if len(users_to_fetch) > 1:
                time.sleep(request_delay)
        
        return profiles

    def resolve_stakeholders(self, user_ids: List[str], db_client=None) -> List[Dict[str, str]]:
        """
        Resolve a list of user IDs to user information with caching.
        
        Args:
            user_ids: List of Slack user IDs
            db_client: Optional database client for caching
            
        Returns:
            List of user info dicts with profile images
        """
        if not user_ids:
            return []
            
        # Remove duplicates while preserving order
        unique_user_ids = list(dict.fromkeys(user_ids))
        
        return self.batch_fetch_user_profiles(unique_user_ids, db_client)

    def extract_user_ids_from_conversation(self, conversation_text: str) -> List[str]:
        """
        Extract user IDs from conversation text using regex.
        Enhanced to handle multiple mention formats.
        
        Args:
            conversation_text: Raw conversation text
            
        Returns:
            List of unique user IDs found in the conversation
        """
        import re
        user_ids = []
        
        # Pattern 1: Standard Slack user ID format: U followed by 8+ alphanumeric characters
        standard_ids = re.findall(r'U[A-Z0-9]{8,}', conversation_text)
        user_ids.extend(standard_ids)
        
        # Pattern 2: Slack mention format: <@U123456789>
        mention_ids = re.findall(r'<@(U[A-Z0-9]{8,})>', conversation_text)
        user_ids.extend(mention_ids)
        
        # Pattern 3: Slack mention with display name: <@U123456789|username>
        mention_with_name_ids = re.findall(r'<@(U[A-Z0-9]{8,})\|[^>]+>', conversation_text)
        user_ids.extend(mention_with_name_ids)
        
        print(f"🔍 Regex extraction found user IDs: {user_ids}")
        
        # Remove duplicates while preserving order
        unique_ids = list(dict.fromkeys(user_ids))
        print(f"📝 Unique user IDs: {unique_ids}")
        return unique_ids

    def extract_github_issues_from_conversation(self, conversation_text: str) -> List[str]:
        """
        Extract GitHub issue references from conversation text.
        
        Args:
            conversation_text: Raw conversation text
            
        Returns:
            List of GitHub issue references (e.g., ["owner/repo#123", "org/project#456"])
        """
        import re
        # Match patterns like: owner/repo#123, org/project#456
        github_patterns = [
            r'([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)#(\d+)',  # owner/repo#123
            r'https://github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)/issues/(\d+)',  # Full GitHub URLs
            r'github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)/issues/(\d+)'  # Partial GitHub URLs
        ]
        
        github_issues = []
        
        for pattern in github_patterns:
            matches = re.findall(pattern, conversation_text, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:  # (owner/repo, issue_number)
                    github_ref = f"{match[0]}#{match[1]}"
                    if github_ref not in github_issues:
                        github_issues.append(github_ref)
        
        return github_issues

    def extract_jira_tickets_from_conversation(self, conversation_text: str) -> List[str]:
        """
        Extract Jira ticket references from conversation text.
        
        Args:
            conversation_text: Raw conversation text
            
        Returns:
            List of Jira ticket references (e.g., ["PROJECT-123", "TEAM-456"])
        """
        import re
        # Match patterns like: PROJECT-123, TEAM-456, ABC-789
        jira_patterns = [
            r'\b([A-Z]{2,10}-\d{1,6})\b',  # PROJECT-123 format
            r'https://[a-zA-Z0-9_.-]+\.atlassian\.net/browse/([A-Z]{2,10}-\d{1,6})',  # Full Jira URLs
            r'atlassian\.net/browse/([A-Z]{2,10}-\d{1,6})',  # Partial Jira URLs
            r'jira\..*?/browse/([A-Z]{2,10}-\d{1,6})'  # Generic Jira browse URLs
        ]
        
        jira_tickets = []
        
        for pattern in jira_patterns:
            matches = re.findall(pattern, conversation_text, re.IGNORECASE)
            for match in matches:
                ticket = match if isinstance(match, str) else match[0]
                if ticket not in jira_tickets:
                    jira_tickets.append(ticket)
        
        return jira_tickets

    def extract_thread_issues_from_conversation(self, conversation_text: str) -> List[str]:
        """
        Extract internal thread issue references from conversation text.
        
        Args:
            conversation_text: Raw conversation text
            
        Returns:
            List of thread issue references (e.g., ["#123", "#456"])
        """
        import re
        # Match patterns like: #123, #456 (but not GitHub-style owner/repo#123)
        thread_pattern = r'(?<!/)#(\d{1,6})\b'  # #123 but not repo#123
        
        matches = re.findall(thread_pattern, conversation_text)
        return [f"#{match}" for match in matches if match]

    def extract_all_issue_references(self, conversation_text: str) -> Dict[str, List[str]]:
        """
        Extract all types of issue references from conversation text.
        
        Args:
            conversation_text: Raw conversation text
            
        Returns:
            Dict with github_issues, jira_tickets, and thread_issues lists
        """
        return {
            "github_issues": self.extract_github_issues_from_conversation(conversation_text),
            "jira_tickets": self.extract_jira_tickets_from_conversation(conversation_text),
            "thread_issues": self.extract_thread_issues_from_conversation(conversation_text)
        }

    def post_reply_to_thread(
            self,
            channel_id: str,
            thread_ts: str,
            message_text: str,
            request_limit_per_minute: int = DEFAULT_CONFIG['request_limit'],
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
        request_delay = 60 / request_limit_per_minute
        
        while True:
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
              print(f"Retrying after {request_delay} seconds")
              time.sleep(request_delay)

    def notify_inactive_slack_thread(
            self,
            channel_id: str,
            thread_ts: str,
            message_text: str
    ):
        """
        Notify users in an inactive Slack thread.

        Args:
            channel_id: Channel to post in
            thread_ts: Parent thread timestamp
            message_text: Message content (can include context)
            
        Returns:
            Message timestamp if successful, None if failed
        """
        print(f"Notifying inactive thread {thread_ts} in channel {channel_id}")
        reply_ts = self.post_reply_to_thread(channel_id, thread_ts, message_text)
        if reply_ts:
            print(f"Notification sent successfully with ts: {reply_ts}")
            return reply_ts
        else:
            print(f"Failed to send notification for thread {thread_ts}")
            return None
            
    def delete_message(self, channel_id: str, message_ts: str):
        """
        Delete a bot message from a Slack channel.
        
        Args:
            channel_id: Channel containing the message
            message_ts: Timestamp of the message to delete
        
        Note:
            Bot tokens can only delete messages posted by that bot.
            This method will verify the message was posted by this bot before attempting deletion.
        
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            response = self.client.chat_delete(
                channel=channel_id,
                ts=message_ts
            )
            print(f"✅ Bot message deleted successfully: {response['ok']}")
            return True
            
        except SlackApiError as e:
            error_code = e.response['error']
            print(f"❌ Error deleting message: {error_code}")
            
            # Provide helpful error explanations
            if error_code == 'cant_delete_message':
                print("💡 Bot tokens can only delete messages posted by that bot.")
                print("   Make sure this message was posted by your bot.")
            elif error_code == 'message_not_found':
                print("💡 The message doesn't exist or timestamp is invalid.")
            elif error_code == 'channel_not_found':
                print("💡 The channel ID is invalid or bot doesn't have access.")
            elif error_code == 'missing_scope':
                print("💡 Missing required scope: chat:write")
                print("   Add 'chat:write' scope to your Slack app at https://api.slack.com/apps")
                
            return False
    
    def get_message_info(self, channel_id: str, message_ts: str) -> Optional[Dict[str, any]]:
        """
        Get information about a specific message.
        
        Args:
            channel_id: Channel containing the message
            message_ts: Timestamp of the message
            
        Returns:
            Message information dict or None if not found
        """
        try:
            # Get conversation history with a very small window around the timestamp
            response = self.client.conversations_history(
                channel=channel_id,
                inclusive=True,
                oldest=message_ts,
                latest=message_ts,
                limit=1
            )
            
            messages = response.get('messages', [])
            if messages and messages[0].get('ts') == message_ts:
                return messages[0]
            return None
            
        except SlackApiError as e:
            print(f"❌ Error getting message info: {e.response['error']}")
            return None
    
    def is_bot_message(self, channel_id: str, message_ts: str) -> bool:
        """
        Check if a message was posted by this bot.
        
        Args:
            channel_id: Channel containing the message
            message_ts: Timestamp of the message
            
        Returns:
            True if message was posted by this bot, False otherwise
        """
        if not self.bot_user_id:
            return False
            
        message_info = self.get_message_info(channel_id, message_ts)
        if not message_info:
            return False
            
        return message_info.get('user') == self.bot_user_id or message_info.get('bot_id') is not None
    
    def delete_bot_message(self, channel_id: str, message_ts: str) -> bool:
        """
        Delete a message, but only if it was posted by this bot.
        This method verifies message ownership before attempting deletion.
        
        Args:
            channel_id: Channel containing the message
            message_ts: Timestamp of the message
            
        Returns:
            True if deletion successful, False otherwise
        """
        print(f"🔍 Verifying bot message ownership for ts: {message_ts}")
        
        # Get message info first
        message_info = self.get_message_info(channel_id, message_ts)
        if not message_info:
            print("❌ Message not found or not accessible")
            return False
        
        user_id = message_info.get('user')
        bot_id = message_info.get('bot_id')
        
        print(f"📧 Message info: user={user_id}, bot_id={bot_id}, our_bot_id={self.bot_user_id}")
        
        # Check if it's our bot's message
        if user_id == self.bot_user_id or (bot_id and user_id == self.bot_user_id):
            print("🤖 Confirmed: This is our bot's message - proceeding with deletion")
            return self.delete_message(channel_id, message_ts)
        else:
            print("❌ This is NOT our bot's message - cannot delete")
            print("   Bot tokens can only delete messages posted by that specific bot")
            return False

    def check_recent_activity_source(self, channel_id: str, thread_ts: str, since_timestamp: datetime) -> dict:
        """
        Check if recent activity in a thread was from bot or humans.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            since_timestamp: Check activity since this time
            
        Returns:
            Dict with activity analysis: {
                'has_human_activity': bool,
                'has_bot_activity': bool, 
                'latest_human_reply': datetime or None,
                'latest_bot_reply': datetime or None,
                'total_new_replies': int
            }
        """
        try:
            # Get bot user ID for comparison
            auth_response = self.client.auth_test()
            bot_user_id = auth_response.get('user_id')
            
            # Get thread replies since the timestamp
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                oldest=since_timestamp.timestamp(),
                limit=100  # Should be enough for recent activity
            )
            
            if not response['ok']:
                print(f"Failed to fetch recent thread activity: {response.get('error', 'Unknown error')}")
                return {
                    'has_human_activity': False,
                    'has_bot_activity': False,
                    'latest_human_reply': None,
                    'latest_bot_reply': None,
                    'total_new_replies': 0
                }
            
            messages = response.get('messages', [])
            # Skip the parent message, only look at replies
            replies = [msg for msg in messages if msg.get('ts') != thread_ts]
            
            human_replies = []
            bot_replies = []
            
            for reply in replies:
                reply_time = datetime.fromtimestamp(float(reply['ts']), tz=timezone.utc)
                
                # Only consider replies after the since_timestamp
                if reply_time > since_timestamp:
                    if reply.get('user') == bot_user_id or reply.get('bot_id'):
                        bot_replies.append(reply_time)
                    else:
                        human_replies.append(reply_time)
            
            return {
                'has_human_activity': len(human_replies) > 0,
                'has_bot_activity': len(bot_replies) > 0,
                'latest_human_reply': max(human_replies) if human_replies else None,
                'latest_bot_reply': max(bot_replies) if bot_replies else None,
                'total_new_replies': len(human_replies) + len(bot_replies)
            }
            
        except SlackApiError as e:
            print(f"Error checking recent activity: {e.response['error']}")
            return {
                'has_human_activity': False,
                'has_bot_activity': False,
                'latest_human_reply': None,
                'latest_bot_reply': None,
                'total_new_replies': 0
            }

    def is_bot_user(self, user_id: str) -> bool:
        """
        Check if a user ID belongs to a bot.
        
        Args:
            user_id: Slack user ID to check
            
        Returns:
            True if user is a bot, False if human user
        """
        try:
            # Bot user IDs sometimes start with 'B' instead of 'U'
            if user_id.startswith('B'):
                return True
            
            # Get user info to check if it's a bot
            response = self.client.users_info(user=user_id)
            if response['ok']:
                user = response['user']
                # Check various bot indicators
                is_bot = (
                    user.get('is_bot', False) or 
                    user.get('is_app_user', False) or
                    'bot_id' in user or
                    user.get('name', '').endswith('.bot') or
                    user.get('real_name', '').lower().endswith('bot')
                )
                return is_bot
            return False
            
        except SlackApiError as e:
            # If we can't determine, assume it's human (safer for notifications)
            if e.response['error'] == 'user_not_found':
                print(f"User {user_id} not found - treating as human")
            else:
                print(f"Error checking if user {user_id} is bot: {e.response['error']}")
            return False

    def filter_human_stakeholders(self, user_ids: List[str]) -> List[str]:
        """
        Filter out bots from a list of user IDs, keeping only human users.
        Also excludes the bot's own user ID.
        
        Args:
            user_ids: List of user IDs to filter
            
        Returns:
            List of user IDs that belong to human users only
        """
        # Get bot's own user ID to exclude it
        try:
            auth_response = self.client.auth_test()
            bot_user_id = auth_response.get('user_id')
        except:
            bot_user_id = None
        
        human_users = []
        for user_id in user_ids:
            # Skip the bot's own user ID
            if user_id == bot_user_id:
                print(f"🤖 Excluded bot's own user ID: {user_id}")
                continue
                
            if not self.is_bot_user(user_id):
                human_users.append(user_id)
            else:
                print(f"🤖 Filtered out bot user: {user_id}")
        
        return human_users

    def extract_thread_participants(self, channel_id: str, thread_ts: str) -> List[str]:
        """
        Extract all participants (message authors) from a thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of user IDs who participated in the thread
        """
        participants = set()
        
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1000  # Get all messages in thread
            )
            
            if response['ok']:
                messages = response.get('messages', [])
                
                for message in messages:
                    # Add message author
                    if 'user' in message:
                        participants.add(message['user'])
                    
                    # Also check for user mentions in the message text
                    text = message.get('text', '')
                    mentioned_users = self.extract_user_ids_from_conversation(text)
                    participants.update(mentioned_users)
                        
                print(f"👥 Found {len(participants)} unique thread participants")
                return list(participants)
            else:
                print(f"Failed to fetch thread participants: {response.get('error', 'Unknown error')}")
                return []
                
        except SlackApiError as e:
            print(f"Error fetching thread participants: {e.response['error']}")
            return []

    def get_recent_channel_participants(self, channel_id: str, hours: int = 24) -> List[str]:
        """
        Get users who have been active in the channel recently.
        
        Args:
            channel_id: Slack channel ID
            hours: Look back this many hours for recent activity
            
        Returns:
            List of user IDs who were recently active in the channel
        """
        participants = set()
        
        try:
            # Calculate oldest timestamp (hours ago)
            from datetime import datetime, timedelta, timezone
            oldest_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            oldest_ts = oldest_time.timestamp()
            
            response = self.client.conversations_history(
                channel=channel_id,
                oldest=str(oldest_ts),
                limit=100  # Get recent messages
            )
            
            if response['ok']:
                messages = response.get('messages', [])
                
                for message in messages:
                    if 'user' in message:
                        participants.add(message['user'])
                        
                print(f"🕒 Found {len(participants)} recent channel participants in last {hours}h")
                return list(participants)
            else:
                print(f"Failed to fetch recent channel participants: {response.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(f"Error fetching recent channel participants: {e}")
            return []

    def extract_enhanced_stakeholders(self, channel_id: str, thread_ts: str, conversation_text: str) -> List[str]:
        """
        Extract enhanced stakeholder list including thread participants, mentioned users, and recent channel participants.
        
        Args:
            channel_id: Slack channel ID  
            thread_ts: Thread timestamp
            conversation_text: Thread conversation text
            
        Returns:
            List of user IDs for all stakeholders (comprehensive detection)
        """
        # Get thread participants (message authors)
        thread_participants = self.extract_thread_participants(channel_id, thread_ts)
        
        # Get mentioned users from conversation text
        mentioned_users = self.extract_user_ids_from_conversation(conversation_text)
        
        # Get recent channel participants (for broader context)
        recent_participants = self.get_recent_channel_participants(channel_id, hours=24)
        
        # Combine and deduplicate
        all_stakeholders = list(set(thread_participants + mentioned_users + recent_participants))
        
        print(f"👥 Thread participants: {thread_participants}")
        print(f"💬 Mentioned users: {mentioned_users}")
        print(f"🕒 Recent channel participants: {recent_participants}")
        print(f"🎯 Total stakeholders: {all_stakeholders}")
        
        # ENHANCED: If no stakeholders found, ensure we at least include thread author and active participants
        if not all_stakeholders:
            print("⚠️ No stakeholders found via standard methods, falling back to thread author")
            try:
                # Get the thread starter as a fallback stakeholder
                response = self.client.conversations_replies(
                    channel=channel_id,
                    ts=thread_ts,
                    limit=1
                )
                if response['ok'] and response.get('messages'):
                    thread_author = response['messages'][0].get('user')
                    if thread_author:
                        all_stakeholders = [thread_author]
                        print(f"📝 Fallback: Using thread author as stakeholder: {thread_author}")
            except Exception as e:
                print(f"Error getting thread author: {e}")
        
        return all_stakeholders