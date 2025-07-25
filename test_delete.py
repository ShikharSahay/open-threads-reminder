from slack_services.init_slack import SlackService

slack_service = SlackService()

print("🤖 Testing Bot Message Deletion")
print("=" * 50)
print("\nTesting deletion of USER MESSAGE (should fail):")
print("   Attempting to delete ts: 1753346878.747939")
result1 = slack_service.delete_message(
    channel_id="C096TJLR1GF",
    message_ts="1753346878.747939"
)

# Test 2: Post and delete our own bot message (should work)
print("\n2️Testing deletion of BOT'S OWN MESSAGE:")
try:
    # Post a test message
    print("Posting test message...")
    response = slack_service.client.chat_postMessage(
        channel="C096TJLR1GF",
        text="Test message from bot - will be deleted in 3 seconds"
    )
    
    if response['ok']:
        bot_message_ts = response['ts']
        print(f"Posted bot message with ts: {bot_message_ts}")
        
        import time
        time.sleep(3)
        
        # Delete the bot's own message (should work)
        print("Deleting bot's own message...")
        result2 = slack_service.delete_message(
            channel_id="C096TJLR1GF",
            message_ts=bot_message_ts
        )
    else:
        print(f"Failed to post test message: {response}")
        
except Exception as e:
    print(f"Error in test 2: {e}")

# Test 3: Safe delete with verification (recommended approach)
print("\n3️⃣ Testing SAFE DELETE WITH VERIFICATION:")
print("   This verifies message ownership before attempting deletion")
safe_result = slack_service.delete_bot_message(
    channel_id="C096TJLR1GF",
    message_ts="1753346878.747939"
)

print("\n📋 Summary:")
print("Bot tokens can ONLY delete messages posted by that specific bot")
print("Use delete_message() for direct deletion (fastest)")
print("Use delete_bot_message() for safe deletion with verification (recommended)")
print("Both methods will fail gracefully if trying to delete non-bot messages")

