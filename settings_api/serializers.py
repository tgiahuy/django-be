from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from api.models import UserProfile
from .models import (
    Address, NotificationSettings,
    TwoFactorAuth, OTPVerification, LoginSession,
    SocialAccount, Invoice
)


# ========================
# HỒ SƠ CÁ NHÂN
# ========================
class UserBasicInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login']
        read_only_fields = ['id', 'username', 'date_joined', 'last_login']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserBasicInfoSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'user', 'full_name', 'avatar', 'avatar_url',
            'phone', 'gender', 'date_of_birth', 'bio', 'updated_at'
        ]

    def get_full_name(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name or obj.user.username

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        # Fallback sang image (URL field cũ)
        return obj.image or None


class UpdateBasicInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=['male', 'female', 'other'], required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)


class UpdateContactInfoSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=15, required=False)
    otp_code = serializers.CharField(max_length=6, required=False, help_text="OTP khi đổi SĐT/Email")


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mật khẩu hiện tại không đúng.")
        return value

    def validate_new_password(self, value):
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 chữ hoa.")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 chữ số.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Mật khẩu xác nhận không khớp."})
        return data


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField()


# ========================
# SỔ ĐỊA CHỈ
# ========================
class AddressSerializer(serializers.ModelSerializer):
    full_address = serializers.SerializerMethodField()
    map_url = serializers.SerializerMethodField()

    class Meta:
        model = Address
        fields = [
            'id', 'full_name', 'phone', 'province', 'district', 'ward',
            'street_address', 'full_address', 'latitude', 'longitude',
            'map_url', 'is_default', 'address_type', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'full_address', 'map_url']

    def get_full_address(self, obj):
        return f"{obj.street_address}, {obj.ward}, {obj.district}, {obj.province}"

    def get_map_url(self, obj):
        if obj.latitude and obj.longitude:
            return f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
        import urllib.parse
        address = f"{obj.street_address}, {obj.ward}, {obj.district}, {obj.province}"
        encoded = urllib.parse.quote(address)
        return f"https://www.google.com/maps/search/?api=1&query={encoded}"

    def validate(self, data):
        request = self.context.get('request')
        if request and self.instance is None:
            count = Address.objects.filter(user=request.user).count()
            if count >= 10:
                raise serializers.ValidationError("Bạn chỉ có thể lưu tối đa 10 địa chỉ.")
        return data

    def create(self, validated_data):
        return Address.objects.create(user=self.context['request'].user, **validated_data)


class SetDefaultAddressSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()


# ========================
# THÔNG BÁO
# ========================
class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        exclude = ['id', 'user', 'fcm_token']

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class RegisterFCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField()


# ========================
# BẢO MẬT 2 LỚP
# ========================
class TwoFactorAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwoFactorAuth
        fields = ['is_enabled', 'method', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class Enable2FASerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=['phone', 'email', 'totp'])


class Verify2FASerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, min_length=6)

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Mã OTP chỉ gồm chữ số.")
        return value


class Disable2FASerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(max_length=6, required=False)


# ========================
# PHIÊN ĐĂNG NHẬP
# ========================
class LoginSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginSession
        fields = [
            'session_id', 'device_name', 'browser', 'os',
            'ip_address', 'location', 'is_current', 'last_active', 'created_at'
        ]
        read_only_fields = fields


class RevokeSessionSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()


# ========================
# MẠNG XÃ HỘI
# ========================
class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ['id', 'provider', 'provider_email', 'provider_name', 'connected_at']
        read_only_fields = fields


class ConnectSocialSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'facebook', 'github'])
    access_token = serializers.CharField()


class DisconnectSocialSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'facebook', 'github'])

    def validate_provider(self, value):
        user = self.context['request'].user
        if not SocialAccount.objects.filter(user=user, provider=value).exists():
            raise serializers.ValidationError(f"Tài khoản {value} chưa được liên kết.")
        return value


# ========================
# HÓA ĐƠN
# ========================
class InvoiceSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'order_id', 'issued_at',
            'billing_name', 'billing_address', 'billing_email',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount',
            'pdf_file', 'notes'
        ]
        read_only_fields = fields
