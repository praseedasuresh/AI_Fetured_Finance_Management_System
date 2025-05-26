from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    created and modified fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AcademicYear(models.Model):
    """Model for academic years"""
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-start_date']
        
    @classmethod
    def get_active(cls):
        """Get the currently active academic year"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # If multiple active years exist, return the most recent one
            return cls.objects.filter(is_active=True).order_by('-start_date').first()


class Department(models.Model):
    """Model for university departments"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    head = models.CharField(max_length=100, blank=True, default='', help_text="Name of department head")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Course(models.Model):
    """Model for courses offered by the university"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    description = models.TextField(blank=True, null=True)
    credits = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        ordering = ['code']
