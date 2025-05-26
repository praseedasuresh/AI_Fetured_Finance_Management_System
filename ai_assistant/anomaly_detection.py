import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from django.utils import timezone
from django.db.models import Avg, StdDev, Count, Q, F
import datetime
import logging

from expenses.models import Expense, ExpenseCategory
from core.models import Department
from .models import ExpenseAnomaly

logger = logging.getLogger(__name__)

def detect_expense_anomalies(days_lookback=90, min_confidence=0.7):
    """
    Detect anomalies in expenses using multiple detection methods
    
    Args:
        days_lookback (int): Number of days to look back for historical data
        min_confidence (float): Minimum confidence score (0-1) to flag an anomaly
        
    Returns:
        int: Number of new anomalies detected
    """
    try:
        # Get date range for analysis
        end_date = timezone.now().date()
        start_date = end_date - datetime.timedelta(days=days_lookback)
        
        # Get expenses for analysis
        expenses = Expense.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('department', 'category')
        
        if not expenses.exists():
            logger.info("No expenses found in the specified date range")
            return 0
        
        # Convert to DataFrame for easier analysis
        expense_data = []
        for expense in expenses:
            expense_data.append({
                'id': expense.id,
                'amount': float(expense.amount),
                'date': expense.date,
                'department_id': expense.department_id if expense.department else None,
                'category_id': expense.category_id if expense.category else None,
                'title': expense.title,
                'description': expense.description
            })
        
        df = pd.DataFrame(expense_data)
        
        # Run different anomaly detection methods
        amount_anomalies = detect_amount_anomalies(df, expenses)
        frequency_anomalies = detect_frequency_anomalies(df, expenses)
        category_anomalies = detect_category_anomalies(df, expenses)
        department_anomalies = detect_department_anomalies(df, expenses)
        
        # Combine all anomalies and filter by confidence score
        all_anomalies = amount_anomalies + frequency_anomalies + category_anomalies + department_anomalies
        filtered_anomalies = [a for a in all_anomalies if a['confidence_score'] >= min_confidence]
        
        # Save anomalies to database
        new_anomalies = 0
        for anomaly in filtered_anomalies:
            expense = Expense.objects.get(id=anomaly['expense_id'])
            
            # Check if this anomaly already exists
            existing = ExpenseAnomaly.objects.filter(
                expense=expense,
                anomaly_type=anomaly['anomaly_type']
            ).exists()
            
            if not existing:
                ExpenseAnomaly.objects.create(
                    expense=expense,
                    anomaly_type=anomaly['anomaly_type'],
                    confidence_score=anomaly['confidence_score'],
                    description=anomaly['description']
                )
                new_anomalies += 1
        
        return new_anomalies
        
    except Exception as e:
        logger.error(f"Error in detect_expense_anomalies: {str(e)}")
        return 0


def detect_amount_anomalies(df, expenses):
    """Detect anomalies in expense amounts using Isolation Forest"""
    anomalies = []
    
    try:
        if len(df) < 10:  # Need enough data for meaningful analysis
            return anomalies
            
        # Prepare data for Isolation Forest
        X = df[['amount']].copy()
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train Isolation Forest model
        model = IsolationForest(contamination=0.05, random_state=42)
        model.fit(X_scaled)
        
        # Predict anomalies
        df['anomaly_score'] = model.decision_function(X_scaled)
        df['is_anomaly'] = model.predict(X_scaled) == -1
        
        # Get department and category averages for context
        dept_avgs = {}
        for dept in Department.objects.all():
            avg = Expense.objects.filter(department=dept).aggregate(avg=Avg('amount'))['avg']
            if avg:
                dept_avgs[dept.id] = float(avg)
        
        cat_avgs = {}
        for cat in ExpenseCategory.objects.all():
            avg = Expense.objects.filter(category=cat).aggregate(avg=Avg('amount'))['avg']
            if avg:
                cat_avgs[cat.id] = float(avg)
        
        # Process detected anomalies
        for _, row in df[df['is_anomaly']].iterrows():
            expense_id = row['id']
            amount = row['amount']
            
            # Calculate confidence score (0-1) based on anomaly score
            # Convert anomaly score to confidence (anomaly score is negative, lower is more anomalous)
            confidence = min(1.0, max(0.0, 0.5 - row['anomaly_score'] / 2))
            
            # Get context for description
            dept_id = row['department_id']
            cat_id = row['category_id']
            
            dept_context = ""
            if dept_id in dept_avgs:
                dept_avg = dept_avgs[dept_id]
                pct_diff = (amount - dept_avg) / dept_avg * 100 if dept_avg > 0 else 0
                dept_context = f"Department average: ${dept_avg:.2f} (this expense is {abs(pct_diff):.1f}% {'higher' if pct_diff > 0 else 'lower'})"
            
            cat_context = ""
            if cat_id in cat_avgs:
                cat_avg = cat_avgs[cat_id]
                pct_diff = (amount - cat_avg) / cat_avg * 100 if cat_avg > 0 else 0
                cat_context = f"Category average: ${cat_avg:.2f} (this expense is {abs(pct_diff):.1f}% {'higher' if pct_diff > 0 else 'lower'})"
            
            description = f"This expense amount (${amount:.2f}) appears unusual based on historical patterns. {dept_context} {cat_context}"
            
            anomalies.append({
                'expense_id': expense_id,
                'anomaly_type': 'amount',
                'confidence_score': confidence,
                'description': description
            })
    
    except Exception as e:
        logger.error(f"Error in detect_amount_anomalies: {str(e)}")
    
    return anomalies


