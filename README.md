# Finance Management System

A comprehensive financial management system for educational institutions, designed to handle fees, budgets, expenses, and reporting.

## Features

- **User Management**: Role-based access control with different permissions for administrators, finance staff, faculty, and students
- **Fee Management**: Fee categories, structures, student fee assignment, and payment processing
- **Budget Management**: Budget allocation, approval workflow, and transfers between departments
- **Expense Management**: Expense tracking, approval workflow, and recurring expenses
- **Reports**: Comprehensive reporting with scheduled report generation

## System Requirements

- Python 3.8+
- Django 4.0+
- Other dependencies as listed in requirements.txt

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Finance-Management-System
```

### 2. Create a Virtual Environment (Optional but Recommended)

```bash
python -m venv venv
```

#### Activate the virtual environment:

- **Windows**:
  ```bash
  venv\Scripts\activate
  ```
- **Linux/Mac**:
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up the Database

Run the database setup script to create all necessary tables and initial data:

```bash
python setup_database.py
```

This script will:
- Run all migrations
- Create a superuser account
- Set up initial data (departments, academic years)

### 5. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000/

### 6. Login Information

After running the setup script, you can log in with the following credentials:

- **Email**: admin@example.com
- **Password**: admin123

## Module Overview

### Core Module
- Academic years, departments, and courses
- Base models and shared functionality

### Users Module
- Custom user model with roles (admin, finance staff, faculty, student)
- Student profiles and authentication

### Fees Module
- Fee categories and structures
- Student fee assignment and payment processing
- Fee discounts and waivers

### Budget Module
- Budget categories and allocation
- Budget approval workflow
- Budget transfers between departments

### Expenses Module
- Expense tracking and categorization
- Expense approval workflow
- Recurring expenses
- Expense attachments

### Reports Module
- Report templates
- Saved reports
- Scheduled reports with email notifications

## Project Structure

```
Finance-Management-System/
├── core/                  # Core functionality
├── users/                 # User management
├── fees/                  # Fee management
├── budget/                # Budget management
├── expenses/              # Expense management
├── reports/               # Reporting system
├── templates/             # HTML templates
├── static/                # Static files (CSS, JS, images)
├── media/                 # User-uploaded files
├── finance_system/        # Project settings
├── manage.py              # Django management script
├── setup_database.py      # Database setup script
└── requirements.txt       # Project dependencies
```

## Troubleshooting

### Database Issues

If you encounter database errors like "no such table", run the setup script:

```bash
python setup_database.py
```

### Static Files Not Loading

Make sure you have collected static files:

```bash
python manage.py collectstatic
```

## License

[MIT License](LICENSE)
