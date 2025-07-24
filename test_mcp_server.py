#!/usr/bin/env python3
"""
Test script for the MCP server
"""
import os
import asyncio
import json

# Set up environment
os.environ['GOOGLE_CLOUD_PROJECT'] = 'hackathon-2025-463220'

async def test_mcp_server():
    """Test the MCP server functionality"""
    print("Testing MCP Server...")
    print("=" * 40)
    
    try:
        # Import the MCP server
        from vertex.mcp_server import ThreadClassificationMCPServer
        from vertex.client import VertexAIClient
        
        print("✅ MCP server imports successful")
        
        # Test VertexAI client directly
        print("\n1. Testing VertexAI Client...")
        client = VertexAIClient()
        
        test_conversation = "Alice: We have a critical production bug! Bob: I'm investigating now."
        classification_json = client.classify_thread(test_conversation)
        
        print(f"   Conversation: {test_conversation}")
        
        # Parse the JSON response to display results
        try:
            # Clean and parse the JSON response
            import json
            cleaned_json = classification_json.replace('```json', '').replace('```', '').strip()
            classification = json.loads(cleaned_json)
            
            print(f"   Classification: {classification['thread_state']} ({classification['priority']} priority)")
            print(f"   Confidence: {classification['confidence']}")
            print(f"   Reasoning: {classification['reasoning'][:100]}...")
            
        except json.JSONDecodeError as e:
            print(f"   Raw response: {classification_json[:200]}...")
            print(f"   JSON parsing failed: {e}")
            classification = {"thread_state": "unknown", "priority": "none"}
        
        # Test reminder logic (passing raw JSON string)
        print("\n2. Testing Reminder Logic...")
        reminder_decision = client.should_send_reminder(classification_json, 2)  # 2 days old
        
        print(f"   Action: {reminder_decision['action']}")
        print(f"   Reason: {reminder_decision['reason']}")
        
        if reminder_decision['action'] == 'send_reminder':
            print(f"   Reminder Text: {reminder_decision['reminder_text'][:100]}...")
        
        print("\n3. Testing MCP Server Creation...")
        server = ThreadClassificationMCPServer()
        print("✅ MCP server created successfully")
        
        print("\n🎉 All tests passed! The MCP server is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    
    if success:
        print("\n🚀 To run the MCP server:")
        print("   cd vertex && python mcp_server.py")
        print("\n📋 Available MCP tools:")
        print("   • classify_conversation")
        print("   • check_reminder_eligibility") 
        print("   • process_sample_conversations")
    else:
        print("\n🔧 Fix the errors above before running the MCP server") 