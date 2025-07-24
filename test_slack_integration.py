#!/usr/bin/env python3
"""
Test script to fetch real Slack conversations and classify them
"""
import os
import json
from datetime import datetime

# Set up environment
os.environ['GOOGLE_CLOUD_PROJECT'] = 'hackathon-2025-463220'

def test_slack_integration():
    """Fetch real Slack conversations and classify them"""
    print("🔌 Testing Slack Integration with VertexAI Classification")
    print("=" * 60)
    
    try:
        # Import Slack service and VertexAI client
        from slack.init_slack import SlackService
        from vertex.client import VertexAIClient
        
        print("✅ Successfully imported Slack and VertexAI services")
        
        # Initialize services
        slack_service = SlackService()
        vertex_client = VertexAIClient()
        
        # Channel ID
        channel_id = "C096TJLR1GF"
        
        print(f"\n📥 Fetching messages from channel: {channel_id}")
        print("   Looking back 7 days...")
        
        # Fetch messages
        messages = slack_service.fetch_messages_within_range(
            channel_id=channel_id,
            days=7,
            messages_per_call=50
        )
        
        print(f"\n📊 Found {len(messages)} messages")
        if not messages:
            print("❌ No messages found. Check channel access and SLACK_BOT_TOKEN.")
            return False
        
        classified_conversations = []
        
        for i, message in enumerate(messages[:5]):
            if message.get('reply_count', 0) > 0:
                print(f"\n--- Message {i+1} ---")
                print(f"👤 User: {message['user']} | 💬 Replies: {message['reply_count']}")
                
                # Get thread replies
                thread_replies = slack_service.fetch_thread_replies(
                    channel_id=channel_id,
                    thread_ts=message['thread_ts']
                )
                
                if thread_replies and len(thread_replies.strip()) > 50:
                    print(f"📄 Thread preview: {thread_replies[:200]}...")
                    print("🧠 Classifying with VertexAI...")
                    
                    classification_json = vertex_client.classify_thread(thread_replies)
                    
                    try:
                        classification = json.loads(classification_json.strip())
                        
                        print(f"   📌 State: {classification.get('thread_state')}")
                        print(f"   ⚡ Priority: {classification.get('priority')}")
                        print(f"   🎯 Confidence: {classification.get('confidence')}")
                        print(f"   💡 Reason: {classification.get('reasoning', '')[:100]}...")
                        
                        # Resolve stakeholder IDs
                        stakeholder_ids = classification.get('stakeholders', [])
                        resolved_stakeholders = []
                        if stakeholder_ids:
                            print(f"   👥 Resolving {len(stakeholder_ids)} stakeholders...")
                            resolved_stakeholders = slack_service.resolve_stakeholders(stakeholder_ids)
                            for user in resolved_stakeholders:
                                print(f"     • {user['display_name']} ({user['user_id']})")
                        
                        # Simulate 2 days of inactivity
                        days_old = 2
                        reminder = vertex_client.should_send_reminder(classification_json, days_old)
                        print(f"   ⏰ Reminder: {reminder['action']} - {reminder['reason']}")
                        
                        # Append structured result
                        classified_conversations.append({
                            "message": message,
                            "classification": classification,
                            "stakeholders_resolved": resolved_stakeholders,
                            "reminder": reminder
                        })
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parsing failed: {e}")
                        print(f"   Raw response: {classification_json[:200]}...")
            else:
                print(f"🔹 Message {i+1}: No replies, skipped")
        
        # Summary
        print("\n📋 SUMMARY")
        print("=" * 40)
        print(f"Fetched: {len(messages)} messages")
        print(f"Classified: {len(classified_conversations)} conversations")
        
        if classified_conversations:
            states, priorities = {}, {}
            reminders = 0
            
            for conv in classified_conversations:
                state = conv['classification'].get('thread_state', 'unknown')
                priority = conv['classification'].get('priority', 'none')
                
                states[state] = states.get(state, 0) + 1
                priorities[priority] = priorities.get(priority, 0) + 1
                
                if conv['reminder']['action'] == 'send_reminder':
                    reminders += 1
            
            print(f"\nThread States: {states}")
            print(f"Priorities: {priorities}")
            print(f"Reminders Needed: {reminders}")
            
            # Save to file
            filename = f"slack_classification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(classified_conversations, f, indent=2, default=str)
            print(f"\n💾 Saved to: {filename}")
        
        print("\n✅ Slack integration test completed successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Ensure SLACK_BOT_TOKEN and other dependencies are correctly set")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_slack_integration()
    
    if success:
        print("\n🚀 Success! You can now process real Slack threads with AI classification.")
    else:
        print("\n🔧 Please verify your .env setup, channel ID, and GCP configuration.")
