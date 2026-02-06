from django.urls import path
from . views import *
from . storemanager import *
from . customer import *


urlpatterns = [
    path("admin/login/", admin_login, name="admin_login"),
    path("admin/create-user/", create_user, name="create_user"),
    path("admin/auth-forgot-password/", forgot_password, name="forgot_password"),
    path("admin/auth-reset-password/<uidb64>/<token>/", reset_password, name="reset_password"),
    path("admin/logout/",logout,name="logout"),
    path("admin/logout-alldevices/",logout_alldevices,name="logout_alldevices"),
   
    #store-manager
    path("admin/store-manager-create/", create_store_manager, name="create_store_manager"),
    path("admin/store-manager-profile/", get_store_manager_profile, name="store_manager_profile"),
    # path("admin/store-manager-list/",StoreManagerListView.as_view(),name="StoreManagerListView"),
    # path("admin/store-manager-details/", StoreManagerDetailView.as_view(), name="store_manager_details"),
    #path("admin/store-manager-active/", UpdateStoreManagerActiveView.as_view(), name="update-store-manager-active"),
    path("admin/store-manager/",StoreManagerView.as_view(),name="store_manager"),
    path('admin/categories/', CategoryAPIView.as_view()),
    path("admin/services/",ServiceAPIView.as_view()),
    path("admin/manager-service/", ManagerServiceAPIView.as_view()),
    path("admin/manager-booking-update/",update_manager_booking,name="manager_booking_update"),
    path("admin/manager-passcode-verify/",passcode_verify,name="verify_manager_passcode"),
    path("admin/subcategory/",SubcategoryAPIView.as_view(),name="SubcategoryAPIView"),
    path("admin/store-partner/", storepartner.as_view(), name="create_store_partner"),
    #path("admin/manager-update-service/",update_manager_services,name="manager_update_services"),
    
    path("admin/manager-service-update/", update_manager_services,),
    path("admin/category-counts/",category_booking_count,name="manager_dashboard"),



    #booking 
    path("admin/store-category/",CategoryListView.as_view(),name="store_catogery_list"),
    path("admin/store-service-list/",ServiceListView.as_view(),name="store_serice_list"),
    path("admin/store-timeslot-list/",TimeSlotListView.as_view(),name="store_timeslot_list"),
    path("admin/customer-booking/",BookingAPIView.as_view()),
    path("admin/booking-details/",BookingSearchView.as_view()),
    path("admin/create-booking/",create_booking,name="create_booking"),

    #cutomer 
    path("admin/customer-signup/", CustomerSignupView.as_view(), name="customer-signup"),
    path("admin/customer-login/", CustomerLoginView.as_view(), name="customer-login"),
    path("admin/cutomer-logout/", CustomerLogoutView.as_view(), name="customer-logout"),
    path("admin/customer-forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),

    #gentral
    path("admin/bookingdropdown/", bookingdropdown),
    path("admin/paymentdropdown/", paymentdropdown),
    path("admin/bookings-count/", bookingscount),
    path("admin/service-dropdown/", get_services_by_categoryy),
]

