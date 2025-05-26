from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, 
    PasswordResetView, PasswordResetConfirmView
)
from django.urls import reverse_lazy
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q

from .forms import (
    CustomAuthenticationForm, CustomUserCreationForm, CustomUserChangeForm,
    StudentProfileForm, CustomPasswordChangeForm, CustomPasswordResetForm,
    CustomSetPasswordForm
)
from .models import User, StudentProfile
from .decorators import admin_required, finance_staff_required


class CustomLoginView(LoginView):
    """Custom login view with styled form"""
    form_class = CustomAuthenticationForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    """Custom logout view"""
    next_page = 'login'


class CustomPasswordChangeView(PasswordChangeView):
    """Custom password change view with styled form"""
    form_class = CustomPasswordChangeForm
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('profile')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password was successfully updated!')
        return super().form_valid(form)


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view with styled form"""
    form_class = CustomPasswordResetForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Custom password reset confirm view with styled form"""
    form_class = CustomSetPasswordForm
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


@admin_required
def register_user(request):
    """View for registering new users (admin only)"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # The StudentProfile creation is now handled by the signal
            # No need to create it here
            
            messages.success(request, f'Account created for {user.email}')
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})


def register_admin(request):
    """View for registering new administrator accounts"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Force the role to be admin regardless of what was selected
            user = form.save(commit=False)
            user.role = 'admin'
            user.save()
            
            messages.success(request, f'Administrator account created for {user.email}. You can now login.')
            return redirect('login')
    else:
        # Pre-set the role field to admin
        form = CustomUserCreationForm(initial={'role': 'admin'})
    
    return render(request, 'users/register_admin.html', {'form': form})


@login_required
def profile(request):
    """View for user profile"""
    user = request.user
    
    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
        
        # Include student profile form if user is a student
        if user.is_student:
            try:
                student_profile = user.student_profile
            except StudentProfile.DoesNotExist:
                student_profile = StudentProfile(user=user)
            
            profile_form = StudentProfileForm(request.POST, instance=student_profile)
            
            if user_form.is_valid() and profile_form.is_valid():
                with transaction.atomic():
                    user_form.save()
                    profile_form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('profile')
        else:
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('profile')
    else:
        user_form = CustomUserChangeForm(instance=user)
        
        # Include student profile form if user is a student
        if user.is_student:
            try:
                profile_form = StudentProfileForm(instance=user.student_profile)
            except StudentProfile.DoesNotExist:
                profile_form = StudentProfileForm()
        else:
            profile_form = None
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    
    return render(request, 'users/profile.html', context)


@admin_required
def user_list(request):
    """View for listing all users (admin only)"""
    users = User.objects.all().order_by('role', 'first_name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    selected_role = request.GET.get('role', '')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if selected_role:
        users = users.filter(role=selected_role)
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_role': selected_role
    }
    
    return render(request, 'users/list.html', context)


@admin_required
def user_detail(request, pk):
    """View for user details (admin only)"""
    user = get_object_or_404(User, pk=pk)
    
    try:
        student_profile = user.student_profile if user.is_student else None
    except StudentProfile.DoesNotExist:
        student_profile = None
    
    context = {
        'user': user,
        'student_profile': student_profile,
    }
    
    return render(request, 'users/user_detail.html', context)


@admin_required
def edit_user(request, pk):
    """View for editing users (admin only)"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
        
        # Include student profile form if user is a student
        if user.is_student:
            try:
                student_profile = user.student_profile
            except StudentProfile.DoesNotExist:
                student_profile = StudentProfile(user=user)
            
            profile_form = StudentProfileForm(request.POST, instance=student_profile)
            
            if user_form.is_valid() and profile_form.is_valid():
                with transaction.atomic():
                    user_form.save()
                    profile_form.save()
                messages.success(request, f'Profile for {user.email} has been updated!')
                return redirect('user_detail', pk=user.pk)
        else:
            if user_form.is_valid():
                user_form.save()
                messages.success(request, f'Profile for {user.email} has been updated!')
                return redirect('user_detail', pk=user.pk)
    else:
        user_form = CustomUserChangeForm(instance=user)
        
        # Include student profile form if user is a student
        if user.is_student:
            try:
                profile_form = StudentProfileForm(instance=user.student_profile)
            except StudentProfile.DoesNotExist:
                profile_form = StudentProfileForm()
        else:
            profile_form = None
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user': user,
    }
    
    return render(request, 'users/edit_user.html', context)


@admin_required
def delete_user(request, pk):
    """View for deleting users (admin only)"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, f'User {user.email} has been deleted!')
        return redirect('user_list')
    
    return render(request, 'users/delete_user.html', {'user': user})
