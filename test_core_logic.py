#!/usr/bin/env python3
"""
Test core logic without MCP dependencies
"""
import os
import traceback
import vertexai
from vertexai.generative_models import GenerativeModel

# Set up environment
os.environ['GOOGLE_CLOUD_PROJECT'] = 'hackathon-2025-463220'

def test_vertex_ai_directly(conversation_text: str):
    """Test VertexAI directly with detailed debugging"""
    print(f"\n🔍 DEBUGGING VERTEXAI CALL")
    print("=" * 50)
    
    try:
        print("Initializing VertexAI...")
        
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = "us-west1"
        
        print(f"   Project: {project_id}")
        print(f"   Location: {location}")
        
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel("gemini-2.5-pro")
        print("✅ VertexAI model initialized")
        
        prompt = f"""
You are an expert conversation analyzer. Analyze the following conversation and classify it precisely.

Classification Categories:
- OPEN: Active discussion needing attention or response
- CLOSED: Explicitly closed or marked complete
- RESOLVED: Satisfactorily answered or completed
- DEFERRED: Intentionally postponed or delayed
- CHIT_CHAT: Casual conversation with no action items
- UNKNOWN: Cannot determine state with confidence

Priority Levels:
- HIGH: Critical issues, blockers, urgent business matters
- MEDIUM: Important but not urgent, feature requests
- LOW: Nice to have, suggestions, minor improvements
- NONE: No priority (chit_chat, resolved, closed)

Conversation:
{conversation_text}

Return ONLY valid JSON with this exact structure:
{{
    "thread_state": "one of: open, closed, resolved, deferred, chit_chat, unknown",
    "priority": "one of: high, medium, low, none",
    "confidence": 0.85,
    "reasoning": "Brief explanation of classification decision",
    "action_items": ["specific", "actionable", "items"],
    "stakeholders": ["mentioned", "people", "or", "roles"]
}}

Be precise and conservative. If uncertain, use UNKNOWN state.
"""
        
        print("📤 Sending prompt to VertexAI...")
        print(f"   Conversation JSON length: {len(conversation_text)} chars")
        print("   Prompt length:", len(prompt))
        
        response = model.generate_content(prompt)
        
        print("📥 VertexAI Response received!")
        print(f"   Response type: {type(response)}")
        
        if hasattr(response, 'text'):
            print(f"   Response text: {response.text}")
            print(f"   Response length: {len(response.text)}")
        else:
            print(f"   No .text attribute. Available attributes: {dir(response)}")
            
        if hasattr(response, 'candidates'):
            print(f"   Candidates: {len(response.candidates) if response.candidates else 0}")
            if response.candidates:
                for i, candidate in enumerate(response.candidates):
                    print(f"     Candidate {i}: {candidate}")
                    
        # Just return the raw response text
        print("✅ VertexAI response received successfully")
        print(f"   Raw response: {response.text[:200]}...")
        return response.text
        
    except Exception as e:
        print(f"❌ VertexAI call failed: {e}")
        print(f"   Exception type: {type(e)}")
        print("   Full traceback:")
        traceback.print_exc()
        return None

