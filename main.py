from slack_services.init_slack import SlackService
from datetime import datetime, timedelta, timezone
from db.init_db import DBClient
from config import DB_CONFIG, DB_NAME, channels, RESPONSE_LIMIT, THREAD_CYCLE
from vertex.client import VertexAIClient
import json

DB_CONFIG["dbname"] = DB_NAME

db = DBClient(DB_CONFIG)
slack_service = SlackService()
vertex_ai = VertexAIClient()

# Get last THREAD_CYCLE (90) days threads, which are open from database.
for channel in channels:
    channel_id = channel['channel_id']
    table_name = channel['channel_name'].replace("-", "_")
    threads = db.get_open_threads_within_range(
        table=table_name, days=THREAD_CYCLE
    )
    print(f"Found {len(threads)} open threads in channel {channel['channel_name']}.")
    for stored_thread_info in threads:
        # Check if the len of conversations is matching
        # the len of conversation stored in database.
        current_thread_info = slack_service.fetch_thread_info(
            stored_thread_info['thread_ts'],
            stored_thread_info['channel_id']
        )
        if stored_thread_info['reply_count'] < current_thread_info['reply_count']:
            # Will not proceed to validate, since new reply has been added in 24 hours.
            print(f"New reply found in thread {stored_thread_info['thread_ts']} in channel" + \
                    "{stored_thread_info['channel_id']}.")
            db.update_thread_reply_count(
                thread_id=stored_thread_info['thread_ts'],
                channel_id=stored_thread_info["channel_id"],
                reply_count=current_thread_info["reply_count"],
                last_reply=current_thread_info["lastest_reply"]
            )
        elif current_thread_info['last_reply'] < (datetime.now() - timedelta(days=RESPONSE_LIMIT)):
            # Fetch the actual thread conversation
            conversation_text = slack_service.fetch_thread_replies(
                channel_id=stored_thread_info['channel_id'],
                thread_ts=stored_thread_info['thread_ts']
            )
            
            # Use VertexAI to classify the thread
            classification_json = vertex_ai.classify_thread(conversation_text)
            
            try:
                # Parse the AI response
                classification = json.loads(classification_json.replace('```json', '').replace('```', '').strip())
                
                # Transform to match expected format
                ai_response = {
                    "open_questions": [
                        {
                            "question": q.get("question", ""),
                            "from": q.get("asked_person", ""),
                            "to": ""  # TODO
                        } for q in classification.get("open_questions_left", [])
                    ],
                    "status": classification.get("thread_state", "open"),
                    "summary": classification.get("reasoning", "AI analysis completed"),
                    "action_items": classification.get("action_items", []),
                    "stakeholders": classification.get("stakeholders", []),
                    "priority": classification.get("priority", "medium"),
                    "confidence": classification.get("confidence", 0.5)
                }
                
                print(f"AI Classification: {ai_response['status']} (Priority: {ai_response['priority']}, Confidence: {ai_response['confidence']})")
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse AI response: {e}")
                # Fallback to demo response
                ai_response = {
                    "open_questions": [],
                    "status": "open",
                    "summary": "AI parsing failed, using fallback",
                    "action_items": ["Review conversation manually"],
                    "stakeholders": [],
                    "priority": "medium",
                    "confidence": 0.3
                }
            
            # ======== Shikhar need to manage this =======
            
            # Create stakeholder mentions for tagging
            stakeholder_mentions = []
            if ai_response.get('stakeholders'):
                stakeholder_mentions = [f"<@{user_id}>" for user_id in ai_response['stakeholders']]
            
            # Format open questions if available
            open_questions_text = "None"
            if ai_response.get('open_questions_left'):
                questions = [q.get('question', 'Unknown question') for q in ai_response['open_questions_left']]
                open_questions_text = ', '.join(questions)
            elif ai_response.get('action_items'):
                open_questions_text = ', '.join(ai_response['action_items'])
            
            # Format message with bold heading and block quotes using italic keys
            final_message = f":alert: *Reminder Alert*\n\n" \
                            f"This thread has not seen any activity in the last 7 days. " \
                            f"Please review the conversation and take necessary actions.\n\n" \
                            f">_Summary:_ {ai_response['summary']}\n" \
                            f">_Priority:_ {ai_response.get('priority', 'Not specified')}\n" \
                            f">_Open Questions:_ {open_questions_text}\n" \
                            f">_Stakeholders:_ {' '.join(stakeholder_mentions) if stakeholder_mentions else 'None'}"

            if ai_response["status"] == "open":
                # to-do: Refine the slack message
                print(f"Sending response over slack message.")
                print(f"Final message to be sent: {final_message}")
                print(f"Thread ID: {stored_thread_info['thread_ts']}")
                print(f"Channel ID: {stored_thread_info['channel_id']}")
                slack_service.notify_inactive_slack_thread(
                    channel_id=stored_thread_info['channel_id'],
                    message_text=final_message,
                    thread_ts=stored_thread_info['thread_ts']
                )
                # Update thread reply count
                db.update_thread_reply_count(
                    table=table_name,
                    thread_id=stored_thread_info['thread_ts'],
                    channel_id=stored_thread_info['channel_id'],
                    reply_count=current_thread_info['reply_count'] + 1,
                    last_reply= datetime.now(timezone.utc)
                )
            else:
                # Update on database that thread is closed.
                db.update_thread_as_closed(
                    table=table_name,
                    thread_id=stored_thread_info['thread_ts'],
                    channel_id=stored_thread_info['channel_id']
                )
        else:
            print(f"Thread {stored_thread_info['thread_ts']} in channel {stored_thread_info['channel_id']} is still active or has been recently updated.")
    # Reminiding part done.

    # Update last 48 hours slack threads to database
    # Since we want new threads started after yesterday but
    # to make sure we do not miss some thread in computatinal
    # time, so take 30 hours window and neglect already 
    # existed threads.
    new_threads = slack_service.fetch_messages_within_range(
        channel_id=channel["channel_id"],
        days=2
    )

    # Update database with current situation.
    for thread_info in new_threads:
        db.store_thread_in_table(
            table=table_name,
            thread_data=thread_info
        )

db.close()