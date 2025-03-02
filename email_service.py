import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def send_email(recipient, subject, html_content, text_content=None):
    """
    Sends an email using the SMTP configuration from app config.
    
    Args:
        recipient (str): Email address of the recipient
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text content of the email. If not provided, a simplified version of the HTML will be used.
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not text_content:
        # Create a simple text version from HTML if not provided
        text_content = html_content.replace('<br>', '\n').replace('</p>', '\n').replace('<li>', '- ')
        # Remove all HTML tags
        import re
        text_content = re.sub('<[^<]+?>', '', text_content)
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = recipient
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as smtp:
            if current_app.config['MAIL_USE_TLS']:
                smtp.starttls()
            
            if current_app.config['MAIL_USERNAME'] and current_app.config['MAIL_PASSWORD']:
                smtp.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            
            smtp.send_message(msg)
        
        logger.info(f"Email sent to {recipient}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        return False


def send_welcome_email(user_email, username):
    """Send welcome email to new users"""
    subject = "Welcome to YouTube Shorts Generator!"
    
    html_content = f"""
    <html>
    <body>
        <h1>Welcome to YouTube Shorts Generator!</h1>
        <p>Hello {username},</p>
        <p>Thank you for signing up for our service. We're excited to help you create engaging YouTube Shorts content.</p>
        <p>Here's what you can do with your account:</p>
        <ul>
            <li>Generate folk stories from different countries</li>
            <li>Create voiceover scripts and audio</li>
            <li>Get scene descriptions and image prompts</li>
            <li>Download and share your creations</li>
        </ul>
        <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
        <p>Happy creating!</p>
        <p>The YouTube Shorts Generator Team</p>
    </body>
    </html>
    """
    
    return send_email(user_email, subject, html_content)


def send_reset_password_email(user_email, reset_url):
    """Send password reset email"""
    subject = "Reset Your Password"
    
    html_content = f"""
    <html>
    <body>
        <h1>Reset Your Password</h1>
        <p>You requested a password reset for your YouTube Shorts Generator account.</p>
        <p>Please click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
        <p>The YouTube Shorts Generator Team</p>
    </body>
    </html>
    """
    
    return send_email(user_email, subject, html_content)


def send_subscription_confirmation(user_email, username, plan_name):
    """Send subscription confirmation email"""
    subject = f"Your {plan_name.capitalize()} Subscription is Active"
    
    html_content = f"""
    <html>
    <body>
        <h1>Subscription Confirmed</h1>
        <p>Hello {username},</p>
        <p>Thank you for subscribing to our {plan_name.capitalize()} plan!</p>
        <p>Your subscription is now active, and you can start enjoying all the benefits of your plan.</p>
        <p>Visit your dashboard to start creating more content and exploring all the features available to you.</p>
        <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
        <p>The YouTube Shorts Generator Team</p>
    </body>
    </html>
    """
    
    return send_email(user_email, subject, html_content)


def send_payment_failed_notification(user_email, username):
    """Send payment failed notification"""
    subject = "Payment Failed - Action Required"
    
    html_content = f"""
    <html>
    <body>
        <h1>Payment Failed</h1>
        <p>Hello {username},</p>
        <p>We were unable to process your recent subscription payment.</p>
        <p>To continue using our premium features, please update your payment information in your account settings.</p>
        <p>If you do not update your payment information, your subscription may be downgraded to the free plan.</p>
        <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
        <p>The YouTube Shorts Generator Team</p>
    </body>
    </html>
    """
    
    return send_email(user_email, subject, html_content)


def send_generation_completion_notification(user_email, username, country, generation_id):
    """Send notification when a generation is complete"""
    subject = f"Your {country} YouTube Short is Ready"
    
    html_content = f"""
    <html>
    <body>
        <h1>Your YouTube Short is Ready!</h1>
        <p>Hello {username},</p>
        <p>Good news! Your YouTube Short based on a folk story from {country} has been generated successfully.</p>
        <p>You can view and download your content from your dashboard.</p>
        <p>Generation ID: {generation_id}</p>
        <p>We hope you enjoy your creation!</p>
        <p>The YouTube Shorts Generator Team</p>
    </body>
    </html>
    """
    
    return send_email(user_email, subject, html_content)