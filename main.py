from slack_services.init_slack import SlackService
from datetime import datetime, timedelta, timezone
from db.init_db import DBClient
from config import (DB_CONFIG, DB_NAME, channels, RESPONSE_LIMIT, THREAD_CYCLE, 
                    TESTING_MODE, ACTIVE_RESPONSE_LIMIT, ACTIVE_THREAD_CYCLE, ACTIVE_TIME_UNIT,
                    ACTIVE_BOT_COOLDOWN)
from vertex.client import VertexAIClient
import json
import spacy
from psycopg2 import sql

# Load the NER model
nlp = spacy.load("en_core_web_sm")

def get_timedelta_for_config(value, unit):
    """Get appropriate timedelta based on configuration unit."""
    if unit == "minutes":
        return timedelta(minutes=value)
    elif unit == "days":
        return timedelta(days=value)
    else:
        raise ValueError(f"Unsupported time unit: {unit}")

def ensure_database_setup():
    """Ensure database and enhanced schema exist before running workflow."""
    print("🔍 Checking database setup...")
    
    try:
        # First, try connecting without database to check if it exists
        init_config = DB_CONFIG.copy()
        if "dbname" in init_config:
            del init_config["dbname"]
        
        temp_db = DBClient(init_config)
        
        # Check if database exists
        temp_db.cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        db_exists = temp_db.cursor.fetchone()
        temp_db.close()
        
        if not db_exists:
            print(f"📊 Database '{DB_NAME}' doesn't exist. Creating it...")
            temp_db = DBClient(init_config)
            temp_db.create_prerequisites(DB_NAME, channels)
            temp_db.close()
            print("✅ Database created successfully!")
            return True
        
        # Database exists, check if enhanced schema exists
        DB_CONFIG["dbname"] = DB_NAME
        db = DBClient(DB_CONFIG)
        
        # Check if channels master table exists
        try:
            db.cursor.execute("SELECT 1 FROM channels LIMIT 1")
            master_exists = True
        except:
            master_exists = False
        
        # Check if enhanced columns exist in channel tables
        enhanced_exists = True
        for channel in channels:
            table_name = channel["channel_name"].replace("-", "_")
            try:
                db.cursor.execute(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name = 'ai_thread_name'
                """)
                if not db.cursor.fetchone():
                    enhanced_exists = False
                    break
            except:
                enhanced_exists = False
                break
        
        db.close()
        
        if not master_exists or not enhanced_exists:
            print("🔧 Enhanced schema missing. Setting up...")
            
            # Connect without database name first
            temp_db = DBClient(init_config)
            temp_db.create_prerequisites(DB_NAME, channels)
            temp_db.close()
            
            print("✅ Enhanced database schema created!")
            return True
        
        print("✅ Database setup verified - enhanced schema ready!")
        return False
        
    except Exception as e:
        print(f"🚨 Database setup error: {e}")
        print("🔧 Attempting to create fresh setup...")
        
        try:
            # Try fresh setup
            init_config = DB_CONFIG.copy()
            if "dbname" in init_config:
                del init_config["dbname"]
            
            temp_db = DBClient(init_config)
            temp_db.create_prerequisites(DB_NAME, channels)
            temp_db.close()
            
            print("✅ Fresh database setup completed!")
            return True
            
        except Exception as setup_error:
            print(f"❌ Failed to setup database: {setup_error}")
            print("💡 Please check your database connection settings in config.py")
            raise

def verify_enhanced_setup():
    """Verify the enhanced setup and show summary."""
    try:
        DB_CONFIG["dbname"] = DB_NAME
        db = DBClient(DB_CONFIG)
        
        # Check channels
        all_channels = db.get_all_channels()
        print(f"\n📋 Found {len(all_channels)} channels configured:")
        
        for channel in all_channels:
            print(f"  📢 {channel['channel_name']} -> {channel['table_name']}")
        
        # Check enhanced features
        sample_table = channels[0]["channel_name"].replace("-", "_")
        db.cursor.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{sample_table}' 
            AND column_name IN ('ai_thread_name', 'github_issue', 'jira_ticket')
            ORDER BY column_name
        """)
        enhanced_columns = [row['column_name'] for row in db.cursor.fetchall()]
        
        print(f"\n🎯 Enhanced features available:")
        if 'ai_thread_name' in enhanced_columns:
            print("  ✅ AI-generated thread names and descriptions")
        if 'github_issue' in enhanced_columns:
            print("  ✅ GitHub issue linking")  
        if 'jira_ticket' in enhanced_columns:
            print("  ✅ Jira ticket linking")
        
        # Check user profiles table
        try:
            db.cursor.execute("SELECT COUNT(*) as count FROM user_profiles")
            profile_count = db.cursor.fetchone()['count']
            print(f"  ✅ User profiles cache ready ({profile_count} profiles cached)")
        except:
            print("  ✅ User profiles cache ready (empty)")
        
        db.close()
        print()
        
    except Exception as e:
        print(f"⚠️ Verification warning: {e}")

