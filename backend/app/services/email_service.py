"""
Email service using SendGrid for GoalGetter.
Handles all email communications including meeting reminders, invitations, and notifications.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails via SendGrid.
    Handles email delivery with graceful degradation when SendGrid is not configured.
    """

    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        self.support_email = settings.SUPPORT_EMAIL
        self.frontend_url = settings.FRONTEND_URL
        self._sg_client = None

    @property
    def is_configured(self) -> bool:
        """Check if SendGrid is properly configured."""
        return bool(self.api_key)

    @property
    def sg_client(self):
        """Lazy-load SendGrid client."""
        if not self.is_configured:
            return None

        if self._sg_client is None:
            try:
                import sendgrid
                self._sg_client = sendgrid.SendGridAPIClient(api_key=self.api_key)
            except ImportError:
                logger.error("sendgrid package not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid client: {e}")
                return None

        return self._sg_client

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Internal method to send an email via SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Optional plain text content

        Returns:
            bool: True if email was sent successfully
        """
        if not self.is_configured:
            logger.warning(
                f"SendGrid not configured, skipping email to {to_email}: {subject}"
            )
            return False

        try:
            from sendgrid.helpers.mail import Mail, Email, To, Content

            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            if text_content:
                message.add_content(Content("text/plain", text_content))

            response = self.sg_client.send(message)

            if response.status_code in (200, 201, 202):
                logger.info(f"Email sent successfully to {to_email}: {subject}")
                return True
            else:
                logger.error(
                    f"Failed to send email to {to_email}. "
                    f"Status: {response.status_code}, Body: {response.body}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """
        Send welcome email to new users.

        Args:
            to_email: User's email address
            user_name: User's name

        Returns:
            bool: True if email was sent successfully
        """
        subject = f"Welcome to {settings.APP_NAME}! Let's achieve your goals together"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {settings.APP_NAME}!</h1>
        </div>
        <div class="content">
            <h2>Hey {user_name}!</h2>
            <p>Welcome aboard! I'm thrilled you've decided to take this journey toward achieving your goals.</p>
            <p>Here's what you can expect:</p>
            <ul>
                <li><strong>Goal Setting Phase:</strong> Work with your AI coach (yes, it's me - Tony Robbins!) to set powerful, achievable goals</li>
                <li><strong>Unlimited Coaching:</strong> During goal setting, chat with me anytime to refine your goals</li>
                <li><strong>Tracking Phase:</strong> Once your goals are set, we'll meet regularly to keep you accountable</li>
            </ul>
            <p>Remember: The path to success is to take massive, determined action!</p>
            <p style="text-align: center;">
                <a href="{self.frontend_url}" class="button">Get Started Now</a>
            </p>
            <p>Let's make your dreams a reality!</p>
            <p>Your Coach,<br><strong>Tony (AI Coach)</strong></p>
        </div>
        <div class="footer">
            <p>{settings.APP_NAME} - AI-Powered Goal Achievement</p>
            <p>Questions? Contact us at {self.support_email}</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Welcome to {settings.APP_NAME}!

Hey {user_name}!

Welcome aboard! I'm thrilled you've decided to take this journey toward achieving your goals.

Here's what you can expect:
- Goal Setting Phase: Work with your AI coach to set powerful, achievable goals
- Unlimited Coaching: During goal setting, chat with me anytime to refine your goals
- Tracking Phase: Once your goals are set, we'll meet regularly to keep you accountable

Remember: The path to success is to take massive, determined action!

Get started at: {self.frontend_url}

Let's make your dreams a reality!

Your Coach,
Tony (AI Coach)

---
{settings.APP_NAME} - AI-Powered Goal Achievement
Questions? Contact us at {self.support_email}
"""

        return self._send_email(to_email, subject, html_content, text_content)

    def send_meeting_invitation(
        self,
        to_email: str,
        user_name: str,
        meeting_time: datetime,
        duration_minutes: int = 30,
    ) -> bool:
        """
        Send meeting invitation email.

        Args:
            to_email: User's email address
            user_name: User's name
            meeting_time: Scheduled meeting datetime
            duration_minutes: Meeting duration in minutes

        Returns:
            bool: True if email was sent successfully
        """
        formatted_time = meeting_time.strftime("%B %d, %Y at %I:%M %p UTC")
        subject = f"Meeting Scheduled: {settings.APP_NAME} Coaching Session"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
        .meeting-box {{ background-color: white; border: 2px solid #4F46E5; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Meeting Scheduled!</h1>
        </div>
        <div class="content">
            <h2>Hey {user_name}!</h2>
            <p>Great news! Your coaching session has been scheduled.</p>
            <div class="meeting-box">
                <h3>Coaching Session Details</h3>
                <p><strong>Date & Time:</strong> {formatted_time}</p>
                <p><strong>Duration:</strong> {duration_minutes} minutes</p>
                <p><strong>Coach:</strong> Tony (AI Coach)</p>
            </div>
            <p>Here's what to prepare:</p>
            <ul>
                <li>Review your current goals</li>
                <li>Note any challenges you've faced</li>
                <li>Celebrate your wins (big or small!)</li>
                <li>Think about what you want to focus on next</li>
            </ul>
            <p style="text-align: center;">
                <a href="{self.frontend_url}" class="button">View Your Goals</a>
            </p>
            <p>See you there!</p>
            <p>Your Coach,<br><strong>Tony (AI Coach)</strong></p>
        </div>
        <div class="footer">
            <p>{settings.APP_NAME} - AI-Powered Goal Achievement</p>
            <p>Questions? Contact us at {self.support_email}</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Meeting Scheduled!

Hey {user_name}!

Great news! Your coaching session has been scheduled.

COACHING SESSION DETAILS
------------------------
Date & Time: {formatted_time}
Duration: {duration_minutes} minutes
Coach: Tony (AI Coach)

Here's what to prepare:
- Review your current goals
- Note any challenges you've faced
- Celebrate your wins (big or small!)
- Think about what you want to focus on next

View your goals at: {self.frontend_url}

See you there!

Your Coach,
Tony (AI Coach)

---
{settings.APP_NAME} - AI-Powered Goal Achievement
Questions? Contact us at {self.support_email}
"""

        return self._send_email(to_email, subject, html_content, text_content)

    def send_meeting_reminder(
        self,
        to_email: str,
        user_name: str,
        meeting_time: datetime,
        hours_until: int,
        duration_minutes: int = 30,
    ) -> bool:
        """
        Send meeting reminder email.

        Args:
            to_email: User's email address
            user_name: User's name
            meeting_time: Scheduled meeting datetime
            hours_until: Hours until the meeting
            duration_minutes: Meeting duration in minutes

        Returns:
            bool: True if email was sent successfully
        """
        formatted_time = meeting_time.strftime("%B %d, %Y at %I:%M %p UTC")
        time_text = f"{hours_until} hour" if hours_until == 1 else f"{hours_until} hours"
        subject = f"Reminder: Coaching session in {time_text} - {settings.APP_NAME}"

        urgency_text = "Your session is coming up soon!" if hours_until <= 1 else "Your session is tomorrow!"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #F59E0B; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
        .meeting-box {{ background-color: white; border: 2px solid #F59E0B; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
        .countdown {{ font-size: 24px; font-weight: bold; color: #F59E0B; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Meeting Reminder</h1>
            <p class="countdown">{time_text} to go!</p>
        </div>
        <div class="content">
            <h2>Hey {user_name}!</h2>
            <p>{urgency_text}</p>
            <div class="meeting-box">
                <h3>Coaching Session Details</h3>
                <p><strong>Date & Time:</strong> {formatted_time}</p>
                <p><strong>Duration:</strong> {duration_minutes} minutes</p>
            </div>
            <p>Quick prep checklist:</p>
            <ul>
                <li>Have your goals document ready</li>
                <li>Think about your progress since last session</li>
                <li>Prepare any questions you have</li>
            </ul>
            <p style="text-align: center;">
                <a href="{self.frontend_url}" class="button">Join When Ready</a>
            </p>
            <p>Let's make progress!</p>
            <p>Your Coach,<br><strong>Tony (AI Coach)</strong></p>
        </div>
        <div class="footer">
            <p>{settings.APP_NAME} - AI-Powered Goal Achievement</p>
            <p>Questions? Contact us at {self.support_email}</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Meeting Reminder - {time_text} to go!

Hey {user_name}!

{urgency_text}

COACHING SESSION DETAILS
------------------------
Date & Time: {formatted_time}
Duration: {duration_minutes} minutes

Quick prep checklist:
- Have your goals document ready
- Think about your progress since last session
- Prepare any questions you have

Join when ready at: {self.frontend_url}

Let's make progress!

Your Coach,
Tony (AI Coach)

---
{settings.APP_NAME} - AI-Powered Goal Achievement
Questions? Contact us at {self.support_email}
"""

        return self._send_email(to_email, subject, html_content, text_content)

    def send_goal_milestone_email(
        self,
        to_email: str,
        user_name: str,
        goal_title: str,
        milestone: str,
    ) -> bool:
        """
        Send celebration email when user completes a goal milestone.

        Args:
            to_email: User's email address
            user_name: User's name
            goal_title: Title of the goal
            milestone: Description of the milestone achieved

        Returns:
            bool: True if email was sent successfully
        """
        subject = f"You did it! Milestone achieved - {settings.APP_NAME}"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #10B981; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
        .celebration {{ font-size: 48px; text-align: center; margin: 20px 0; }}
        .achievement-box {{ background-color: white; border: 2px solid #10B981; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Congratulations!</h1>
        </div>
        <div class="content">
            <div class="celebration">&#127881; &#127942; &#127881;</div>
            <h2>Amazing work, {user_name}!</h2>
            <p>You've just achieved a significant milestone. This is what progress looks like!</p>
            <div class="achievement-box">
                <h3>Milestone Achieved</h3>
                <p><strong>Goal:</strong> {goal_title}</p>
                <p><strong>Milestone:</strong> {milestone}</p>
            </div>
            <p>Remember what I always say: <em>"Success is doing what you said you would do, consistently, with passion and enthusiasm."</em></p>
            <p>You're living proof of that. Keep going - your next breakthrough is just around the corner!</p>
            <p style="text-align: center;">
                <a href="{self.frontend_url}" class="button">Continue Your Journey</a>
            </p>
            <p>Proud of you!</p>
            <p>Your Coach,<br><strong>Tony (AI Coach)</strong></p>
        </div>
        <div class="footer">
            <p>{settings.APP_NAME} - AI-Powered Goal Achievement</p>
            <p>Questions? Contact us at {self.support_email}</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Congratulations!

Amazing work, {user_name}!

You've just achieved a significant milestone. This is what progress looks like!

MILESTONE ACHIEVED
------------------
Goal: {goal_title}
Milestone: {milestone}

Remember what I always say: "Success is doing what you said you would do, consistently, with passion and enthusiasm."

You're living proof of that. Keep going - your next breakthrough is just around the corner!

Continue your journey at: {self.frontend_url}

Proud of you!

Your Coach,
Tony (AI Coach)

---
{settings.APP_NAME} - AI-Powered Goal Achievement
Questions? Contact us at {self.support_email}
"""

        return self._send_email(to_email, subject, html_content, text_content)

    def send_phase_transition_email(
        self,
        to_email: str,
        user_name: str,
        new_phase: str,
        next_meeting: Optional[datetime] = None,
    ) -> bool:
        """
        Send email when user transitions between phases.

        Args:
            to_email: User's email address
            user_name: User's name
            new_phase: The phase user is transitioning to
            next_meeting: Optional next meeting datetime

        Returns:
            bool: True if email was sent successfully
        """
        if new_phase == "tracking":
            subject = f"Goals Set! Time to Track Your Progress - {settings.APP_NAME}"
            next_meeting_text = ""
            if next_meeting:
                formatted_time = next_meeting.strftime("%B %d, %Y at %I:%M %p UTC")
                next_meeting_text = f"<p><strong>Your first check-in:</strong> {formatted_time}</p>"

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
        .phase-box {{ background-color: white; border: 2px solid #4F46E5; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Phase 2: Tracking Mode</h1>
        </div>
        <div class="content">
            <h2>Great work, {user_name}!</h2>
            <p>You've completed your goal setting phase and you're now in tracking mode!</p>
            <div class="phase-box">
                <h3>What's Different Now?</h3>
                <ul>
                    <li><strong>Scheduled Check-ins:</strong> We'll meet at regular intervals to review your progress</li>
                    <li><strong>Focus Time:</strong> Between meetings, focus on taking action toward your goals</li>
                    <li><strong>Accountability:</strong> Each meeting, we'll celebrate wins and address challenges</li>
                </ul>
                {next_meeting_text}
            </div>
            <p>You can still edit your goals anytime, but chat access is now reserved for our scheduled sessions. This helps you stay focused on execution!</p>
            <p style="text-align: center;">
                <a href="{self.frontend_url}" class="button">View Your Goals</a>
            </p>
            <p>Time to turn those goals into reality!</p>
            <p>Your Coach,<br><strong>Tony (AI Coach)</strong></p>
        </div>
        <div class="footer">
            <p>{settings.APP_NAME} - AI-Powered Goal Achievement</p>
            <p>Questions? Contact us at {self.support_email}</p>
        </div>
    </div>
</body>
</html>
"""
        else:
            subject = f"Back to Goal Setting - {settings.APP_NAME}"
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Goal Setting Mode</h1>
        </div>
        <div class="content">
            <h2>Welcome back, {user_name}!</h2>
            <p>You're back in goal setting mode. This means you have unlimited access to chat with your coach!</p>
            <p>Use this time to:</p>
            <ul>
                <li>Refine your existing goals</li>
                <li>Add new goals</li>
                <li>Get coaching on any challenges</li>
            </ul>
            <p style="text-align: center;">
                <a href="{self.frontend_url}" class="button">Start Chatting</a>
            </p>
            <p>Your Coach,<br><strong>Tony (AI Coach)</strong></p>
        </div>
        <div class="footer">
            <p>{settings.APP_NAME} - AI-Powered Goal Achievement</p>
            <p>Questions? Contact us at {self.support_email}</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Phase Transition

Hey {user_name}!

You've transitioned to {new_phase} phase.

Visit {self.frontend_url} to continue your journey.

Your Coach,
Tony (AI Coach)

---
{settings.APP_NAME} - AI-Powered Goal Achievement
Questions? Contact us at {self.support_email}
"""

        return self._send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get email service instance for dependency injection."""
    return email_service
