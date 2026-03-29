from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
import random
import string

from api.models import UserProfile, Order
from api.serializers import OrderSerializer
from .models import (
    Address, NotificationSettings,
    TwoFactorAuth, OTPVerification, LoginSession,
    SocialAccount, Invoice
)
from .serializers import (
    UserProfileSerializer, UpdateBasicInfoSerializer,
    UpdateContactInfoSerializer, ChangePasswordSerializer,
    AvatarUploadSerializer, AddressSerializer, SetDefaultAddressSerializer,
    NotificationSettingsSerializer, RegisterFCMTokenSerializer,
    TwoFactorAuthSerializer, Enable2FASerializer, Verify2FASerializer,
    Disable2FASerializer, LoginSessionSerializer, RevokeSessionSerializer,
    SocialAccountSerializer, ConnectSocialSerializer, DisconnectSocialSerializer,
    InvoiceSerializer
)


# ========================
# HELPERS
# ========================
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


# ========================
# HỒ SƠ CÁ NHÂN
# ========================
class ProfileView(APIView):
    """GET: Xem toàn bộ hồ sơ cá nhân"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)


class UpdateBasicInfoView(APIView):
    """PUT: Cập nhật thông tin cơ bản (tên, giới tính, ngày sinh, bio)"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UpdateBasicInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        profile = get_or_create_profile(user)

        # Cập nhật User model
        for field in ('first_name', 'last_name'):
            if field in data:
                setattr(user, field, data[field])
        user.save()

        # Cập nhật Profile model
        for field in ('gender', 'date_of_birth', 'bio'):
            if field in data:
                setattr(profile, field, data[field])
        profile.save()

        return Response({
            "message": "Cập nhật thông tin thành công.",
            "data": UserProfileSerializer(profile, context={'request': request}).data
        })


class UpdateContactInfoView(APIView):
    """GET: Gửi OTP  |  PUT: Cập nhật email hoặc SĐT sau khi có OTP"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """POST: Yêu cầu gửi OTP xác thực"""
        purpose = request.data.get('purpose', 'change_phone')
        if purpose not in ('change_phone', 'change_email', 'change_password'):
            return Response({"error": "purpose không hợp lệ."}, status=400)

        otp = generate_otp()
        expires = timezone.now() + timedelta(minutes=5)
        OTPVerification.objects.filter(user=request.user, purpose=purpose, is_used=False).delete()
        OTPVerification.objects.create(
            user=request.user, otp_code=otp,
            purpose=purpose, expires_at=expires
        )
        # TODO: gửi OTP thực tế qua email/SMS
        return Response({"message": f"Mã OTP đã được gửi đến {request.user.email}. Hiệu lực 5 phút."})

    def put(self, request):
        """PUT: Cập nhật email / SĐT sau khi cung cấp OTP"""
        serializer = UpdateContactInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        profile = get_or_create_profile(user)

        if 'email' in data or 'phone' in data:
            otp_code = data.get('otp_code')
            if not otp_code:
                return Response({"error": "Cần cung cấp otp_code để thay đổi thông tin liên hệ."}, status=400)

            otp_obj = OTPVerification.objects.filter(
                user=user, otp_code=otp_code, is_used=False
            ).last()

            if not otp_obj or not otp_obj.is_valid():
                return Response({"error": "Mã OTP không hợp lệ hoặc đã hết hạn."}, status=400)

            otp_obj.is_used = True
            otp_obj.save()

        if 'email' in data:
            user.email = data['email']
            profile.email = data['email']
            user.save()
        if 'phone' in data:
            profile.phone = data['phone']
        profile.save()

        return Response({"message": "Cập nhật thông tin liên hệ thành công."})


class ChangePasswordView(APIView):
    """PUT: Thay đổi mật khẩu"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response({"message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."})