def generate_ai_thread_name(ai_response: dict) -> str:
    """Generate a concise thread name from AI analysis."""
    # Use AI summary or fallback to extracting key terms
    summary = ai_response.get('reasoning', '')
    if summary:
        # Take first sentence or first 50 characters
        first_sentence = summary.split('.')[0]
        if len(first_sentence) <= 50:
            return first_sentence.strip()
        return summary[:47].strip() + "..."
    
    # Fallback based on action items
    action_items = ai_response.get('action_items', [])
    if action_items:
        return f"Discussion: {action_items[0][:40]}..."
    
    # Final fallback
    return "Thread Discussion"

def process_ai_analysis(slack_service, conversation_text: str, thread_info: dict, existing_ai_data: dict = None) -> dict:
    """
    Process AI analysis for a thread, with smart caching and activity detection.
    Only calls AI if:
    1. No existing AI analysis, OR
    2. New human activity detected since last analysis
    
    Args:
        slack_service: Slack service instance
        conversation_text: Thread conversation text
        thread_info: Current thread information
        existing_ai_data: Previously cached AI analysis (if any)
    """
    
    # If we have existing AI analysis and no new human activity, reuse it
    if existing_ai_data and existing_ai_data.get('ai_analysis_json'):
        try:
            cached_analysis = json.loads(existing_ai_data['ai_analysis_json'])
            
            # Check if thread has new replies since last AI analysis
            last_analysis_time = existing_ai_data.get('updated_at')
            current_latest_reply = thread_info.get('latest_reply')
            
            if last_analysis_time and current_latest_reply:
                # Convert to comparable datetime objects
                if isinstance(last_analysis_time, str):
                    # Check if it's a timestamp string or ISO format
                    try:
                        # Try parsing as timestamp first
                        last_analysis_time = datetime.fromtimestamp(float(last_analysis_time), tz=timezone.utc)
                    except ValueError:
                        # Fall back to ISO format
                        last_analysis_time = datetime.fromisoformat(last_analysis_time.replace('Z', '+00:00'))
                elif isinstance(last_analysis_time, datetime) and last_analysis_time.tzinfo is None:
                    # Add timezone if naive datetime
                    last_analysis_time = last_analysis_time.replace(tzinfo=timezone.utc)
                
                if isinstance(current_latest_reply, str):
                    # Check if it's a timestamp string or ISO format
                    try:
                        # Try parsing as timestamp first
                        current_latest_reply = datetime.fromtimestamp(float(current_latest_reply), tz=timezone.utc)
                    except ValueError:
                        # Fall back to ISO format
                        current_latest_reply = datetime.fromisoformat(current_latest_reply.replace('Z', '+00:00'))
                elif isinstance(current_latest_reply, datetime) and current_latest_reply.tzinfo is None:
                    # Add timezone if naive datetime
                    current_latest_reply = current_latest_reply.replace(tzinfo=timezone.utc)
                
                # If no new activity since last analysis, reuse cached data
                if current_latest_reply <= last_analysis_time:
                    print(f"📋 Reusing cached AI analysis (no new activity since {last_analysis_time})")
                    return {
                        'ai_thread_name': existing_ai_data.get('ai_thread_name'),
                        'ai_description': existing_ai_data.get('ai_description'), 
                        'ai_stakeholders': json.loads(existing_ai_data.get('ai_stakeholders', '[]')),
                        'ai_priority': existing_ai_data.get('ai_priority'),
                        'ai_confidence': existing_ai_data.get('ai_confidence'),
                        'github_issue': existing_ai_data.get('github_issue'),
                        'jira_ticket': existing_ai_data.get('jira_ticket'),
                        'thread_issue': existing_ai_data.get('thread_issue'),
                        'ai_analysis_json': existing_ai_data.get('ai_analysis_json'),
                        'ai_response': cached_analysis
                    }
                else:
                    print(f"🔄 New activity detected since {last_analysis_time}, re-analyzing...")
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"⚠️ Error processing cached AI data, will re-analyze: {e}")
    
    print(f"🤖 Calling AI for thread analysis...")
    
    # Get fresh AI analysis
    vertex_client = VertexAIClient()
    ai_response_json = vertex_client.classify_thread(conversation_text)
    
    if not ai_response_json:
        print("Failed to get AI response")
        return {}
    
    # Parse the JSON response
    try:
        ai_response = json.loads(ai_response_json)
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response JSON: {e}")
        print(f"Raw response: {ai_response_json}")
        return {}
    
    # Extract stakeholders from conversation
    ai_stakeholders = slack_service.extract_user_ids_from_conversation(conversation_text)
    
    # Filter out bots - only keep human stakeholders
    human_stakeholders = slack_service.filter_human_stakeholders(ai_stakeholders)
    
    # Extract various issue references
    issue_refs = slack_service.extract_all_issue_references(conversation_text)
    
    # Generate concise thread name
    ai_thread_name = generate_ai_thread_name(ai_response)
    
    return {
        'ai_thread_name': ai_thread_name,
        'ai_description': ai_response.get('reasoning', 'No description available'),
        'ai_stakeholders': human_stakeholders,
        'ai_priority': ai_response.get('priority'),
        'ai_confidence': ai_response.get('confidence_score'),
        'github_issue': issue_refs.get('github_issues', [None])[0] if issue_refs.get('github_issues') else None,
        'jira_ticket': issue_refs.get('jira_tickets', [None])[0] if issue_refs.get('jira_tickets') else None,
        'thread_issue': issue_refs.get('thread_issues', [None])[0] if issue_refs.get('thread_issues') else None,
        'ai_analysis_json': ai_response_json,
        'ai_response': ai_response
    }

