import os
from typing import Dict, Any
from dotenv import load_dotenv
from .enums import ThreadState, ReminderAction, ThreadPriority

load_dotenv()

class VertexAIClient:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
        
        # Set up authentication if credentials path is provided
        if self.credentials_path:
            if os.path.exists(self.credentials_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
                print(f"✅ Using Google Cloud credentials from: {self.credentials_path}")
            else:
                print(f"⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS path does not exist: {self.credentials_path}")
                print("   Falling back to default authentication (gcloud or default service account)")
        else:
            print("ℹ️  No GOOGLE_APPLICATION_CREDENTIALS provided, using default authentication")

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

              ONLY return a valid JSON object. DO NOT include explanations, notes, or formatting (like triple backticks). Output must be raw JSON.

              Classification Categories:
              - thread_state: one of ["open", "closed", "resolved", "deferred", "chit_chat", "unknown"]
              - priority: one of ["high", "medium", "low", "none"]

              Conversation Data:
              {conversation_data}

              Your task:
              1. Analyze the conversation.
              2. Identify the slack thread_state and priority.
              3. Extract ALL user IDs in the format U123ABC456 (e.g., [User: U123ABC456] or just U123ABC456).
              4. Identify clear action items (as a list of strings).
              5. Identify unresolved questions with the user being asked.
              6. Return ONLY a JSON object matching the exact structure below — no extra text, markdown, or code blocks.

              Required JSON format:
              {{
                "thread_state": "one of: open, closed, resolved, deferred, chit_chat, unknown",
                "priority": "one of: high, medium, low, none",
                "confidence_score": 0.85,
                "reasoning": "Brief explanation of classification decision",
                "action_items": ["specific", "actionable", "items"],
                "stakeholders": ["U123ABC456", "U789DEF012"],
                "open_questions_left": [
                  {{ "question": "Why is the API not working?", "asked_person": "U123ABC456" }},
                  {{ "question": "When will the database migration be completed?", "asked_person": "U789DEF012" }}
                ]
              }}

              IMPORTANT:
              - DO NOT return anything other than this JSON object.
              - DO NOT include introductory text, explanations, or code formatting like ```json.
              - If unsure, return "unknown" for thread_state or empty arrays where applicable.
              """

            
            response = model.generate_content(prompt)
            # Clean the response of markdown code blocks
            cleaned_response = response.text.replace('```json', '').replace('```', '').strip()
            return cleaned_response
            
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
        
        # Extract user IDs from conversation text
        import re
        user_ids = re.findall(r'U[A-Z0-9]{8,}', text_data)
        # Remove duplicates while preserving order
        stakeholders = list(dict.fromkeys(user_ids))
        
        urgent_keywords = ['urgent', 'critical', 'production', 'down', 'error', 'bug', 'broken']
        resolved_keywords = ['completed', 'done', 'finished', 'deployed', 'fixed', 'resolved', 'closed']
        deferred_keywords = ['defer', 'postpone', 'later', 'next sprint', 'backlog', 'future']
        casual_keywords = ['lunch', 'coffee', 'weekend', 'game', 'weather', 'vacation', 'thanks', 'hello', 'dinner']
        
        if any(word in text_lower for word in urgent_keywords):
            return {
                "thread_state": ThreadState.OPEN.value,
                "priority": ThreadPriority.HIGH.value,
                "confidence": 0.8,
                "reasoning": "Contains urgent/critical keywords",
                "action_items": ["Address urgent issue"],
                "stakeholders": stakeholders
            }
        elif any(word in text_lower for word in resolved_keywords):
            return {
                "thread_state": ThreadState.RESOLVED.value,
                "priority": ThreadPriority.NONE.value,
                "confidence": 0.8,
                "reasoning": "Contains completion keywords",
                "action_items": [],
                "stakeholders": stakeholders
            }
        elif any(word in text_lower for word in deferred_keywords):
            return {
                "thread_state": ThreadState.DEFERRED.value,
                "priority": ThreadPriority.MEDIUM.value,
                "confidence": 0.8,
                "reasoning": "Contains deferral keywords",
                "action_items": ["Schedule for later"],
                "stakeholders": stakeholders
            }
        elif any(word in text_lower for word in casual_keywords):
            return {
                "thread_state": ThreadState.CHIT_CHAT.value,
                "priority": ThreadPriority.NONE.value,
                "confidence": 0.9,
                "reasoning": "Contains casual conversation keywords",
                "action_items": [],
                "stakeholders": stakeholders
            }
        else:
            return {
                "thread_state": ThreadState.OPEN.value,
                "priority": ThreadPriority.MEDIUM.value,
                "confidence": 0.6,
                "reasoning": "Default classification for active discussion",
                "action_items": ["Review and respond"],
                "stakeholders": stakeholders
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
