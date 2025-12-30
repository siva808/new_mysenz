from .models import *
from .serializers import *
from rest_framework.exceptions import NotFound
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404

token_generator = PasswordResetTokenGenerator()

@api_view(["POST"])
@permission_classes([AllowAny])
def admin_login(request):
    email = request.data.get("email")
    password = request.data.get("password")
    user = authenticate(request, username=email, password=password)

    if user is not None:
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        username = None
        manager_id = None  # FIX – define default
        store_id = None

        if hasattr(user, "store_manager"):
            username = user.store_manager.manager_name
            manager_id = str(user.store_manager.id)

            if hasattr(user.store_manager, "store") and user.store_manager.store:
                store_id = str(user.store_manager.store.id)
        else:
            username = user.email

        return Response({
            "success": True,
            "access": access_token,
            "refresh": refresh_token,
            "user": {
                "uuid": str(user.id),
                "email": user.email,
                "role": user.role,   
                "username": username,
                "manager_id": manager_id,
                "store_id": store_id,
            }
        })

    return Response({"success": False, "message": "Invalid credentials"})

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get("email")
    try:
        user = AdminUser.objects.get(email=email)
    except AdminUser.DoesNotExist:
        return Response({"error": "User not found"}, status=404)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    reset_link = f"http://192.168.1.22:8000/api/auth/reset-password/{uid}/{token}/"
    send_mail(
        "Password Reset",
        f"It happens to the best of us.Tap the link below and Mysenze will guide you to a fresh new password: {reset_link}",
        "noreply@example.com",
        [user.email],
    )

    return Response({"success": True, "message": "Password reset link sent"})

@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = AdminUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, AdminUser.DoesNotExist):
        return Response({"error": "Invalid link"}, status=400)

    if not token_generator.check_token(user, token):
        return Response({"error": "Invalid or expired token"}, status=400)

    new_password = request.data.get("password")
    if not new_password:
        return Response({"error": "Password required"}, status=400)

    user.set_password(new_password)
    user.save()
    return Response({"success": True, "message": "Password reset successful"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh = request.data.get("refresh_token")
    if not refresh:
        return Response({
            "success":False,"message":"refresh token required "
        },status=400)
    try:
        token=RefreshToken(refresh)
        token.blacklist()
        return Response({"success":True,"message":"logout successfully"},status=200)
    except Exception as e:
        return Response({"success":False, "message":"invalidtoken or  expride refreshtoken"},status=401)
    

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_alldevices(request):
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken,BlacklistedToken
    tokens=OutstandingToken.objects.filter(user=request.user)
    for token in tokens:
        try:
            BlacklistedToken.objects.get_or_create(token=token)
        except:
            continue
    return Response({
        "successs":True,
        "message":"logged out from all devices."
    })


def get_dashboard_url(role):
    if role == "superadmin":
        return "/dashboard/admin"
    elif role == "manager":
        return "/dashboard/manager"
    elif role == "staff":
        return "/dashboard/staff"
    else:
        return "/dashboard/customer"

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_user(request):
    if request.user.role != "superadmin":
        return Response({"error": "Not authorized"}, status=403)

    email = request.data.get("email")
    password = request.data.get("password")
    role = request.data.get("role", "customer")

    if not email or not password:
        return Response({"error": "Email and password required"}, status=400)

    user = AdminUser.objects.create_user(email=email, password=password, role=role)
    return Response({
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    })

class StoreManagerPasscodeResetView(generics.UpdateAPIView):
    serializer_class = StoreManagerSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_object(self):
        return StoreManager.objects.get(pk=self.kwargs["pk"])

    def perform_update(self, serializer):
        instance = serializer.instance
        # regenerate passcode
        new_passcode = generate_passcode()
        instance.passcode = new_passcode
        instance.save()

        # send email to manager
        send_mail(
            subject="Your StoreManager access Passcode has been reset",
            message=f"Hello {instance.manager_name},\n\nYour new passcode is: {new_passcode}\n\nRegards,\nAdmin Team",
            from_email="admin@yourdomain.com",
            recipient_list=[instance.user.email],
            fail_silently=False,
        )


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]


class ServiceListView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        category_id = self.request.query_params.get("category")
        queryset = Service.objects.filter(show_in_ecom=True)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset
    
class TimeSlotListView(generics.ListAPIView):
    serializer_class = TimeSlotSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        store_id = self.request.query_params.get("store")
        date = self.request.query_params.get("date")

        queryset = TimeSlot.objects.filter(is_active=True)

        if store_id:
            queryset = queryset.filter(store_id=store_id)

        return queryset


class IsAdminOrStaff(permissions.BasePermission):
    """Allow only Admin, Manager, Staff roles."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [
            "superadmin", "admin", "manager", "staff"
        ])



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bookingdropdown(request):
    #data = list(BookingStatus.objects.values("id", "status"))
    data = list(BookingStatus.objects.values_list("status", flat=True))
    return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def paymentdropdown(request):
    #data = list(BookingStatus.objects.values("id", "status"))
    data = list(PaymentStatus.objects.values_list("status", flat=True))
    return Response({"success": True, "data": data}, status=status.HTTP_200_OK)



class SubcategoryAPIView(APIView):

    def get(self, request):
        category_id = request.query_params.get("category_id")

        try:
            if category_id:
                subcategories = SubCategory.objects.filter(category_id=category_id).order_by("id")
                serializer = SubcategorySerilalizer(subcategories, many=True)
                return Response({"success": True,"message": "Subcategories retrieved successfully", "data": serializer.data})

            
            subcategories = SubCategory.objects.all().order_by("id")
            serializer = SubcategorySerilalizer(subcategories, many=True)
            return Response({
                "success": True,
                "message": "All subcategories retrieved successfully",
                "data": serializer.data
            })

        except Exception as e:
            return Response({
                "success": False,
                "message": f"Error retrieving subcategories: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        serializer = SubcategorySerilalizer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "SubCategory created successfully",
            })
        return Response({
            "success": False,
            "message": "Validation failed",
            "errors": serializer.errors
        })
    
    def put(self, request): 
        subcategory_id = request.data.get("id") 
        name = request.data.get("name") 
        is_active = request.data.get("is_active") 
        try: 
            subcategory = get_object_or_404(SubCategory, pk=subcategory_id) 
            if not subcategory_id:
                return Response({ "success": False,"message": "id was required"})
            if name: 
                subcategory.name = name 
            if is_active is not None: 
                subcategory.is_active = is_active 
            subcategory.save() 
            serializer = SubcategorySerilalizer(subcategory) 
            return Response({ "success": True, "message": "SubCategory updated successfully", "data": serializer.data }) 
        except Exception as e: return Response({ "success": False, "message": f"Error updating SubCategory: {str(e)}" }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

# class AdminNotificationLogListView(generics.ListAPIView):
#     serializer_class = NotificationLogSerializer
#     permission_classes = [IsAdminOrStaff]
#     queryset = NotificationLog.objects.all().order_by("-timestamp")

# class AdminBillingLogListView(generics.ListAPIView):
#     serializer_class = BillingPushLogSerializer
#     permission_classes = [IsAdminOrStaff]
#     queryset = BillingPushLog.objects.all().order_by("-attempted_at")

# class SystemSettingsListCreateView(generics.ListCreateAPIView):
#     serializer_class = SystemSettingsSerializer
#     queryset = SystemSettings.objects.all()
#     permission_classes = [IsAdminOrStaff]


# class SystemSettingsUpdateView(generics.UpdateAPIView):
#     serializer_class = SystemSettingsSerializer
#     queryset = SystemSettings.objects.all()
#     permission_classes = [IsAdminOrStaff]


