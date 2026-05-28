"""
admin.py — Register models in Django Admin for easy management.
Useful during development for inspecting data and creating the first employee account.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from timetable_app.models import Organisation, WorkTypeLimit, User, Availability, Timetable, Shift


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'shop_open', 'shop_close', 'created_at']
    search_fields = ['name']


@admin.register(WorkTypeLimit)
class WorkTypeLimitAdmin(admin.ModelAdmin):
    list_display  = ['org', 'work_type', 'hours_per_week']
    list_filter   = ['work_type', 'org']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display   = ['user_id', 'full_name', 'role', 'work_type', 'org', 'is_active']
    list_filter    = ['role', 'work_type', 'is_active', 'org']
    search_fields  = ['user_id', 'full_name']
    readonly_fields = ['user_id', 'created_at', 'updated_at', 'plain_password']
    ordering       = ['full_name']

    fieldsets = (
        ('Identity',    {'fields': ('user_id', 'full_name', 'password')}),
        ('Role',        {'fields': ('role', 'work_type', 'org')}),
        ('Status',      {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Debug',       {'fields': ('plain_password',), 'classes': ('collapse',)}),
        ('Timestamps',  {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('full_name', 'role', 'work_type', 'org', 'password1', 'password2'),
        }),
    )


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display  = ['worker', 'week_start', 'day', 'start_time', 'submitted_at']
    list_filter   = ['day', 'week_start', 'worker__org']
    search_fields = ['worker__full_name', 'worker__user_id']
    date_hierarchy = 'week_start'


class ShiftInline(admin.TabularInline):
    model  = Shift
    extra  = 0
    fields = ['worker', 'day', 'start_time', 'end_time', 'hours']
    readonly_fields = ['hours']


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display  = ['org', 'week_start', 'status', 'generated_at']
    list_filter   = ['status', 'org']
    date_hierarchy = 'week_start'
    inlines       = [ShiftInline]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display  = ['worker', 'timetable', 'day', 'start_time', 'end_time', 'hours']
    list_filter   = ['day', 'timetable__org']
    search_fields = ['worker__full_name']
