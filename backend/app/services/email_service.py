from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.observability.logging import get_logger

logger = get_logger("aara.email")


class EmailService:
    """Sends transactional email via SMTP.

    When SMTP_HOST is not configured (e.g. local development), emails are
    logged instead of sent so the reset/registration flow remains testable
    without a real mail provider.
    """

    def __init__(
        self,
        smtp_host: str | None,
        smtp_port: int,
        smtp_username: str | None,
        smtp_password: str | None,
        smtp_from: str,
        smtp_use_tls: bool = True,
    ) -> None:
        self._host = smtp_host
        self._port = smtp_port
        self._username = smtp_username
        self._password = smtp_password
        self._from = smtp_from
        self._use_tls = smtp_use_tls

    @property
    def is_configured(self) -> bool:
        return bool(self._host)

    def send(self, to_email: str, subject: str, html_body: str, text_body: str) -> None:
        if not self.is_configured:
            logger.warning(
                "smtp_not_configured_email_not_sent",
                to=to_email,
                subject=subject,
                body=text_body,
            )
            return

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._from
        message["To"] = to_email
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self._host, self._port, timeout=10) as server:
            if self._use_tls:
                server.starttls()
            if self._username and self._password:
                server.login(self._username, self._password)
            server.sendmail(self._from, [to_email], message.as_string())
        logger.info("email_sent", to=to_email, subject=subject)

    def send_password_reset_email(self, to_email: str, reset_link: str) -> None:
        subject = "Reset your AARA password"
        text_body = (
            "We received a request to reset your AARA password.\n\n"
            f"Reset your password here: {reset_link}\n\n"
            "This link expires soon and can only be used once. "
            "If you did not request this, you can safely ignore this email."
        )
        html_body = f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
          <h2>Reset your AARA password</h2>
          <p>We received a request to reset your password. Click the button below to choose a new one.</p>
          <p>
            <a href="{reset_link}"
               style="display:inline-block;padding:10px 20px;background:#6c5ce7;color:#fff;
                      text-decoration:none;border-radius:6px;">
              Reset Password
            </a>
          </p>
          <p>Or copy this link into your browser:<br>{reset_link}</p>
          <p style="color:#888;font-size:13px;">
            This link expires soon and can only be used once.
            If you did not request this, you can safely ignore this email.
          </p>
        </div>
        """
        self.send(to_email, subject, html_body, text_body)
