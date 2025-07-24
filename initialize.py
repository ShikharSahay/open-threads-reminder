from db.init_db import DBClient
from slack_services.init_slack import SlackService
from config import DB_CONFIG, channels

db = DBClient(DB_CONFIG)

prerequisites_created = False

# Create prequiste dadtabase
if not prerequisites_created:
    db.create_prerequisites(
        "cuto_db",
        channels
    )

# Insert data in threads from slack.
slack = SlackService()

for channel in channels:
    channel_id = channel['channel_id']
    table_name = channel["channel_name"].replace("-", "_")
    threads = slack.fetch_messages_within_range(
        channel_id=channel_id,
        days=90,
    )
    
    for thread in threads:
        # Initial status of all threads will be open.
        thread['status'] = 'open'
        db.store_thread_in_table(
            table=table_name,
            thread_data=thread
        )

print(f"All insertion done.")