def detect_frequency_anomalies(df, expenses):
    """Detect anomalies in expense frequency patterns"""
    anomalies = []
    
    try:
        # Group expenses by day to analyze frequency
        df['date_only'] = pd.to_datetime(df['date']).dt.date
        daily_counts = df.groupby('date_only').size().reset_index(name='count')
        
        if len(daily_counts) < 7:  # Need at least a week of data
            return anomalies
        
        # Calculate statistics
        mean_daily = daily_counts['count'].mean()
        std_daily = daily_counts['count'].std()
        threshold = mean_daily + 2 * std_daily  # 2 standard deviations above mean
        
        # Find days with unusually high frequency
        high_frequency_days = daily_counts[daily_counts['count'] > threshold]['date_only'].tolist()
        
        if not high_frequency_days:
            return anomalies
            
        # Find expenses on high frequency days
        for day in high_frequency_days:
            day_expenses = df[df['date_only'] == day]
            
            # Calculate confidence based on how many std devs above mean
            day_count = day_expenses.shape[0]
            z_score = (day_count - mean_daily) / std_daily if std_daily > 0 else 0
            confidence = min(1.0, max(0.5, z_score / 4))  # Scale z-score to confidence
            
            for _, row in day_expenses.iterrows():
                description = f"This expense occurred on {day} when {day_count} expenses were recorded, which is unusually high compared to the average of {mean_daily:.1f} expenses per day."
                
                anomalies.append({
                    'expense_id': row['id'],
                    'anomaly_type': 'frequency',
                    'confidence_score': confidence,
                    'description': description
                })
    
    except Exception as e:
        logger.error(f"Error in detect_frequency_anomalies: {str(e)}")
    
    return anomalies


def detect_category_anomalies(df, expenses):
    """Detect expenses with unusual categories for the department"""
    anomalies = []
    
    try:
        # Need department and category for this analysis
        df_valid = df.dropna(subset=['department_id', 'category_id'])
        
        if len(df_valid) < 10:  # Need enough data
            return anomalies
            
        # Get common category-department combinations
        dept_cat_counts = df_valid.groupby(['department_id', 'category_id']).size().reset_index(name='count')
        dept_totals = df_valid.groupby('department_id').size().reset_index(name='total')
        
        # Merge to get percentages
        dept_cat_counts = pd.merge(dept_cat_counts, dept_totals, on='department_id')
        dept_cat_counts['percentage'] = dept_cat_counts['count'] / dept_cat_counts['total']
        
        # Find uncommon category-department combinations (less than 5% of department expenses)
        uncommon = dept_cat_counts[dept_cat_counts['percentage'] < 0.05]
        
        for _, row in df_valid.iterrows():
            dept_id = row['department_id']
            cat_id = row['category_id']
            
            # Check if this combination is uncommon
            match = uncommon[(uncommon['department_id'] == dept_id) & (uncommon['category_id'] == cat_id)]
            
            if not match.empty:
                percentage = match.iloc[0]['percentage']
                confidence = min(1.0, max(0.5, (0.05 - percentage) * 10))  # Scale to confidence
                
                # Get department and category names for description
                try:
                    department = Department.objects.get(id=dept_id)
                    category = ExpenseCategory.objects.get(id=cat_id)
                    
                    description = f"This expense uses category '{category.name}' which is unusual for the '{department.name}' department (only {percentage*100:.1f}% of this department's expenses use this category)."
                    
                    anomalies.append({
                        'expense_id': row['id'],
                        'anomaly_type': 'category',
                        'confidence_score': confidence,
                        'description': description
                    })
                except:
                    pass  # Skip if we can't get department or category
    
    except Exception as e:
        logger.error(f"Error in detect_category_anomalies: {str(e)}")
    
    return anomalies


def detect_department_anomalies(df, expenses):
    """Detect departments with unusual spending patterns"""
    anomalies = []
    
    try:
        # Need department for this analysis
        df_valid = df.dropna(subset=['department_id'])
        
        if len(df_valid) < 10:  # Need enough data
            return anomalies
            
        # Group by department and calculate statistics
        dept_stats = df_valid.groupby('department_id')['amount'].agg(['mean', 'std', 'count']).reset_index()
        
        for _, row in df_valid.iterrows():
            dept_id = row['department_id']
            amount = row['amount']
            
            # Get stats for this department
            dept_row = dept_stats[dept_stats['department_id'] == dept_id]
            if dept_row.empty or dept_row.iloc[0]['count'] < 5:  # Need enough data for this department
                continue
                
            dept_mean = dept_row.iloc[0]['mean']
            dept_std = dept_row.iloc[0]['std']
            
            if pd.isna(dept_std) or dept_std == 0:
                continue
                
            # Calculate z-score
            z_score = abs(amount - dept_mean) / dept_std
            
            # Flag if more than 2.5 standard deviations from mean
            if z_score > 2.5:
                confidence = min(1.0, max(0.5, z_score / 5))  # Scale z-score to confidence
                
                try:
                    department = Department.objects.get(id=dept_id)
                    
                    description = f"This expense amount (${amount:.2f}) is {z_score:.1f} standard deviations from the mean expense amount (${dept_mean:.2f}) for the '{department.name}' department."
                    
                    anomalies.append({
                        'expense_id': row['id'],
                        'anomaly_type': 'department',
                        'confidence_score': confidence,
                        'description': description
                    })
                except:
                    pass  # Skip if we can't get department
    
    except Exception as e:
        logger.error(f"Error in detect_department_anomalies: {str(e)}")
    
    return anomalies
