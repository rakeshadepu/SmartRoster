"""
admin.py — Register models in Django Admin for easy management.
Useful during development for inspecting data and creating the first employee account.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from timetable_app.models import (
    Organisation, BusinessHours, WorkTypeLimit, User, Availability, Timetable, Shift
)


class BusinessHoursInline(admin.TabularInline):
    model  = BusinessHours
    extra  = 0
    fields = ['day_of_week', 'open_time', 'close_time']


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'created_at']
    search_fields = ['name']
    inlines       = [BusinessHoursInline]


@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display  = ['org', 'day_of_week', 'open_time', 'close_time']
    list_filter   = ['day_of_week', 'org']


@admin.register(WorkTypeLimit)
class WorkTypeLimitAdmin(admin.ModelAdmin):
    list_display  = ['org', 'work_type', 'hours_per_week']
    list_filter   = ['work_type', 'org']

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['full_name']
    list_display = [
        'user_id',
        'employee_code',
        'full_name',
        'email',
        'phone',
        'role',
        'work_type',
        'org',
    ]

    list_filter = [
        'role',
        'work_type',
        'org'
    ]

    search_fields = [
        'user_id',
        'employee_code',
        'full_name',
        'email',
        'phone'
    ]

    readonly_fields = [
        'user_id',
        'created_at',
        'updated_at',
        'plain_password'
    ]

    fieldsets = (
        ('Identity', {
            'fields': (
                'user_id',
                'employee_code',
                'first_name',
                'last_name',
                'full_name',
                'password'
            )
        }),

        ('Contact Details', {
            'fields': (
                'email',
                'phone',
                'nationality',
                'dob'
            )
        }),

        ('Bank Details', {
            'fields': (
                'iban',
                'bic'
            )
        }),

        ('Employment', {
            'fields': (
                'role',
                'work_type',
                'org'
            )
        }),

        ('Status', {
            'fields': (
                'is_staff',
                'is_superuser'
            )
        }),

        ('Debug', {
            'fields': ('plain_password',),
            'classes': ('collapse',)
        }),

        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display  = ['worker', 'week_start', 'week_number', 'day', 'start_time', 'submitted_at']
    list_filter   = ['day', 'week_number', 'worker__org']
    readonly_fields = ['week_number']
    search_fields = ['worker__full_name', 'worker__user_id']
    date_hierarchy = 'week_start'


class ShiftInline(admin.TabularInline):
    model  = Shift
    extra  = 0
    fields = ['worker', 'day', 'start_time', 'end_time', 'hours']
    readonly_fields = ['hours']


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display  = ['org', 'week_start', 'status', 'generated_by', 'generated_at']
    list_filter   = ['status', 'org']
    date_hierarchy = 'week_start'
    inlines       = [ShiftInline]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display  = ['worker', 'timetable', 'day', 'start_time', 'end_time', 'hours']
    list_filter   = ['day', 'timetable__org']
    search_fields = ['worker__full_name']
