import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
import io

from reports.models import ScheduledReport, SavedReport
from reports.views import (
    _generate_report_data, _generate_pdf_report, 
    _generate_excel_report, _generate_csv_report
)
from core.models import AcademicYear, Department

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run scheduled reports that are due'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Force run all active scheduled reports regardless of next_run date',
        )

    def handle(self, *args, **options):
        force_all = options.get('force_all', False)
        now = timezone.now()
        
        # Get scheduled reports that are due
        if force_all:
            self.stdout.write(self.style.WARNING('Forcing run of all active scheduled reports'))
            scheduled_reports = ScheduledReport.objects.filter(is_active=True)
        else:
            scheduled_reports = ScheduledReport.objects.filter(
                is_active=True,
                next_run__lte=now
            )
        
        self.stdout.write(f'Found {scheduled_reports.count()} scheduled reports to run')
        
        for report in scheduled_reports:
            try:
                self.stdout.write(f'Running scheduled report: {report.title}')
                
                # Generate the report
                saved_report = self._generate_report(report)
                
                # Update next run date
                self._update_next_run_date(report)
                
                # Send email notifications
                if saved_report:
                    self._send_email_notifications(report, saved_report)
                    self.stdout.write(self.style.SUCCESS(f'Successfully ran report: {report.title}'))
                else:
                    self.stdout.write(self.style.ERROR(f'Failed to generate report: {report.title}'))
            
            except Exception as e:
                logger.error(f'Error running scheduled report {report.id}: {str(e)}')
                self.stdout.write(self.style.ERROR(f'Error running report {report.title}: {str(e)}'))
    
    def _generate_report(self, scheduled_report):
        """Generate a report based on a scheduled report configuration"""
        try:
            # Get parameters from the scheduled report
            params = scheduled_report.parameters
            
            # Get academic year and department
            try:
                academic_year = AcademicYear.objects.get(id=params.get('academic_year'))
            except AcademicYear.DoesNotExist:
                # If specified academic year doesn't exist, use the active one
                academic_year = AcademicYear.get_active()
                
            department = None
            if params.get('department'):
                try:
                    department = Department.objects.get(id=params.get('department'))
                except Department.DoesNotExist:
                    pass
            
            # Parse dates if present
            start_date = None
            end_date = None
            if params.get('start_date'):
                start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d').date()
            if params.get('end_date'):
                end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d').date()
            
            # Generate report data
            report_data = _generate_report_data(
                scheduled_report.template.report_type,
                academic_year,
                department,
                start_date,
                end_date,
                params.get('include_details', True)
            )
            
            # Save the report
            saved_report = SavedReport(
                title=f"{scheduled_report.title} (Scheduled Run)",
                description=f"Automatically generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                template=scheduled_report.template,
                report_data=report_data,
                parameters=params,
                academic_year=academic_year,
                department=department,
                created_by=scheduled_report.created_by
            )
            
            # Generate the file based on format
            format_type = params.get('format', 'pdf')
            buffer = io.BytesIO()
            
            if format_type == 'csv':
                response = _generate_csv_report(saved_report)
                buffer.write(response.content)
                file_name = f"{saved_report.title}.csv"
                content_type = 'text/csv'
            elif format_type == 'excel':
                response = _generate_excel_report(saved_report)
                buffer.write(response.content)
                file_name = f"{saved_report.title}.xlsx"
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:  # Default to PDF
                response = _generate_pdf_report(saved_report)
                buffer.write(response.content)
                file_name = f"{saved_report.title}.pdf"
                content_type = 'application/pdf'
            
            # Save the file to the report
            saved_report.file.save(file_name, buffer, save=False)
            saved_report.save()
            
            return saved_report
        
        except Exception as e:
            logger.error(f'Error generating report: {str(e)}')
            return None
    
    def _update_next_run_date(self, report):
        """Update the next run date based on frequency"""
        now = timezone.now()
        
        if report.frequency == 'daily':
            next_run = now + timedelta(days=1)
        elif report.frequency == 'weekly':
            next_run = now + timedelta(weeks=1)
        elif report.frequency == 'monthly':
            # Add approximately one month (30 days)
            next_run = now + timedelta(days=30)
        elif report.frequency == 'quarterly':
            # Add approximately three months (90 days)
            next_run = now + timedelta(days=90)
        else:
            # Default to weekly if frequency is unknown
            next_run = now + timedelta(weeks=1)
        
        # Update the report
        report.next_run = next_run
        report.save()
    
    def _send_email_notifications(self, scheduled_report, saved_report):
        """Send email notifications to recipients"""
        recipients = scheduled_report.recipients.all()
        
        if not recipients:
            logger.info(f'No recipients for report {scheduled_report.id}')
            return
        
        try:
            # Prepare email
            subject = f'Scheduled Report: {saved_report.title}'
            
            # Create email context
            context = {
                'report': saved_report,
                'scheduled_report': scheduled_report,
                'generated_date': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else '/',
            }
            
            # Render email body
            email_body = render_to_string('reports/email/scheduled_report.html', context)
            
            # Create email message
            email = EmailMessage(
                subject=subject,
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient.email for recipient in recipients],
            )
            email.content_subtype = 'html'
            
            # Attach the report file
            if saved_report.file:
                email.attach_file(saved_report.file.path)
            
            # Send email
            email.send()
            
            logger.info(f'Sent report {saved_report.id} to {len(recipients)} recipients')
        
        except Exception as e:
            logger.error(f'Error sending email notifications: {str(e)}')
