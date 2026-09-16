"""
Notification Service - Event-driven alerts across SMS, Email, and In-App notifications.
"""
from typing import List, Dict, Any
from datetime import datetime


class NotificationService:
    """Dispatches asynchronous alerts upon critical land stack events."""

    def __init__(self):
        self._sent_notifications: List[Dict[str, Any]] = []

    def notify(
        self,
        event_type: str,
        recipient: str,
        subject: str,
        message: str,
        channel: str = "IN_APP"  # SMS, EMAIL, IN_APP
    ) -> Dict[str, Any]:
        """Send notification and archive in event history."""
        notif = {
            "notification_id": f"NOTIF-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:18]}",
            "event_type": event_type,
            "recipient": recipient,
            "channel": channel,
            "subject": subject,
            "message": message,
            "status": "DELIVERED",
            "timestamp": datetime.utcnow().isoformat()
        }
        self._sent_notifications.append(notif)
        return notif

    def get_recipient_notifications(self, recipient: str) -> List[Dict[str, Any]]:
        """Fetch notifications for a citizen or officer."""
        return [n for n in self._sent_notifications if n["recipient"] == recipient]


notification_service = NotificationService()
