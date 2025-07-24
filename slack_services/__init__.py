"""
Slack integration module for the Open Threads Reminder app.
"""

# To import this slack functions to others parts of the code, we need to export the functions
from .init_slack import SlackService

__all__ = ['SlackService'] 