class AvatarUploadView(APIView):
    """POST: Upload ảnh đại diện"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = get_or_create_profile(request.user)
        profile.avatar = serializer.validated_data['avatar']
        profile.save()

        return Response({
            "message": "Cập nhật ảnh đại diện thành công.",
            "avatar_url": request.build_absolute_uri(profile.avatar.url)
        })


# ========================
# SỔ ĐỊA CHỈ
# ========================
class AddressListCreateView(APIView):
    """GET: Danh sách địa chỉ  |  POST: Thêm địa chỉ mới"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        return Response(AddressSerializer(addresses, many=True).data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        address = serializer.save()
        return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    """GET / PUT / DELETE: Chi tiết, sửa, xóa một địa chỉ"""
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return Address.objects.get(pk=pk, user=request.user)
        except Address.DoesNotExist:
            return None

    def get(self, request, pk):
        address = self.get_object(request, pk)
        if not address:
            return Response({"error": "Không tìm thấy địa chỉ."}, status=404)
        return Response(AddressSerializer(address).data)

    def put(self, request, pk):
        address = self.get_object(request, pk)
        if not address:
            return Response({"error": "Không tìm thấy địa chỉ."}, status=404)
        serializer = AddressSerializer(address, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Cập nhật địa chỉ thành công.", "data": serializer.data})

    def delete(self, request, pk):
        address = self.get_object(request, pk)
        if not address:
            return Response({"error": "Không tìm thấy địa chỉ."}, status=404)
        address.delete()
        return Response({"message": "Đã xóa địa chỉ."}, status=204)


class SetDefaultAddressView(APIView):
    """POST: Đặt địa chỉ mặc định"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetDefaultAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            address = Address.objects.get(pk=serializer.validated_data['address_id'], user=request.user)
        except Address.DoesNotExist:
            return Response({"error": "Không tìm thấy địa chỉ."}, status=404)

        address.is_default = True
        address.save()
        return Response({"message": f"Đã đặt '{address.street_address}' làm địa chỉ mặc định."})


# ========================
# CÀI ĐẶT THÔNG BÁO
# ========================
class NotificationSettingsView(APIView):
    """GET / PUT: Xem và cập nhật cài đặt thông báo"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings_obj, _ = NotificationSettings.objects.get_or_create(user=request.user)
        return Response(NotificationSettingsSerializer(settings_obj).data)

    def put(self, request):
        settings_obj, _ = NotificationSettings.objects.get_or_create(user=request.user)
        serializer = NotificationSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Đã cập nhật cài đặt thông báo.", "data": serializer.data})


class RegisterFCMTokenView(APIView):
    """POST: Đăng ký FCM token cho push notification"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RegisterFCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settings_obj, _ = NotificationSettings.objects.get_or_create(user=request.user)
        settings_obj.fcm_token = serializer.validated_data['fcm_token']
        settings_obj.save()
        return Response({"message": "Đã đăng ký push notification."})


# ========================
# BẢO MẬT 2 LỚP
# ========================
class TwoFactorAuthView(APIView):
    """GET: Xem trạng thái 2FA"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        two_fa, _ = TwoFactorAuth.objects.get_or_create(user=request.user)
        return Response(TwoFactorAuthSerializer(two_fa).data)


class Enable2FAView(APIView):
    """POST: Bật 2FA — gửi OTP để xác nhận"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Enable2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method = serializer.validated_data['method']
        user = request.user

        otp = generate_otp()
        expires = timezone.now() + timedelta(minutes=5)
        OTPVerification.objects.filter(user=user, purpose='2fa_setup', is_used=False).delete()
        OTPVerification.objects.create(user=user, otp_code=otp, purpose='2fa_setup', expires_at=expires)

        profile = get_or_create_profile(user)
        target = profile.phone if method == 'phone' and profile.phone else user.email

        # TODO: Gửi OTP thực tế (email/SMS)
        return Response({
            "message": f"Mã OTP đã được gửi đến {target}. Nhập OTP để hoàn tất cài đặt 2FA.",
            "method": method
        })


class Verify2FASetupView(APIView):
    """POST: Xác nhận OTP để hoàn tất bật 2FA"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Verify2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        otp_obj = OTPVerification.objects.filter(
            user=user, purpose='2fa_setup', is_used=False
        ).last()

        if not otp_obj or not otp_obj.is_valid():
            return Response({"error": "Mã OTP không hợp lệ hoặc đã hết hạn."}, status=400)

        if otp_obj.otp_code != serializer.validated_data['otp_code']:
            return Response({"error": "Mã OTP không đúng."}, status=400)

        otp_obj.is_used = True
        otp_obj.save()

        two_fa, _ = TwoFactorAuth.objects.get_or_create(user=user)
        two_fa.is_enabled = True
        backup_codes = [''.join(random.choices(string.ascii_uppercase + string.digits, k=8)) for _ in range(8)]
        two_fa.backup_codes = backup_codes
        two_fa.save()

        return Response({
            "message": "Đã bật xác thực 2 lớp thành công.",
            "backup_codes": backup_codes,
            "notice": "Lưu các mã dự phòng này ở nơi an toàn. Chúng sẽ không hiển thị lại."
        })


