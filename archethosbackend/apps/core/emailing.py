from html import escape
import logging

from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend

from .models import Company, Enquiry


logger = logging.getLogger(__name__)


def _service_label(service):
    if isinstance(service, dict):
        return str(service.get("label") or service.get("title") or service.get("name") or "").strip()
    return str(service or "").strip()


def _smtp_connection(company):
    if not company.smtp_host or not company.smtp_from_email:
        return None
    if company.smtp_use_tls and company.smtp_use_ssl:
        logger.warning("Enquiry email skipped: Company SMTP TLS and SSL are both enabled.")
        return None
    return EmailBackend(
        host=company.smtp_host,
        port=company.smtp_port,
        username=company.smtp_username,
        password=company.smtp_password,
        use_tls=company.smtp_use_tls,
        use_ssl=company.smtp_use_ssl,
        fail_silently=False,
    )


def _service_rows(labels):
    if not labels:
        labels = ["No specific services selected"]
    return "".join(
        f"""
        <tr>
          <td style=\"width:52px;padding:16px 0;border-top:1px solid #d8d2c8;color:#d39a35;font:12px/1.2 Arial,sans-serif;letter-spacing:2px;\">{index:02d}</td>
          <td style=\"padding:16px 0;border-top:1px solid #d8d2c8;color:#17303c;font:16px/1.4 Arial,sans-serif;\">{escape(label)}</td>
          <td style=\"width:32px;padding:16px 0;border-top:1px solid #d8d2c8;color:#17303c;text-align:right;font:22px/1 Arial,sans-serif;\">→</td>
        </tr>
        """
        for index, label in enumerate(labels, start=1)
    )


def _email_content(enquiry, company):
    company_name = company.name or "Archethos"
    services = [
        label
        for label in (_service_label(item) for item in (enquiry.services or []))
        if label
    ]
    service_text = "\n".join(f"{index:02d}  {label}" for index, label in enumerate(services or ["No specific services selected"], start=1))
    location = enquiry.location or "Not provided"
    project_type = enquiry.project_type or "Not provided"

    text = f"""We've received a new enquiry for {company_name}.

Name: {enquiry.name}
Email: {enquiry.email}
Phone: {enquiry.phone or 'Not provided'}
Project type: {project_type}
Location: {location}

Message:
{enquiry.message}

Services requested:
{service_text}
"""

    html = f"""
    <!doctype html>
    <html>
      <body style=\"margin:0;background:#f5f2ec;color:#17303c;\">
        <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#f5f2ec;\">
          <tr><td style=\"padding:40px 24px;\">
            <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:720px;margin:0 auto;background:#f5f2ec;\">
              <tr><td style=\"border-top:1px solid #d8d2c8;padding:34px 0 38px;\">
                <p style=\"margin:0 0 18px;color:#b87919;font:12px/1.2 Arial,sans-serif;letter-spacing:3px;text-transform:uppercase;\">New enquiry</p>
                <h1 style=\"margin:0;color:#17303c;font:700 36px/1.1 Arial,sans-serif;\">We've received your enquiry.</h1>
                <p style=\"margin:20px 0 0;color:#526570;font:16px/1.6 Arial,sans-serif;\">A new project conversation has arrived for {escape(company_name)}. Reply directly to this email to contact {escape(enquiry.name)}.</p>
              </td></tr>
              <tr><td style=\"border-top:1px solid #d8d2c8;padding:24px 0 30px;\">
                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\">
                  <tr><td style=\"padding:0 0 12px;color:#b87919;font:12px/1.2 Arial,sans-serif;letter-spacing:3px;text-transform:uppercase;\">Enquiry details</td></tr>
                  <tr><td style=\"padding:5px 0;color:#17303c;font:16px/1.5 Arial,sans-serif;\"><strong>Name</strong>&nbsp;&nbsp;{escape(enquiry.name)}</td></tr>
                  <tr><td style=\"padding:5px 0;color:#17303c;font:16px/1.5 Arial,sans-serif;\"><strong>Email</strong>&nbsp;&nbsp;{escape(enquiry.email)}</td></tr>
                  <tr><td style=\"padding:5px 0;color:#17303c;font:16px/1.5 Arial,sans-serif;\"><strong>Phone</strong>&nbsp;&nbsp;{escape(enquiry.phone or 'Not provided')}</td></tr>
                  <tr><td style=\"padding:5px 0;color:#17303c;font:16px/1.5 Arial,sans-serif;\"><strong>Project</strong>&nbsp;&nbsp;{escape(project_type)}</td></tr>
                  <tr><td style=\"padding:5px 0;color:#17303c;font:16px/1.5 Arial,sans-serif;\"><strong>Location</strong>&nbsp;&nbsp;{escape(location)}</td></tr>
                  <tr><td style=\"padding:18px 0 0;color:#526570;font:16px/1.6 Arial,sans-serif;\">{escape(enquiry.message).replace(chr(10), '<br>')}</td></tr>
                </table>
              </td></tr>
              <tr><td style=\"border-top:1px solid #d8d2c8;padding:28px 0 0;\">
                <p style=\"margin:0 0 8px;color:#b87919;font:12px/1.2 Arial,sans-serif;letter-spacing:3px;text-transform:uppercase;\">Services</p>
                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\">{_service_rows(services)}</table>
              </td></tr>
              <tr><td style=\"padding:34px 0 0;color:#81909a;font:12px/1.5 Arial,sans-serif;\">{escape(company_name)}</td></tr>
            </table>
          </td></tr>
        </table>
      </body>
    </html>
    """
    return text, html


def send_enquiry_notification(enquiry: Enquiry, company: Company) -> bool:
    if not company.send_email_copy:
        return False

    connection = _smtp_connection(company)
    if connection is None:
        logger.warning("Enquiry email skipped: SMTP is not configured for Company %s.", company.pk)
        return False

    text, html = _email_content(enquiry, company)
    message = EmailMultiAlternatives(
        subject=f"New enquiry from {enquiry.name}",
        body=text,
        from_email=company.smtp_from_email,
        to=[company.send_email_copy],
        reply_to=[enquiry.email],
        connection=connection,
    )
    message.attach_alternative(html, "text/html")
    try:
        message.send()
    except Exception:
        logger.exception("Could not send enquiry notification for enquiry %s.", enquiry.pk)
        return False
    return True
