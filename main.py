import random
from slack_services.init_slack import SlackService
from datetime import datetime, timedelta, timezone
from db.init_db import DBClient
from config import DB_CONFIG, channels, RESPONSE_LIMIT, THREAD_CYCLE

db = DBClient(DB_CONFIG)
slack = SlackService()

# Get last THREAD_CYCLE (90) days threads, which are open from database.
for channel in channels:
    channel_id = channel['channel_id']
    table_name = channel['channel_name'].replace("-", "_")
    threads = db.get_open_threads_within_range(
        table=table_name, days=THREAD_CYCLE
    )
    
    # Go through each thread
    for stored_thread_info in threads:
        # Check if the len of conversations is matching
        # the len of conversation stored in database.
        current_thread_info = slack.fetch_thread_info(
            stored_thread_info['thread_ts'],
            stored_thread_info['channel_id']
        )
        if stored_thread_info['reply_count'] < current_thread_info['reply_count']:
            # Will not proceed to validate, since new reply has been added in 24 hours.
            db.update_thread_conversation_length(
                thread_id=stored_thread_info["thread_ts"],
                channel_id=stored_thread_info["channel_id"],
                reply_count=current_thread_info['reply_count'],
                last_reply_ts=current_thread_info['latest_reply']
            )
        elif current_thread_info['last_reply'] < (datetime.now() - timedelta(days=RESPONSE_LIMIT)):
            # ======== KRISHNA NEEDS TO USE AI VERTEX HERE ======
            
            # Demo response.
            ai_response = {
                "open_questions": [
                    {
                        "question": "",
                        "from": "",
                        "to": ""
                    },
                ],
                "status": random.choice["open", "closed"],
                "summary": "Demo summary"
            }
            # ======== Shikhar need to manage this =======
            final_message = ""

            if ai_response["status"] == "open":
                # Response using slack
                print(f"Sending response over slack message.")

                # =============
                # Logic to send message on slack.
                # Note: <=Validate before sending, since channel contains critical messages"=>
                # ============

                # Update thread reply count
                db.update_thread_reply_count(
                    thread_id=stored_thread_info['thread_ts'],
                    channel_id=stored_thread_info['channel_id'],
                    reply_count=current_thread_info['reply_count'] + 1,
                    last_reply=f"{datetime.now(timezone.utc).timestamp():.6f}"
                )
            else:
                # Update on database that thread is closed.
                db.update_thread_as_closed(
                    thread_id=stored_thread_info['thread_ts'],
                    channel_id=stored_thread_info['channel_id']
                )
    # Reminiding part done.

    # Update last 48 hours slack threads to database
    # Since we want new threads started after yesterday but
    # to make sure we do not miss some thread in computatinal
    # time, so take 30 hours window and neglect already 
    # existed threads.
    new_threads = slack.fetch_messages_within_range(
        channel_id=channel["channel_id"],
        days=2
    )

    # Update database with current situation.
    for thread_info in new_threads:
        db.store_thread_in_table(
            table=table_name,
            thread_data=thread_info
        )

# Validate that this thread is duplicate or simillar thread 
# is present or not.

# Use vector database and find the similarity of this thread.

# Store this embeded thread in vector database.

db.close()