class Disable2FAView(APIView):
    """POST: Tắt 2FA"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Disable2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not user.check_password(serializer.validated_data['password']):
            return Response({"error": "Mật khẩu không đúng."}, status=400)

        two_fa, _ = TwoFactorAuth.objects.get_or_create(user=user)
        two_fa.is_enabled = False
        two_fa.backup_codes = []
        two_fa.save()

        return Response({"message": "Đã tắt xác thực 2 lớp."})


# ========================
# PHIÊN ĐĂNG NHẬP
# ========================
class LoginSessionListView(APIView):
    """GET: Danh sách tất cả phiên đăng nhập"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = LoginSession.objects.filter(user=request.user)
        return Response({
            "total": sessions.count(),
            "sessions": LoginSessionSerializer(sessions, many=True).data
        })


class RevokeSessionView(APIView):
    """POST: Thu hồi một phiên đăng nhập"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RevokeSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = LoginSession.objects.get(
                session_id=serializer.validated_data['session_id'],
                user=request.user
            )
            if session.is_current:
                return Response({"error": "Không thể thu hồi phiên hiện tại."}, status=400)
            session.delete()
            return Response({"message": "Đã đăng xuất khỏi thiết bị đó."})
        except LoginSession.DoesNotExist:
            return Response({"error": "Không tìm thấy phiên đăng nhập."}, status=404)


class RevokeAllSessionsView(APIView):
    """POST: Đăng xuất khỏi tất cả thiết bị khác"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        deleted, _ = LoginSession.objects.filter(user=request.user, is_current=False).delete()
        return Response({"message": f"Đã đăng xuất khỏi {deleted} thiết bị khác."})


# ========================
# MẠNG XÃ HỘI
# ========================
class SocialAccountListView(APIView):
    """GET: Danh sách tài khoản MXH đã liên kết"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = SocialAccount.objects.filter(user=request.user)
        return Response(SocialAccountSerializer(accounts, many=True).data)


class ConnectSocialView(APIView):
    """POST: Liên kết tài khoản mạng xã hội"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConnectSocialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data['access_token']

        # TODO: Xác thực token thực tế với Google/Facebook/GitHub
        provider_data = self._verify_social_token(provider, access_token)
        if not provider_data:
            return Response({"error": "Token không hợp lệ."}, status=400)

        account, created = SocialAccount.objects.get_or_create(
            user=request.user, provider=provider,
            defaults={
                'provider_user_id': provider_data.get('id', ''),
                'provider_email': provider_data.get('email', ''),
                'provider_name': provider_data.get('name', ''),
                'access_token': access_token,
            }
        )

        if not created:
            return Response({"error": f"Tài khoản {provider} đã được liên kết."}, status=400)

        return Response({
            "message": f"Đã liên kết tài khoản {provider} thành công.",
            "data": SocialAccountSerializer(account).data
        })

    def _verify_social_token(self, provider, token):
        """TODO: Gọi API của Google/Facebook/GitHub để xác thực token thực tế."""
        return {"id": "mock_id", "email": "mock@example.com", "name": "Mock User"}


class DisconnectSocialView(APIView):
    """DELETE: Hủy liên kết tài khoản mạng xã hội"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        serializer = DisconnectSocialSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        SocialAccount.objects.filter(user=request.user, provider=serializer.validated_data['provider']).delete()
        return Response({"message": f"Đã hủy liên kết tài khoản {serializer.validated_data['provider']}."})


# ========================
# ĐƠN HÀNG & HÓA ĐƠN
# ========================
class OrderHistoryView(APIView):
    """GET: Lịch sử đơn hàng (có lọc theo status, phân trang)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')

        order_status = request.query_params.get('status')
        if order_status:
            orders = orders.filter(status=order_status)

        page = max(int(request.query_params.get('page', 1)), 1)
        per_page = 10
        start = (page - 1) * per_page
        total = orders.count()

        serializer = OrderSerializer(orders[start:start + per_page], many=True, context={'request': request})
        return Response({
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
            "results": serializer.data
        })


class InvoiceDetailView(APIView):
    """GET: Xem hóa đơn của một đơn hàng"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            invoice = Invoice.objects.get(order__id=order_id, order__user=request.user)
        except Invoice.DoesNotExist:
            return Response({"error": "Không tìm thấy hóa đơn."}, status=404)
        return Response(InvoiceSerializer(invoice).data)


class InvoiceListView(APIView):
    """GET: Danh sách tất cả hóa đơn của user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.filter(order__user=request.user).order_by('-issued_at')
        return Response(InvoiceSerializer(invoices, many=True).data)
