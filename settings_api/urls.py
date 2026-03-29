from django.urls import path
from . import views

urlpatterns = [

    # ========================
    # HỒ SƠ CÁ NHÂN
    # ========================
    path('profile/',          views.ProfileView.as_view(),          name='settings-profile'),
    path('profile/basic/',    views.UpdateBasicInfoView.as_view(),  name='settings-profile-basic'),
    path('profile/contact/',  views.UpdateContactInfoView.as_view(), name='settings-profile-contact'),
    path('profile/password/', views.ChangePasswordView.as_view(),  name='settings-change-password'),
    path('profile/avatar/',   views.AvatarUploadView.as_view(),    name='settings-avatar-upload'),

    # ========================
    # SỔ ĐỊA CHỈ
    # ========================
    path('addresses/',           views.AddressListCreateView.as_view(), name='settings-address-list'),
    path('addresses/<int:pk>/',  views.AddressDetailView.as_view(),     name='settings-address-detail'),
    path('addresses/default/',   views.SetDefaultAddressView.as_view(), name='settings-address-default'),

    # ========================
    # CÀI ĐẶT THÔNG BÁO
    # ========================
    path('notifications/',     views.NotificationSettingsView.as_view(), name='settings-notifications'),
    path('notifications/fcm/', views.RegisterFCMTokenView.as_view(),     name='settings-fcm-token'),

    # ========================
    # BẢO MẬT 2 LỚP
    # ========================
    path('2fa/',         views.TwoFactorAuthView.as_view(),   name='settings-2fa-status'),
    path('2fa/enable/',  views.Enable2FAView.as_view(),        name='settings-2fa-enable'),
    path('2fa/verify/',  views.Verify2FASetupView.as_view(),   name='settings-2fa-verify'),
    path('2fa/disable/', views.Disable2FAView.as_view(),       name='settings-2fa-disable'),

    # ========================
    # PHIÊN ĐĂNG NHẬP
    # ========================
    path('sessions/',            views.LoginSessionListView.as_view(),  name='settings-sessions'),
    path('sessions/revoke/',     views.RevokeSessionView.as_view(),     name='settings-session-revoke'),
    path('sessions/revoke-all/', views.RevokeAllSessionsView.as_view(), name='settings-session-revoke-all'),

    # ========================
    # MẠNG XÃ HỘI
    # ========================
    path('social/',             views.SocialAccountListView.as_view(), name='settings-social-list'),
    path('social/connect/',     views.ConnectSocialView.as_view(),     name='settings-social-connect'),
    path('social/disconnect/',  views.DisconnectSocialView.as_view(),  name='settings-social-disconnect'),

    # ========================
    # ĐƠN HÀNG & HÓA ĐƠN
    # ========================
    path('orders/',                      views.OrderHistoryView.as_view(),  name='settings-order-history'),
    path('invoices/',                    views.InvoiceListView.as_view(),   name='settings-invoice-list'),
    path('invoices/<int:order_id>/',     views.InvoiceDetailView.as_view(), name='settings-invoice-detail'),
]
