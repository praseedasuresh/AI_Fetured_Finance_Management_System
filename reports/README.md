# Reports Module

The Reports module provides comprehensive financial reporting capabilities for the Finance Management System, including fee collection reports, budget allocation reports, expense tracking reports, and financial summary reports.

## Features

- **Report Templates**: Create and manage different types of report templates
- **Report Generation**: Generate reports with various parameters and formats (PDF, Excel, CSV)
- **Saved Reports**: Save generated reports for future reference
- **Scheduled Reports**: Schedule automatic report generation and distribution
- **Email Notifications**: Automatically send reports to specified recipients

## Scheduled Reports

The Reports module includes a management command to run scheduled reports automatically. This command can be set up to run periodically using a cron job or Windows Task Scheduler.

### Running the Command Manually

To run the scheduled reports command manually, use the following command:

```bash
python manage.py run_scheduled_reports
```

This will run all scheduled reports that are due (based on their next_run date).

To force run all active scheduled reports regardless of their next_run date:

```bash
python manage.py run_scheduled_reports --force-all
```

### Setting Up Automatic Scheduling

#### Linux/Unix (Cron Job)

To set up a cron job to run the scheduled reports command automatically, add the following to your crontab:

```bash
# Run scheduled reports every day at 1:00 AM
0 1 * * * cd /path/to/finance_system && /path/to/python manage.py run_scheduled_reports >> /path/to/logs/scheduled_reports.log 2>&1
```

To edit your crontab, run:

```bash
crontab -e
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create a new Basic Task
3. Name it "Finance System Scheduled Reports"
4. Set the trigger to run daily at 1:00 AM
5. Set the action to "Start a program"
6. Program/script: `C:\path\to\python.exe`
7. Add arguments: `C:\path\to\finance_system\manage.py run_scheduled_reports`
8. Start in: `C:\path\to\finance_system`

### Email Configuration

For email notifications to work properly, ensure that your Django settings include the following:

```python
# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'Finance System <your-email@example.com>'
```

Replace the values with your actual email server settings.

## Report Types

The system supports the following report types:

1. **Fee Reports**: Track fee collection status, outstanding balances, and payment trends
2. **Budget Reports**: Monitor budget allocations, utilization, and transfers
3. **Expense Reports**: Analyze expenses by category, department, and time period
4. **Financial Summary Reports**: Get a complete overview of the institution's financial health

## Customizing Reports

You can customize report templates by creating new templates with specific configurations. The template data is stored as JSON and can include:

- Fields to include in the report
- Sorting and filtering options
- Chart configurations
- Custom calculations

## Security

Reports are secured based on user roles and permissions:

- Admins can access all reports
- Finance staff can access reports related to their department
- Department heads can only access reports for their department
- Regular users cannot access reports unless specifically granted access
