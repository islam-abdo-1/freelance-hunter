"""
Email notification service for Freelance Hunter.
Supports SMTP with TLS for sending scan completion and job alert emails.
"""
import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from core.config.loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class EmailTemplate:
    """Email template with subject and body."""
    subject: str
    html_body: str
    text_body: str


class EmailService:
    """Handles sending email notifications."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or get_config().email_config
        self.enabled = self.config.get("enabled", False)
        self.smtp_host = self.config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.username = self.config.get("username", "")
        self.password = self.config.get("password", "")
        self.from_email = self.config.get("from_email", self.username)
        self.use_tls = self.config.get("use_tls", True)
        
        if not self.enabled:
            logger.warning("Email service is disabled in config")
    
    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection."""
        context = ssl.create_default_context()
        smtp = smtplib.SMTP(self.smtp_host, self.smtp_port)
        smtp.ehlo()
        if self.use_tls:
            smtp.starttls(context=context)
            smtp.ehlo()
        if self.username and self.password:
            smtp.login(self.username, self.password)
        return smtp
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send a single email."""
        if not self.enabled:
            logger.warning("Email service disabled, skipping send")
            return False
        
        if not self.username or not self.password:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            
            with self._create_smtp_connection() as smtp:
                smtp.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_email_async(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send email asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_email, to_email, subject, html_body, text_body)
    
    # ===== Templates =====
    
    def _scan_complete_template(self, stats: dict[str, Any], top_jobs: list[dict[str, Any]] | None = None) -> EmailTemplate:
        """Template for scan completion notification."""
        top_jobs = top_jobs or []
        
        jobs_html = ""
        for i, job in enumerate(top_jobs[:5], 1):
            jobs_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{i}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><a href="{job.get('job_url', '#')}" style="color: #2563eb; text-decoration: none;">{job.get('title', 'N/A')}</a></td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{job.get('platform', 'N/A')}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{job.get('budget', 'N/A')}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><span style="background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{job.get('match_level', 'N/A').replace('_', ' ')}</span></td>
            </tr>
            """
        
        jobs_text = "\n".join([
            f"{i}. {job.get('title', 'N/A')} | {job.get('platform', 'N/A')} | {job.get('budget', 'N/A')} | {job.get('match_level', 'N/A')}"
            for i, job in enumerate(top_jobs[:5], 1)
        ])
        
        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 12px 12px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; flex-wrap: wrap; gap: 10px; }}
                .stat {{ background: white; padding: 15px; border-radius: 8px; text-align: center; min-width: 80px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
                .stat-label {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #2563eb; color: white; padding: 12px; text-align: right; }}
                td {{ padding: 12px; text-align: right; }}
                .footer {{ text-align: center; margin-top: 30px; color: #64748b; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 Freelance Hunter</h1>
                <p>اكتمل المسح التلقائي - {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            <div class="content">
                <h2>📊 ملخص المسح</h2>
                <div class="stats">
                    <div class="stat"><div class="stat-value">{stats.get('verified_jobs', 0)}</div><div class="stat-label">محقق</div></div>
                    <div class="stat"><div class="stat-value">{stats.get('relevant_jobs', 0)}</div><div class="stat-label">ملائم</div></div>
                    <div class="stat"><div class="stat-value">{stats.get('high_match_jobs', 0)}</div><div class="stat-label">مطابقة عالية</div></div>
                    <div class="stat"><div class="stat-value">{stats.get('duplicates_removed', 0)}</div><div class="stat-label">مكرر</div></div>
                </div>
                
                <h2>🏆 أفضل الفرص</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>العنوان</th>
                            <th>المنصة</th>
                            <th>الميزانية</th>
                            <th>المطابقة</th>
                        </tr>
                    </thead>
                    <tbody>
                        {jobs_html or '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #94a3b8;">لا توجد فرص عالية المطابقة</td></tr>'}
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>Freelance Hunter - نظام اكتشاف الوظائف الذكي</p>
                    <p>يمكنك تعديل إعدادات الإشعارات من <a href="#" style="color: #2563eb;">لوحة التحكم</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        Freelance Hunter - اكتمل المسح التلقائي
        ==============================
        
        ملخص المسح ({datetime.now().strftime('%Y-%m-%d %H:%M')}):
        - تم التحقق من: {stats.get('verified_jobs', 0)} وظيفة
        - فرص ملائمة: {stats.get('relevant_jobs', 0)}
        - مطابقة عالية: {stats.get('high_match_jobs', 0)}
        - مكررات مزالة: {stats.get('duplicates_removed', 0)}
        
        أفضل الفرص:
        {jobs_text or 'لا توجد فرص عالية المطابقة'}
        
        ---
        Freelance Hunter - نظام اكتشاف الوظائف الذكي
        """
        
        return EmailTemplate(
            subject=f"🎯 Freelance Hunter - اكتمل المسح ({stats.get('high_match_jobs', 0)} فرص ممتازة)",
            html_body=html,
            text_body=text
        )
    
    def _high_match_alert_template(self, job: dict[str, Any]) -> EmailTemplate:
        """Template for high match job alert."""
        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .alert {{ background: linear-gradient(135deg, #fef3c7, #fde68a); border: 1px solid #f59e0b; border-radius: 12px; padding: 24px; }}
                .job-title {{ font-size: 20px; font-weight: bold; color: #1e40af; margin-bottom: 16px; }}
                .detail {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }}
                .label {{ color: #6b7280; }}
                .value {{ font-weight: 600; color: #111827; }}
                .btn {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="alert">
                <h2>⭐ فرصة ممتازة جديدة!</h2>
                <p class="job-title">{job.get('title', 'فرصة جديدة')}</p>
                
                <div class="detail"><span class="label">المنصة:</span><span class="value">{job.get('platform', 'N/A')}</span></div>
                <div class="detail"><span class="label">الميزانية:</span><span class="value">{job.get('budget', 'N/A')}</span></div>
                <div class="detail"><span class="label">درجة المطابقة:</span><span class="value">{job.get('match_score', 0):.1f}%</span></div>
                <div class="detail"><span class="label">العميل:</span><span class="value">{job.get('client_name', 'N/A')} ({job.get('client_country', 'N/A')})</span></div>
                <div class="detail"><span class="label">النشر:</span><span class="value">{job.get('time_since_posted', 'N/A')}</span></div>
                
                <a href="{job.get('job_url', '#')}" class="btn">عرض الوظيفة والتقديم</a>
                
                <p style="margin-top: 20px; font-size: 14px; color: #6b7280;">
                    سبب المطابقة: {job.get('match_reason', 'N/A')[:200]}...
                </p>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        ⭐ فرصة ممتازة جديدة!
        
        {job.get('title', 'فرصة جديدة')}
        المنصة: {job.get('platform', 'N/A')}
        الميزانية: {job.get('budget', 'N/A')}
        درجة المطابقة: {job.get('match_score', 0):.1f}%
        العميل: {job.get('client_name', 'N/A')}
        النشر: {job.get('time_since_posted', 'N/A')}
        
        الرابط: {job.get('job_url', '#')}
        
        سبب المطابقة: {job.get('match_reason', 'N/A')[:200]}...
        """
        
        return EmailTemplate(
            subject=f"⭐ Freelance Hunter - فرصة ممتازة: {job.get('title', 'جديدة')[:50]}",
            html_body=html,
            text_body=text
        )
    
    # ===== Public Methods =====
    
    async def send_scan_complete(self, stats: dict[str, Any], top_jobs: list[dict[str, Any]] | None = None, 
                                  email: str | None = None) -> bool:
        """Send scan completion notification."""
        email = email or get_config().email_notifications.get("email")
        if not email:
            logger.warning("No email configured for notifications")
            return False
        
        if not get_config().email_notifications.get("enabled"):
            return False
        
        if not get_config().email_notifications.get("on_scan_complete"):
            return False
        
        template = self._scan_complete_template(stats, top_jobs)
        return await self.send_email_async(email, template.subject, template.html_body, template.text_body)
    
    async def send_high_match_alert(self, job: dict[str, Any], email: str | None = None) -> bool:
        """Send high match job alert."""
        email = email or get_config().email_notifications.get("email")
        if not email:
            return False
        
        if not get_config().email_notifications.get("enabled"):
            return False
        
        if not get_config().email_notifications.get("on_high_match"):
            return False
        
        template = self._high_match_alert_template(job)
        return await self.send_email_async(email, template.subject, template.html_body, template.text_body)
    
    async def send_test_email(self, email: str | None = None) -> bool:
        """Send test email to verify configuration."""
        email = email or get_config().email_notifications.get("email")
        if not email:
            return False
        
        html = """
        <html dir="rtl"><body style="font-family: sans-serif; padding: 20px;">
        <h2 style="color: #2563eb;">✅ اختبار الإعدادات</h2>
        <p>تم إعداد الإشعارات بنجاح لـ Freelance Hunter</p>
        <p>ستصلك الإشعارات عند:</p>
        <ul>
            <li>اكتمال المسح التلقائي</li>
            <li>العثور على فرص مطابقة بدرجة عالية</li>
        </ul>
        <p style="color: #6b7280; font-size: 14px;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </body></html>
        """
        
        text = "اختبار الإعدادات - Freelance Hunter\nتم إعداد الإشعارات بنجاح."
        
        return await self.send_email_async(
            email, 
            "✅ Freelance Hunter - اختبار الإشعارات", 
            html, 
            text
        )


# Global instance
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service