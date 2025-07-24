import os
from typing import Dict, Any
from dotenv import load_dotenv
from .enums import ThreadState, ReminderAction, ThreadPriority

load_dotenv()

class VertexAIClient:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
        
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")

    def classify_thread(self, conversation_data) -> str:
        """
        Classify a conversation using Vertex AI Gemini 2.5 Pro
        
        Args:
            conversation_data: The conversation data (can be text or JSON)
            
        Returns:
            Raw JSON string response from VertexAI
        """
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            vertexai.init(project=self.project_id, location=self.location)
            model = GenerativeModel("gemini-2.5-pro")
            
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

            Conversation Data:
            {conversation_data}

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
            
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            # Return fallback as JSON string
            fallback = self._fallback_classify(conversation_data)
            import json
            return json.dumps(fallback)

    def _fallback_classify(self, conversation_data) -> Dict[str, Any]:
        """Rule-based fallback classification when AI fails"""
        # Convert to string if it's not already
        if isinstance(conversation_data, dict):
            import json
            text_data = json.dumps(conversation_data)
        else:
            text_data = str(conversation_data)
            
        text_lower = text_data.lower()
        
        urgent_keywords = ['urgent', 'critical', 'production', 'down', 'error', 'bug', 'broken']
        resolved_keywords = ['completed', 'done', 'finished', 'deployed', 'fixed', 'resolved', 'closed']
        deferred_keywords = ['defer', 'postpone', 'later', 'next sprint', 'backlog', 'future']
        casual_keywords = ['lunch', 'coffee', 'weekend', 'game', 'weather', 'vacation', 'thanks', 'hello']
        
        if any(word in text_lower for word in urgent_keywords):
            return {
                "thread_state": ThreadState.OPEN.value,
                "priority": ThreadPriority.HIGH.value,
                "confidence": 0.8,
                "reasoning": "Contains urgent/critical keywords",
                "action_items": ["Address urgent issue"],
                "stakeholders": ["team"]
            }
        elif any(word in text_lower for word in resolved_keywords):
            return {
                "thread_state": ThreadState.RESOLVED.value,
                "priority": ThreadPriority.NONE.value,
                "confidence": 0.8,
                "reasoning": "Contains completion keywords",
                "action_items": [],
                "stakeholders": []
            }
        elif any(word in text_lower for word in deferred_keywords):
            return {
                "thread_state": ThreadState.DEFERRED.value,
                "priority": ThreadPriority.MEDIUM.value,
                "confidence": 0.8,
                "reasoning": "Contains deferral keywords",
                "action_items": ["Schedule for later"],
                "stakeholders": ["team"]
            }
        elif any(word in text_lower for word in casual_keywords):
            return {
                "thread_state": ThreadState.CHIT_CHAT.value,
                "priority": ThreadPriority.NONE.value,
                "confidence": 0.9,
                "reasoning": "Contains casual conversation keywords",
                "action_items": [],
                "stakeholders": []
            }
        else:
            return {
                "thread_state": ThreadState.OPEN.value,
                "priority": ThreadPriority.MEDIUM.value,
                "confidence": 0.6,
                "reasoning": "Default classification for active discussion",
                "action_items": ["Review and respond"],
                "stakeholders": ["team"]
            }

    def should_send_reminder(self, classification_json: str, days_since_activity: int) -> Dict[str, Any]:
        """
        Determine reminder eligibility based on classification and time
        
        Args:
            classification_json: JSON string classification result
            days_since_activity: Days since last activity
            
        Returns:
            Dict with reminder decision and details
        """
        try:
            import json
            # Clean the JSON string of code blocks
            cleaned_json = classification_json.replace('```json', '').replace('```', '').strip()
            classification = json.loads(cleaned_json)
        except:
            # If JSON parsing fails, return no reminder
            return {
                "action": ReminderAction.NO_REMINDER.value,
                "reason": "Invalid classification format",
                "reminder_text": None
            }
            
        thread_state = classification.get("thread_state")
        priority = classification.get("priority")
        
        no_reminder_states = {
            ThreadState.CLOSED.value,
            ThreadState.RESOLVED.value,
            ThreadState.CHIT_CHAT.value
        }
        
        if thread_state in no_reminder_states:
            return {
                "action": ReminderAction.NO_REMINDER.value,
                "reason": f"No reminders for {thread_state} threads",
                "reminder_text": None
            }
        
        thresholds = {
            ThreadPriority.HIGH.value: 1,
            ThreadPriority.MEDIUM.value: 3,
            ThreadPriority.LOW.value: 7,
            ThreadPriority.NONE.value: 14
        }
        
        threshold = thresholds.get(priority, 7)
        
        if days_since_activity >= threshold:
            return {
                "action": ReminderAction.SEND_REMINDER.value,
                "reason": f"Inactive for {days_since_activity} days (threshold: {threshold})",
                "reminder_text": self._generate_reminder_text(classification, days_since_activity),
                "priority": priority,
                "stakeholders": classification.get("stakeholders", [])
            }
        
        return {
            "action": ReminderAction.NO_REMINDER.value,
            "reason": f"Below threshold ({days_since_activity} < {threshold} days)",
            "reminder_text": None
        }

    def _generate_reminder_text(self, classification: Dict[str, Any], days_inactive: int) -> str:
        """Generate contextual reminder text"""
        state = classification.get("thread_state")
        priority = classification.get("priority")
        action_items = classification.get("action_items", [])
        
        if state == ThreadState.DEFERRED.value:
            base_text = f"Deferred thread reminder: {days_inactive} days inactive."
        elif state == ThreadState.OPEN.value:
            base_text = f"Open thread reminder: {days_inactive} days inactive."
        else:
            base_text = f"Thread attention needed: {days_inactive} days inactive."
        
        if action_items:
            base_text += f"\n\nPending actions:\n" + "\n".join([f"- {item}" for item in action_items])
        
        if priority in [ThreadPriority.HIGH.value, ThreadPriority.MEDIUM.value]:
            base_text += f"\n\nPriority: {priority.upper()}"
        
        base_text += "\n\nPlease review and update."
        return base_text