def main():
    """Main workflow with automatic database setup."""
    print("🚀 Open Threads Reminder - Enhanced Workflow")
    print("=" * 60)
    
    # Step 1: Ensure database setup
    setup_performed = ensure_database_setup()
    
    if setup_performed:
        verify_enhanced_setup()
    
    # Step 2: Initialize services
    print("🔧 Initializing services...")
    DB_CONFIG["dbname"] = DB_NAME
    
    db = DBClient(DB_CONFIG)
    slack_service = SlackService()
    vertex_ai = VertexAIClient()
    
    print("✅ All services initialized!")
    print("\n🎯 Starting enhanced thread processing workflow...")

    # Get last THREAD_CYCLE (90) days threads, which are open from database.
    for channel in channels:
        channel_id = channel['channel_id']
        table_name = channel['channel_name'].replace("-", "_")
        
        print(f"\n=== Processing Channel: {channel['channel_name']} ===")
        
        threads = db.get_open_threads_within_range(
            table=table_name, days=ACTIVE_THREAD_CYCLE
        )
        print(f"Found {len(threads)} open threads in channel {channel['channel_name']}.")
        
        for stored_thread_info in threads:
            print(f"\nProcessing thread: {stored_thread_info['thread_ts']}")
            
            # Check if the len of conversations is matching
            # the len of conversation stored in database.
            current_thread_info = slack_service.fetch_thread_info(
                stored_thread_info['thread_ts'],
                stored_thread_info['channel_id']
            )
            
            # Ensure current_thread_info['last_reply'] is timezone-aware for comparison
            last_reply = current_thread_info['last_reply']
            if isinstance(last_reply, datetime) and last_reply.tzinfo is None:
                last_reply = last_reply.replace(tzinfo=timezone.utc)
            elif isinstance(last_reply, str):
                try:
                    # Try parsing as timestamp first
                    last_reply = datetime.fromtimestamp(float(last_reply), tz=timezone.utc)
                except ValueError:
                    # Fall back to ISO format
                    last_reply = datetime.fromisoformat(last_reply.replace('Z', '+00:00'))
            
            if stored_thread_info['reply_count'] < current_thread_info['reply_count']:
                # Will not proceed to validate, since new reply has been added in 24 hours.
                print(f"New reply found in thread {stored_thread_info['thread_ts']} in channel {stored_thread_info['channel_id']}.")
                db.update_thread_reply_count(
                    table=table_name,
                    thread_id=stored_thread_info['thread_ts'],
                    channel_id=stored_thread_info["channel_id"],
                    reply_count=current_thread_info["reply_count"],
                    last_reply=current_thread_info["latest_reply"]
                )
            elif last_reply < (datetime.now(timezone.utc) - get_timedelta_for_config(ACTIVE_RESPONSE_LIMIT, ACTIVE_TIME_UNIT)):
                print(f"Thread {stored_thread_info['thread_ts']} is inactive (>{ACTIVE_RESPONSE_LIMIT} {ACTIVE_TIME_UNIT}), processing AI analysis...")
                
                # Fetch the actual thread conversation
                conversation_text = slack_service.fetch_thread_replies(
                    channel_id=stored_thread_info['channel_id'],
                    thread_ts=stored_thread_info['thread_ts']
                )
                
                # Clean conversation text (NER)
                doc = nlp(conversation_text)
                clean_conversation_text = conversation_text

                for ent in reversed(doc.ents):
                    if ent.label_ in ["ORG"]:
                        clean_conversation_text = (
                            clean_conversation_text[:ent.start_char]
                             + "[COMPANY]"
                             + clean_conversation_text[ent.end_char:]
                        )
                
                # Process AI analysis
                ai_data = process_ai_analysis(slack_service, clean_conversation_text, current_thread_info, stored_thread_info)
                ai_response = ai_data['ai_response']
                
                print(f"AI Analysis: {ai_response['thread_state']} (Priority: {ai_response['priority']}, Confidence: {ai_data['ai_confidence']})")
                
                # Store enhanced data back to database
                enhanced_thread_data = {
                    'thread_ts': stored_thread_info['thread_ts'],
                    'channel_id': stored_thread_info['channel_id'],
                    'user_id': stored_thread_info['user_id'],
                    'reply_count': current_thread_info['reply_count'],
                    'latest_reply': current_thread_info['latest_reply'],
                    'status': stored_thread_info['status'],
                    **ai_data
                }
                db.store_thread_in_table(table_name, enhanced_thread_data)
                
                # Show all found references for debugging
                issue_refs = ai_data.get('ai_response', {}).get('issue_references', {})
                if issue_refs.get('github_issues'):
                    print(f"   Found GitHub issues: {issue_refs['github_issues']}")
                if issue_refs.get('jira_tickets'):
                    print(f"   Found Jira tickets: {issue_refs['jira_tickets']}")
                if issue_refs.get('thread_issues'):
                    print(f"   Found thread issues: {issue_refs['thread_issues']}")
                
                # Cache user profiles for stakeholders
                if ai_data['ai_stakeholders']:
                    slack_service.resolve_stakeholders(ai_data['ai_stakeholders'], db)
                
                if ai_response["thread_state"] == "open":
                    # Check bot message cooldown before sending
                    cooldown_minutes = ACTIVE_BOT_COOLDOWN if ACTIVE_TIME_UNIT == "minutes" else ACTIVE_BOT_COOLDOWN * 60
                    can_send = db.can_bot_send_message(
                        table=table_name,
                        thread_ts=stored_thread_info['thread_ts'],
                        channel_id=stored_thread_info['channel_id'],
                        cooldown_minutes=cooldown_minutes
                    )
                    
                    if not can_send:
                        print(f"⏳ Bot message cooldown active - skipping reminder for thread {stored_thread_info['thread_ts']}")
                        print(f"   Cooldown: {ACTIVE_BOT_COOLDOWN} {ACTIVE_TIME_UNIT} between bot messages")
                        continue
                    
                    # Smart activity detection: Check if there's recent human activity
                    inactivity_threshold = datetime.now(timezone.utc) - get_timedelta_for_config(ACTIVE_RESPONSE_LIMIT, ACTIVE_TIME_UNIT)
                    activity_check = slack_service.check_recent_activity_source(
                        channel_id=stored_thread_info['channel_id'],
                        thread_ts=stored_thread_info['thread_ts'],
                        since_timestamp=inactivity_threshold
                    )
                    
                    # If there's recent human activity, skip reminder (thread is active)
                    if activity_check['has_human_activity']:
                        print(f"👥 Recent human activity detected - thread is active, skipping reminder")
                        print(f"   Latest human reply: {activity_check['latest_human_reply']}")
                        print(f"   Total new replies: {activity_check['total_new_replies']}")
                        continue
                    
                    print(f"💬 No recent human activity detected - proceeding with reminder")
                    if activity_check['has_bot_activity']:
                        print(f"   (Bot activity found: {activity_check['latest_bot_reply']})")
                    
                    # Check if this is a repeat reminder
                    previous_bot_message_info = None
                    try:
                        # Get the timestamp of the last bot message
                        query = sql.SQL("SELECT last_bot_message_ts FROM {} WHERE thread_ts = %s AND channel_id = %s").format(sql.Identifier(table_name))
                        db.cursor.execute(query, (stored_thread_info['thread_ts'], stored_thread_info['channel_id']))
                        result = db.cursor.fetchone()
                        if result and result['last_bot_message_ts']:
                            previous_bot_message_info = result['last_bot_message_ts']
                    except Exception as e:
                        print(f"Warning: Could not fetch previous bot message timestamp: {e}")
                    
                    is_repeat_reminder = previous_bot_message_info is not None
                    
                    # Create stakeholder mentions for tagging (filter out bots)
                    stakeholder_mentions = []
                    if ai_response.get('stakeholders'):
                        # Filter AI-generated stakeholders to remove bots
                        human_ai_stakeholders = slack_service.filter_human_stakeholders(ai_response['stakeholders'])
                        stakeholder_mentions = [f"<@{user_id}>" for user_id in human_ai_stakeholders]
                    
                    # Also add conversation-extracted stakeholders (already filtered)
                    conversation_stakeholders = ai_data.get('ai_stakeholders', [])
                    for user_id in conversation_stakeholders:
                        mention = f"<@{user_id}>"
                        if mention not in stakeholder_mentions:
                            stakeholder_mentions.append(mention)
                    
                    # Format open questions if available
                    open_questions_text = "None"
                    if ai_response.get('open_questions_left'):
                        questions = [q.get('question', 'Unknown question') for q in ai_response['open_questions_left']]
                        open_questions_text = ', '.join(questions)
                    elif ai_response.get('action_items'):
                        open_questions_text = ', '.join(ai_response['action_items'])
                    
                    # Priority emoji mapping with escalation for repeats
                    priority_emoji = {
                        "high": "🔴",
                        "medium": "🟡", 
                        "low": "🟢",
                        "none": "⚪"
                    }
                    
                    # Escalate urgency for repeat reminders
                    original_priority = ai_response.get('priority', 'none')
                    display_priority = original_priority
                    urgency_indicator = ""
                    
                    if is_repeat_reminder:
                        # Escalate priority visually for repeat reminders
                        if original_priority == "low":
                            display_priority = "medium"
                            urgency_indicator = " ⚠️ ESCALATED"
                        elif original_priority == "medium":
                            display_priority = "high" 
                            urgency_indicator = " 🚨 CRITICAL"
                        elif original_priority == "high":
                            urgency_indicator = " 💥 URGENT - REPEATED"
                        else:  # none
                            display_priority = "medium"
                            urgency_indicator = " ⚠️ NEEDS ATTENTION"
                    
                    priority_color = priority_emoji.get(display_priority, "⚪")
                    
                    # Customize message header based on reminder type
                    if is_repeat_reminder:
                        # Calculate time since last reminder
                        # Ensure both datetimes are timezone-aware
                        if previous_bot_message_info.tzinfo is None:
                            previous_bot_message_info = previous_bot_message_info.replace(tzinfo=timezone.utc)
                        
                        time_since_last = datetime.now(timezone.utc) - previous_bot_message_info
                        if time_since_last.days > 0:
                            time_ago = f"{time_since_last.days} days ago"
                        elif time_since_last.seconds > 3600:
                            hours = time_since_last.seconds // 3600
                            time_ago = f"{hours} hours ago"
                        else:
                            minutes = time_since_last.seconds // 60
                            time_ago = f"{minutes} minutes ago"
                        
                        header = f"🔄 *Follow-up Thread Reminder*{urgency_indicator}\n\n"
                        inactive_text = f"This thread is **still inactive** after our previous reminder ({time_ago}). *This may be critical* - please review urgently.\n\n"
                    else:
                        header = f"🚨 *Thread Reminder Alert*\n\n"
                        inactive_text = f"This thread has been inactive for *{ACTIVE_RESPONSE_LIMIT} {ACTIVE_TIME_UNIT}*. Please review and take action.\n\n"
                    
                    # Format enhanced message with dynamic urgency
                    final_message = header + inactive_text
                    
                    # Summary section with blue color
                    final_message += f"```📋 SUMMARY```\n"
                    final_message += f">{ai_response['reasoning']}\n\n"
                    
                    # Priority and action items in colored blocks
                    final_message += f"```🎯 DETAILS```\n"
                    final_message += f">🔸 *Priority:* {priority_color} {display_priority.upper()}{urgency_indicator}\n"
                    final_message += f">🔸 *Action Items:* {open_questions_text}\n"
                    final_message += f">🔸 *Team:* {' '.join(stakeholder_mentions) if stakeholder_mentions else 'None assigned'}\n"
                    
                    # Add issue references if available  
                    issue_refs = []
                    if ai_data.get('github_issue'):
                        issue_refs.append(f"GitHub: {ai_data['github_issue']}")
                    if ai_data.get('jira_ticket'):
                        issue_refs.append(f"Jira: {ai_data['jira_ticket']}")
                    if ai_data.get('thread_issue'):
                        issue_refs.append(f"Thread: {ai_data['thread_issue']}")
                    
                    if issue_refs:
                        final_message += f">🔸 *Related Issues:* {' | '.join(issue_refs)}\n"
                    
                    # Stronger call-to-action for repeat reminders
                    if is_repeat_reminder:
                        final_message += f"\n🚨 **URGENT ACTION REQUIRED** - Previous reminder was ignored.\n"
                        final_message += f"💬 *Please respond immediately or escalate to management.*"
                    else:
                        final_message += f"\n💬 *Please respond or update the thread status.*"

                    print(f"Sending response over slack message.")
                    print(f"Final message to be sent: {final_message}")
                    
                    # Send the message
                    message_ts = slack_service.notify_inactive_slack_thread(
                        channel_id=stored_thread_info['channel_id'],
                        message_text=final_message,
                        thread_ts=stored_thread_info['thread_ts']
                    )
                    
                    # Update bot message timestamp if message was sent successfully
                    if message_ts:
                        db.update_bot_message_timestamp(
                            table=table_name,
                            thread_ts=stored_thread_info['thread_ts'],
                            channel_id=stored_thread_info['channel_id']
                        )
                        print(f"✅ Bot message timestamp updated for cooldown tracking")
                    
                    # Update thread reply count
                    db.update_thread_reply_count(
                        table=table_name,
                        thread_id=stored_thread_info['thread_ts'],
                        channel_id=stored_thread_info['channel_id'],
                        reply_count=current_thread_info['reply_count'] + 1,
                        last_reply=datetime.now(timezone.utc)
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
        
        print(f"✅ Reminder processing completed for channel {channel['channel_name']}")

        # Update last 48 hours slack threads to database
        # Since we want new threads started after yesterday but
        # to make sure we do not miss some thread in computational
        # time, so take 30 hours window and neglect already 
        # existed threads.
        print(f"\nFetching new threads for channel {channel['channel_name']}...")
        new_threads = slack_service.fetch_messages_within_range(
            channel_id=channel["channel_id"],
            days=2
        )
        print(f"Found {len(new_threads)} new threads to process")

        # Update database with current situation.
        for thread_info in new_threads:
            # For new threads, we don't have AI analysis yet
            thread_data = {
                **thread_info,
                'ai_thread_name': None,
                'ai_description': None,
                'ai_stakeholders': json.dumps([]),
                'ai_priority': None,
                'ai_confidence': None,
                'github_issue': None,
                'jira_ticket': None,
                'thread_issue': None,
                'ai_analysis_json': None,
                'last_bot_message_ts': None
            }
            
            db.store_thread_in_table(
                table=table_name,
                thread_data=thread_data
            )
        
        # Update channel statistics
        print(f"Updating channel statistics for {channel['channel_name']}...")
        db.update_channel_stats(channel['channel_id'])

    print("\n🎉 Enhanced workflow completed successfully!")
    
    # Show actual database state instead of misleading "contains" messages
    print("📊 Workflow Summary:")
    
    total_threads_processed = 0
    total_ai_analyzed = 0
    total_profiles_cached = 0
    
    # Count actual data for each channel
    for channel in channels:
        table_name = channel['channel_name'].replace("-", "_")
        try:
            # Count total threads
            db.cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            thread_count = db.cursor.fetchone()['count']
            total_threads_processed += thread_count
            
            # Count AI analyzed threads
            db.cursor.execute(f"SELECT COUNT(*) as count FROM {table_name} WHERE ai_thread_name IS NOT NULL")
            ai_count = db.cursor.fetchone()['count']
            total_ai_analyzed += ai_count
            
            print(f"  📢 {channel['channel_name']}: {thread_count} threads ({ai_count} AI analyzed)")
            
        except Exception as e:
            print(f"  📢 {channel['channel_name']}: Error reading data - {e}")
    
    # Count cached user profiles
    try:
        db.cursor.execute("SELECT COUNT(*) as count FROM user_profiles")
        total_profiles_cached = db.cursor.fetchone()['count']
    except Exception as e:
        print(f"  👥 User profiles: Error reading data - {e}")
    
    print(f"\n📈 Database State:")
    print(f"  🧵 Total threads: {total_threads_processed}")
    print(f"  🤖 AI analyzed: {total_ai_analyzed}")
    print(f"  👥 User profiles cached: {total_profiles_cached}")
    
    if total_threads_processed == 0:
        print(f"\n💡 Next Steps:")
        print(f"  1. Add the bot to #{channels[0]['channel_name']} channel in Slack")
        print(f"  2. Create some test threads and wait {ACTIVE_RESPONSE_LIMIT} {ACTIVE_TIME_UNIT}")
        print(f"  3. Run 'python main.py' again to see AI analysis in action")
    else:
        print(f"\n✨ Enhanced Features Available:")
        print(f"  ✅ AI thread names and descriptions")
        print(f"  ✅ GitHub/Jira/Thread issue tracking")
        print(f"  ✅ User profile caching with Slack DPs")
        print(f"  ✅ Smart reminder notifications")

    db.close()

if __name__ == "__main__":
    main()