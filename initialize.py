from db.init_db import DBClient
from slack_services.init_slack import SlackService
from config import DB_CONFIG, channels

try:
    # Use context manager for proper resource cleanup
    with DBClient(DB_CONFIG) as db:
        # Create prerequisite database
        print("Creating database and tables...")
        db.create_prerequisites(DB_CONFIG.get('dbname'), channels)
        print("Database setup completed.")
        
        slack = SlackService()
        total_threads = 0
        
        for i, channel in enumerate(channels, 1):
            channel_id = channel['channel_id']
            channel_name = channel["channel_name"]
            table_name = channel_name.replace("-", "_")
            
            print(f"Processing channel {i}/{len(channels)}: {channel_name}")
            
            try:
                threads = slack.fetch_messages_within_range(
                    channel_id=channel_id,
                    days=90,
                )
                
                print(f"Found {len(threads)} threads in {channel_name}")
                
                for thread in threads:
                    # Initial status of all threads will be open.
                    thread['status'] = 'open'
                    db.store_thread_in_table(
                        table=table_name,
                        thread_data=thread
                    )
                
                total_threads += len(threads)
                print(f"Completed {channel_name}: {len(threads)} threads stored")
                
            except Exception as e:
                print(f"Error processing channel {channel_name}: {e}")
                continue
        
        print(f"All insertion done. Total threads processed: {total_threads}")

except Exception as e:
    print(f"Initialization failed: {e}")
    exit(1)
