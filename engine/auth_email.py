"""
engine/auth_email.py
─────────────────────
Sends verification and password reset emails.
Reuses the same SMTP_* env vars already used by generator.py admin alerts.
"""

import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

APP_BASE_URL      = os.getenv("APP_BASE_URL",  "http://localhost:8000")
FRONTEND_BASE_URL = os.getenv("FRONTEND_URL",  "http://localhost:3000")


def send_verification_email(to_email: str, token: str) -> None:
    """
    Fire-and-forget — call from a background task so it never blocks the response.
    Raises on SMTP failure (caller should log + ignore, not crash the request).
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([smtp_user, smtp_pass]):
        print("[WARN] auth_email: SMTP_USER / SMTP_PASS not set — skipping verification email")
        return

    verify_url = f"{APP_BASE_URL}/auth/verify-email?token={token}"

    text_body = (
        f"Welcome to GlamAI!\n\n"
        f"Please verify your email by clicking the link below:\n\n"
        f"{verify_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you didn't create an account, you can ignore this email."
    )

    html_body = f"""
    <html><body style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px">
      <h2 style="color:#1a1a2e">Welcome to GlamAI ✨</h2>
      <p>Please verify your email address to activate your account.</p>
      <a href="{verify_url}"
         style="display:inline-block;margin:16px 0;padding:12px 24px;
                background:#c96b8a;color:#fff;border-radius:8px;
                text-decoration:none;font-weight:bold">
        Verify Email
      </a>
      <p style="color:#888;font-size:13px">
        This link expires in 24 hours.<br>
        If you didn't create an account, you can ignore this email.
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your GlamAI account"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())

    print(f"[INFO] Verification email sent to {to_email}")


def send_password_reset_email(to_email: str, token: str) -> None:
    """
    Sends a password reset link to the user.
    Fire-and-forget — call from a background task.
    Link points to the frontend reset page, not the API.
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([smtp_user, smtp_pass]):
        print("[WARN] auth_email: SMTP_USER / SMTP_PASS not set — skipping password reset email")
        return

    reset_url = f"{FRONTEND_BASE_URL}/auth/reset-password?token={token}&email={to_email}"

    text_body = (
        f"Hi,\n\n"
        f"We received a request to reset the password for your GlamAI account.\n\n"
        f"Click the link below to set a new password:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in 1 hour.\n\n"
        f"If you didn't request this, you can safely ignore this email — "
        f"your password won't change.\n\n"
        f"— The GlamAI Team"
    )

    html_body = f"""
    <html><body style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px">
      <h2 style="color:#1a1a2e">Reset your password 🔑</h2>
      <p>We received a request to reset the password for your GlamAI account.</p>
      <a href="{reset_url}"
         style="display:inline-block;margin:16px 0;padding:12px 24px;
                background:#c96b8a;color:#fff;border-radius:8px;
                text-decoration:none;font-weight:bold">
        Set New Password
      </a>
      <p style="color:#888;font-size:13px">
        This link expires in <strong>1 hour</strong>.<br>
        If you didn't request a password reset, you can safely ignore this email.
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your GlamAI password"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())

    print(f"[INFO] Password reset email sent to {to_email}")