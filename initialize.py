from db.init_db import DBClient
from slack_services.init_slack import SlackService

DB_CONFIG = {
    "dbname": "postgres", 
    "user": "postgres", 
    "password": "", 
    "host": "localhost",
    "port": "5432"
}
channels = [
    {
        "channel_name":"vishal-testing-slack",
        "channel_id":"C096TJLR1GF"
    },
    {
        "channel_name": "proj_pg15_upgrade",
        "channel_id": "C07DURKHHNH"
    },
    {
        "channel_name": "proj_pg15",
        "channel_id": "C03L0TLANHY"
    }
]

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
