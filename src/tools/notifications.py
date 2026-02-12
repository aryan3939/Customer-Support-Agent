"""
Notification Tools — send alerts to agents and teams.

Simulates Slack/email notifications for escalations and updates.
"""

from src.utils.logging import get_logger

logger = get_logger(__name__)


async def notify_slack(
    channel: str,
    message: str,
    ticket_id: str = "",
    priority: str = "medium",
) -> dict:
    """
    Send a notification to a Slack channel.
    In production: uses Slack Webhook API.
    """
    logger.info(
        "slack_notification_sent",
        channel=channel,
        ticket_id=ticket_id,
        priority=priority,
    )
    
    return {
        "status": "sent",
        "channel": channel,
        "message_preview": message[:100],
    }


async def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
    ticket_id: str = "",
) -> dict:
    """
    Send an email notification.
    In production: uses SendGrid/SES API.
    """
    logger.info(
        "email_notification_sent",
        to=to_email,
        subject=subject,
        ticket_id=ticket_id,
    )
    
    return {
        "status": "sent",
        "to": to_email,
        "subject": subject,
    }
