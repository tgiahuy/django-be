from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


# ========================
# SỔ ĐỊA CHỈ
# ========================
class Address(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Nhà riêng'),
        ('office', 'Văn phòng'),
        ('other', 'Khác'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    province = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    ward = models.CharField(max_length=100)
    street_address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='home')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Địa chỉ'
        verbose_name_plural = 'Sổ địa chỉ'

    def save(self, *args, **kwargs):
        # Đảm bảo chỉ có 1 địa chỉ mặc định
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.street_address}, {self.ward}, {self.district}"


# ========================
# CÀI ĐẶT THÔNG BÁO
# ========================
class NotificationSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')

    # Thông báo qua Email
    email_order_status = models.BooleanField(default=True)
    email_promotions = models.BooleanField(default=True)
    email_new_products = models.BooleanField(default=False)
    email_security = models.BooleanField(default=True)

    # Thông báo qua trình duyệt (Push Notification)
    push_order_status = models.BooleanField(default=True)
    push_promotions = models.BooleanField(default=False)
    push_new_products = models.BooleanField(default=False)
    push_security = models.BooleanField(default=True)

    # FCM token cho push notification
    fcm_token = models.TextField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cài đặt thông báo'
        verbose_name_plural = 'Cài đặt thông báo'

    def __str__(self):
        return f"Notification settings of {self.user.username}"


# ========================
# BẢO MẬT 2 LỚP (2FA)
# ========================
class TwoFactorAuth(models.Model):
    METHOD_CHOICES = [
        ('phone', 'Số điện thoại'),
        ('email', 'Email'),
        ('totp', 'Ứng dụng xác thực'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    is_enabled = models.BooleanField(default=False)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='email')
    secret_key = models.CharField(max_length=32, blank=True, null=True)
    backup_codes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Xác thực 2 lớp'
        verbose_name_plural = 'Xác thực 2 lớp'

    def __str__(self):
        return f"2FA for {self.user.username}"


class OTPVerification(models.Model):
    PURPOSE_CHOICES = [
        ('2fa_setup', 'Cài đặt 2FA'),
        ('2fa_verify', 'Xác thực 2FA'),
        ('change_password', 'Đổi mật khẩu'),
        ('change_phone', 'Đổi SĐT'),
        ('change_email', 'Đổi Email'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_verifications')
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mã OTP'
        verbose_name_plural = 'Mã OTP'
        ordering = ['-created_at']

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"OTP for {self.user.username} - {self.purpose}"


# ========================
# PHIÊN ĐĂNG NHẬP
# ========================
class LoginSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_sessions')
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    device_name = models.CharField(max_length=200, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=200, blank=True)
    is_current = models.BooleanField(default=False)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_active']
        verbose_name = 'Phiên đăng nhập'
        verbose_name_plural = 'Phiên đăng nhập'

    def __str__(self):
        return f"Session {self.session_id} - {self.user.username}"


# ========================
# LIÊN KẾT MẠNG XÃ HỘI
# ========================
class SocialAccount(models.Model):
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('github', 'GitHub'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    provider_email = models.EmailField(blank=True)
    provider_name = models.CharField(max_length=100, blank=True)
    access_token = models.TextField(blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'provider']
        verbose_name = 'Tài khoản MXH'
        verbose_name_plural = 'Tài khoản MXH'

    def __str__(self):
        return f"{self.user.username} - {self.provider}"


# ========================
# HÓA ĐƠN ĐIỆN TỬ
# ========================
class Invoice(models.Model):
    # Tham chiếu đúng sang api.Order (không phải store.Order)
    order = models.OneToOneField('api.Order', on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    billing_name = models.CharField(max_length=100)
    billing_address = models.TextField()
    billing_email = models.EmailField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    pdf_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Hóa đơn'
        verbose_name_plural = 'Hóa đơn'
        ordering = ['-issued_at']

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import datetime
            now = datetime.datetime.now()
            self.invoice_number = f"INV-{now.year}{now.month:02d}{now.day:02d}-{self.order.id:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number
