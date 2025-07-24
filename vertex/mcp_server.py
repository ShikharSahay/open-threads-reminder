import asyncio
import json
from typing import Any, Dict, List
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .client import VertexAIClient
from .enums import ThreadState, ReminderAction

class ThreadClassificationMCPServer:
    def __init__(self):
        self.server = Server("thread-classification")
        self.vertex_client = VertexAIClient()
        self._register_tools()
        
    def _register_tools(self):
        """Register MCP tools for thread classification and reminder management"""
        
        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="classify_conversation",
                    description="Classify a conversation using Gemini 2.5 Pro to determine state and priority",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_text": {
                                "type": "string", 
                                "description": "The conversation text to analyze and classify"
                            },
                            "conversation_id": {
                                "type": "string", 
                                "description": "Optional identifier for the conversation",
                                "default": "conv-1"
                            }
                        },
                        "required": ["conversation_text"]
                    }
                ),
                types.Tool(
                    name="check_reminder_eligibility",
                    description="Determine if a conversation requires a reminder based on classification and time elapsed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "classification": {
                                "type": "object", 
                                "description": "Classification result from classify_conversation tool"
                            },
                            "days_since_activity": {
                                "type": "integer", 
                                "description": "Number of days since last activity in the conversation"
                            }
                        },
                        "required": ["classification", "days_since_activity"]
                    }
                ),
                types.Tool(
                    name="process_sample_conversations",
                    description="Process and classify multiple sample conversations for demonstration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_detailed_analysis": {
                                "type": "boolean",
                                "description": "Include detailed classification reasoning in results",
                                "default": True
                            }
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            try:
                if name == "classify_conversation":
                    return await self._handle_classify_conversation(arguments)
                elif name == "check_reminder_eligibility":
                    return await self._handle_check_reminder_eligibility(arguments)
                elif name == "process_sample_conversations":
                    return await self._handle_process_sample_conversations(arguments)
                else:
                    return [types.TextContent(
                        type="text", 
                        text=f"Error: Unknown tool '{name}'. Available tools: classify_conversation, check_reminder_eligibility, process_sample_conversations"
                    )]
            except Exception as e:
                return [types.TextContent(
                    type="text", 
                    text=f"Tool execution error: {str(e)}"
                )]

    async def _handle_classify_conversation(self, arguments: dict) -> list[types.TextContent]:
        """Handle single conversation classification"""
        conversation_text = arguments.get("conversation_text", "")
        conversation_id = arguments.get("conversation_id", "conv-1")
        
        if not conversation_text.strip():
            return [types.TextContent(
                type="text",
                text="Error: conversation_text cannot be empty"
            )]
        
        classification = self.vertex_client.classify_thread(conversation_text)
        
        result = {
            "conversation_id": conversation_id,
            "conversation_length": len(conversation_text),
            "classification": classification,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        return [types.TextContent(
            type="text", 
            text=json.dumps(result, indent=2, ensure_ascii=False)
        )]

    async def _handle_check_reminder_eligibility(self, arguments: dict) -> list[types.TextContent]:
        """Handle reminder eligibility check"""
        classification = arguments.get("classification", {})
        days_since_activity = arguments.get("days_since_activity", 0)
        
        if not classification:
            return [types.TextContent(
                type="text",
                text="Error: classification object is required"
            )]
        
        reminder_decision = self.vertex_client.should_send_reminder(
            classification, 
            days_since_activity
        )
        
        result = {
            "days_since_activity": days_since_activity,
            "thread_state": classification.get("thread_state"),
            "priority": classification.get("priority"),
            "reminder_decision": reminder_decision,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        return [types.TextContent(
            type="text", 
            text=json.dumps(result, indent=2, ensure_ascii=False)
        )]

    async def _handle_process_sample_conversations(self, arguments: dict) -> list[types.TextContent]:
        """Handle batch processing of sample conversations"""
        include_detailed = arguments.get("include_detailed_analysis", True)
        
        sample_conversations = [
            {
                "id": "urgent-bug-report",
                "text": "Sarah: We have a critical production bug affecting user logins. The authentication service is returning 500 errors. Mike: I'm investigating now, this is blocking all new signups. Sarah: Revenue impact is significant, need immediate fix. Mike: Found the issue - database connection pool exhausted. Deploying fix in 10 minutes.",
                "days_since_activity": 2
            },
            {
                "id": "feature-completion",
                "text": "Alex: The new dashboard feature has been successfully implemented and tested. All unit tests pass, integration tests complete. Lisa: Excellent work! I've reviewed the code and it looks solid. Alex: Deployed to production, monitoring shows everything running smoothly. Lisa: Perfect, marking this ticket as resolved.",
                "days_since_activity": 1
            },
            {
                "id": "deferred-enhancement",
                "text": "Tom: Should we implement the advanced search functionality for the next release? Emma: That's a good idea but let's defer it to Q2. We have higher priority security features to focus on first. Tom: Makes sense, I'll add it to the backlog for future consideration. Emma: Good plan, we can revisit after the security audit is complete.",
                "days_since_activity": 8
            },
            {
                "id": "casual-conversation",
                "text": "Jessica: Anyone interested in grabbing lunch at the new Thai place? David: Count me in! I heard they have excellent pad thai. Jessica: Great! Let's meet at the lobby at 12:30. David: Perfect, see you then. Looking forward to trying their green curry too.",
                "days_since_activity": 3
            },
            {
                "id": "planning-discussion",
                "text": "Rachel: We need to plan the architecture for the new microservice. Should we use Go or Node.js? Mark: Go would be better for performance, but our team has more Node.js experience. Rachel: Let's schedule a technical review meeting to discuss trade-offs. Mark: I'll set up a meeting for Friday to make the decision.",
                "days_since_activity": 5
            }
        ]
        
        results = []
        for conv in sample_conversations:
            try:
                classification = self.vertex_client.classify_thread(conv["text"])
                
                reminder_decision = self.vertex_client.should_send_reminder(
                    classification, 
                    conv["days_since_activity"]
                )
                
                conversation_result = {
                    "conversation_id": conv["id"],
                    "days_since_activity": conv["days_since_activity"],
                    "classification": classification if include_detailed else {
                        "thread_state": classification.get("thread_state"),
                        "priority": classification.get("priority"),
                        "confidence": classification.get("confidence")
                    },
                    "reminder_decision": reminder_decision,
                    "success": True
                }
                
            except Exception as e:
                conversation_result = {
                    "conversation_id": conv["id"],
                    "error": str(e),
                    "success": False
                }
            
            results.append(conversation_result)
        
        summary = {
            "total_conversations": len(sample_conversations),
            "successful_classifications": sum(1 for r in results if r.get("success", False)),
            "failed_classifications": sum(1 for r in results if not r.get("success", False)),
            "conversations_by_state": self._summarize_by_state(results),
            "reminder_eligible": sum(1 for r in results 
                                   if r.get("success", False) and 
                                   r.get("reminder_decision", {}).get("action") == ReminderAction.SEND_REMINDER.value),
            "conversations": results,
            "timestamp": datetime.now().isoformat()
        }
        
        return [types.TextContent(
            type="text", 
            text=json.dumps(summary, indent=2, ensure_ascii=False)
        )]

    def _summarize_by_state(self, results: List[Dict]) -> Dict[str, int]:
        """Create summary of conversation states"""
        state_counts = {}
        for result in results:
            if result.get("success", False):
                state = result.get("classification", {}).get("thread_state", "unknown")
                state_counts[state] = state_counts.get(state, 0) + 1
        return state_counts

    async def run(self):
        """Start the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

async def main():
    """Entry point for the MCP server"""
    server = ThreadClassificationMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main()) 