from django.contrib import admin
from .models import (
    Address, NotificationSettings, TwoFactorAuth,
    OTPVerification, LoginSession, SocialAccount, Invoice
)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'province', 'district', 'is_default', 'address_type']
    list_filter = ['is_default', 'address_type', 'province']
    search_fields = ['user__username', 'full_name', 'phone']


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_order_status', 'push_order_status', 'updated_at']
    search_fields = ['user__username']


@admin.register(TwoFactorAuth)
class TwoFactorAuthAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled', 'method', 'updated_at']
    list_filter = ['is_enabled', 'method']
    search_fields = ['user__username']


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'is_used', 'expires_at', 'created_at']
    list_filter = ['purpose', 'is_used']
    search_fields = ['user__username']


@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_name', 'browser', 'os', 'ip_address', 'is_current', 'last_active']
    list_filter = ['is_current', 'os', 'browser']
    search_fields = ['user__username', 'ip_address']


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'provider_email', 'provider_name', 'connected_at']
    list_filter = ['provider']
    search_fields = ['user__username', 'provider_email']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'order', 'billing_name', 'total_amount', 'issued_at']
    search_fields = ['invoice_number', 'billing_name', 'billing_email']
    readonly_fields = ['invoice_number', 'issued_at']