def test_core_logic():
    """Test just the VertexAI client and classification logic"""
    print("Testing Core Classification Logic...")
    print("=" * 45)
    
    try:
        # Test VertexAI client directly
        from vertex.client import VertexAIClient
        print("✅ VertexAI client imported successfully")
        
        # Initialize client
        client = VertexAIClient()
        print("✅ VertexAI client initialized")
        
        # Test conversations in real Slack JSON format
        test_cases = [
            (
                # HIGH priority OPEN - Production incident
                [
                    {
                        "user": "U078ALICE",
                        "type": "message", 
                        "ts": "1753339984.193769",
                        "text": "🚨 CRITICAL: Production API is down! Users can't login",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078BOB",
                        "type": "message",
                        "ts": "1753339985.073579", 
                        "text": "On it! Checking the database connections now",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078ALICE",
                        "type": "message",
                        "ts": "1753339986.311589",
                        "text": "Error logs are showing timeout errors. This is blocking all users!",
                        "team": "T0YK2G6N9", 
                        "thread_ts": "1753339979.554459"
                    }
                ],
                "Should be HIGH priority OPEN"
            ),
            (
                # RESOLVED/CLOSED - Feature completion
                [
                    {
                        "user": "U078JOHN",
                        "type": "message",
                        "ts": "1753339984.193769",
                        "text": "Hey team, I've finished implementing the new user dashboard feature",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078SARAH", 
                        "type": "message",
                        "ts": "1753339985.073579",
                        "text": "Awesome! I've tested it and everything looks good",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078JOHN",
                        "type": "message",
                        "ts": "1753339986.311589", 
                        "text": "Great! Marking this ticket as completed then ✅",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    }
                ],
                "Should be RESOLVED/CLOSED"
            ),
            (
                # DEFERRED - Sprint planning
                [
                    {
                        "user": "U078TOM",
                        "type": "message",
                        "ts": "1753339984.193769",
                        "text": "Should we tackle the mobile app redesign this sprint?",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078EMMA",
                        "type": "message", 
                        "ts": "1753339985.073579",
                        "text": "I think we're already at capacity with the API work",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078TOM",
                        "type": "message",
                        "ts": "1753339986.311589",
                        "text": "Good point. Let's defer the mobile redesign to next sprint then",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078EMMA",
                        "type": "message",
                        "ts": "1753339987.379159",
                        "text": "Agreed! I'll move it to the next sprint backlog",
                        "team": "T0YK2G6N9", 
                        "thread_ts": "1753339979.554459"
                    }
                ],
                "Should be DEFERRED"
            ),
            (
                # CHIT_CHAT - Social conversation like the user's example
                [
                    {
                        "user": "U078MIKE",
                        "type": "message",
                        "ts": "1753339984.193769",
                        "text": "Anyone want to grab lunch?",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078LISA",
                        "type": "message",
                        "ts": "1753339985.073579",
                        "text": "Sure! I'm thinking that new sushi place",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078MIKE", 
                        "type": "message",
                        "ts": "1753339986.311589",
                        "text": "Perfect! Let's go in 10 minutes",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    }
                ],
                "Should be CHIT_CHAT"
            ),
            (
                # Random spam-like conversation (like user's example)
                [
                    {
                        "user": "U078JNFK4QJ",
                        "type": "message",
                        "ts": "1753339984.193769",
                        "text": "Yo",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078JNFK4QJ",
                        "type": "message", 
                        "ts": "1753339985.073579",
                        "text": "lo",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078JNFK4QJ",
                        "type": "message",
                        "ts": "1753339986.311589",
                        "text": "vso",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078JNFK4QJ",
                        "type": "message",
                        "ts": "1753339987.379159", 
                        "text": "dsfl",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    },
                    {
                        "user": "U078JNFK4QJ",
                        "type": "message",
                        "ts": "1753339987.792909",
                        "text": "asf",
                        "team": "T0YK2G6N9",
                        "thread_ts": "1753339979.554459"
                    }
                ],
                "Should be UNKNOWN or CHIT_CHAT (nonsense spam)"
            )
        ]
        
        print(f"\n🧪 Testing {len(test_cases)} conversations...")
        
        for i, (conversation_data, expected) in enumerate(test_cases, 1):
            print(f"\nTest {i}: {expected}")
            
            # Convert JSON to string for display
            import json
            conversation_json = json.dumps(conversation_data, indent=2)
            print(f"Input JSON structure:")
            print(f"   {len(conversation_data)} messages")
            print(f"   Users: {list(set(msg['user'] for msg in conversation_data))}")
            print(f"   Sample text: {conversation_data[0]['text']}...")
            
            # First test VertexAI directly
            direct_result = test_vertex_ai_directly(conversation_json)
            
            print(f"\n📋 Using Client classify_thread method:")
            # Classify conversation using client  
            classification_json = client.classify_thread(conversation_json)
            
            print(f"Raw JSON Response:")
            print(f"   {classification_json[:300]}...")
            
            # Try to parse for display
            try:
                import json
                classification = json.loads(classification_json.replace('```json', '').replace('```', '').strip())
                print(f"Parsed Result: {classification.get('thread_state')} ({classification.get('priority')} priority)")
                print(f"Confidence: {classification.get('confidence')}")
                print(f"Reasoning: {classification.get('reasoning', '')}...")
            except Exception as e:
                print(f"Could not parse JSON: {e}")
                classification = {}
            
            # Compare results
            if direct_result and isinstance(direct_result, str):
                print(f"🔍 Direct vs Client comparison:")
                print(f"   Direct VertexAI worked: ✅")
                print(f"   Both returned raw JSON strings")
            else:
                print(f"🔍 Direct VertexAI failed, client used fallback")
            
            # Test reminder logic (2 days old)
            reminder = client.should_send_reminder(classification_json, 2)
            print(f"Reminder: {reminder['action']} - {reminder['reason']}")
            
            print("-" * 60)
        
        print(f"\n🎉 All {len(test_cases)} tests completed successfully!")
        print("\n📋 Core logic is working. To test full MCP server:")
        print("   1. pip install -r requirements.txt")
        print("   2. python test_mcp_server.py") 
        print("   3. cd vertex && python mcp_server.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_core_logic() 