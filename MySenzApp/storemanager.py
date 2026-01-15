from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status,generics,permissions
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction 
from django.db.models import Count
from .crud import *
from .serializers import *
from .models import *
from .notification import NotificationService
import json 
from datetime import date, timedelta



class StoreManagerListView(generics.ListAPIView):
    serializer_class = StoreManagerDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StoreManager.objects.all()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "success": True,
                "message": "Store managers fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False,"message": "Failed to fetch store managers","errors": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryListView(generics.ListAPIView):
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.all()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({"success": True,"message": "Catogery fetched successfully","data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False,"message": "Failed to fetch store managers","errors": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class StoreManagerDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            uuid = request.query_params.get("uuid")
            if not uuid:
                return Response({"success": False,"message": "UUID query parameter is required"})

            manager = get_object_or_404(StoreManager, id=uuid)
            serializer = StoreManagerDetailSerializer(manager)

            return Response({"success":True,"message": "success","data": serializer.data})

        except StoreManager.DoesNotExist:
            return Response({"success": False,"message": "Manager not found"})

        except Exception as e:
            return Response({"success": False,"message": str(e)})



class UpdateStoreManagerActiveView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        manager_id = request.data.get("managerId")
        active_type = request.data.get("activeType") 

        if manager_id is None or active_type is None:
            return Response({"success": False, "message": "managerId and activeType are required"})

        manager = get_object_or_404(StoreManager, id=manager_id)
        manager.is_active = bool(active_type)
        manager.save()

        serializer = StoreManagerDetailSerializer(manager)
        return Response({"success": True,"message": f"Manager {'activated' if manager.is_active else 'deactivated'} successfully"})
    

class CategoryAPIView(APIView):

    def get(self, request):
        category_id = request.query_params.get("id")

        try:
            if category_id:

                category = get_object_or_404(Category, pk=category_id)
                serializer = ServiceCategorySerializer(category)

                return Response({"success": True,"message": "Category retrieved successfully","data": serializer.data}, status=status.HTTP_200_OK)

            categories = Category.objects.all().order_by("id")

            serializer = ServiceCategorySerializer(categories, many=True)
            return Response({"success": True,"message": "Categories retrieved successfully","data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False,"message": f"Error retrieving category: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        serializer = ServiceCategorySerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response({"success": True,"message": "Category created successfully"}, status=status.HTTP_201_CREATED)
        return Response({"success": False,"message": "Validation failed","errors": serializer.errors},status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        category_id = request.query_params.get("id")

        if not category_id:
            return Response({"success": False,"message": "id query parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = get_object_or_404(Category, pk=category_id)
            serializer = ServiceCategorySerializer(category, data=request.data)

            if serializer.is_valid():
                serializer.save()
                return Response({"success": True,"message": "Category updated successfully"}, status=status.HTTP_200_OK)
            return Response({"success": False,"message": "Validation failed","errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"success": False,"message": f"Error updating category: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        category_id = request.query_params.get("id")

        if not category_id:
            return Response({"success": False,"message": "id query parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = get_object_or_404(Category, pk=category_id)
            category.delete()

            return Response({"success": True,"message": "Category deleted successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"success": False,"message": f"Error deleting category: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ServiceAPIView(APIView):
    def get(self, request):
        category_name = request.query_params.get("name")
        if category_name:
            category = get_object_or_404(Service, name__iexact=category_name)
            serializer = ServiceDetailsSerializer(category)
            return Response({"success": True,"message": "Services retrieved successfully","data": serializer.data
            }, status=status.HTTP_200_OK)

        categories = Service.objects.all().order_by("id")
        serializer = ServiceDetailsSerializer(categories, many=True)
        return Response({"success": True,"message": "All Services retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ServiceCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True,"message": "Services created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({"success": False,"message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        service_id = request.data.get("id")
        if not service_id:
            return Response({"success": False,"message": "id body parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        service = get_object_or_404(Service, pk=service_id)
        serializer = ServiceSerializer(service, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True,"message": "Service updated successfully","data": serializer.data
        }, status=status.HTTP_200_OK)

        return Response({"success": False,"message": "Validation failed","errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)  

    def delete(self, request):
        category_name = request.query_params.get("name")
        if not category_name:
            return Response({"success": False,"message": "name query parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        category = get_object_or_404(Service, name__iexact=category_name)
        category.delete()
        return Response({"success": True,"message": "Services deleted successfully"}, status=status.HTTP_200_OK)
    


class ManagerServiceAPIView(APIView):

    def post(self, request):
        manager_id = request.data.get("manager")
        category_name = request.data.get("category_name")
        subcategory = request.data.get("subcategory_name")
        services_name = request.data.get("services_name", [])

        if not manager_id or not category_name:
            return Response({"success": False,"message": "manager and category_name are required"},status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                category = get_object_or_404(Category, name=category_name)

                obj, created = Mangerservices.objects.get_or_create(manager_id=manager_id,category=category,
                                                                    subcategory=subcategory,defaults={"services_name": services_name})

                if not created:
                    return Response({"success": False,"message": "Service already exists for this manager",}, status=status.HTTP_208_ALREADY_REPORTED)

                return Response({"success": True,"message": "Manager Service created successfully"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"success": False,"message": "Failed to create service","error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request):
        manager_id = request.query_params.get("manager_id")

        if manager_id:
            services = Mangerservices.objects.filter(manager__id=manager_id)
        else:
            services = Mangerservices.objects.all()

        serializer = StoreManagerServicesSerializer(services, many=True)
        return Response({"success": True,"message": "Manager Services retrieved successfully","data": serializer.data}, status=status.HTTP_200_OK)
    


class UpdateBookingAPI(APIView):
    def put(self, request):
        booking_id = request.data.get("booking_id")

        if not booking_id:
            return Response({"sucess":False,"error": "booking_id is required"}, status=400)

        try:
            booking = Booking.objects.get(booking_id=booking_id)
        except Booking.DoesNotExist:
            return Response({"sucess":False,"error": "Booking not found"}, status=404)

        serializer = BookingSerializer(booking, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"sucess":True,"message": "Booking updated"}, status=200)

        return Response(serializer.errors, status=400)
    



class BookingSearchView(APIView):

    def post(self, request):
    
        json_request = JSONParser().parse(request)
        appointment_type = json_request.get("appointment_type")
        store_id = json_request.get("store_id")
        detail_method = json_request.get("detail_method")
        start_date = json_request.get("start_date")
        end_date = json_request.get("end_date")
        
        if not store_id:
            return Response({"success": False,"message": "store_id is required" }, status=status.HTTP_400_BAD_REQUEST)

        try:
            store_uuid = uuid.UUID(store_id)
        except:
            return Response({"success": False,"message": "Invalid store_id UUID"},status=status.HTTP_400_BAD_REQUEST)

    
        bookings = Booking.objects.filter(store__id=store_uuid)

        today = date.today()
        tomorrow = today + timedelta(days=1)
        first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day_last_month = today.replace(day=1) - timedelta(days=1)

        if detail_method == "today":
            bookings = bookings.filter(appointment_date=today)
            

        elif detail_method == "tomorrow":
            bookings = bookings.filter(appointment_date=tomorrow)
            
        elif detail_method == "future":
            bookings = bookings.filter(appointment_date__gt=today)
           

        elif detail_method == "last_month":
            bookings = bookings.filter(
                appointment_date__gte=first_day_last_month,
                appointment_date__lte=last_day_last_month
            )
            

        elif detail_method == "custom":
            if not start_date or not end_date:
                return Response({"success": False,"message": "start_date and end_date are required for custom filter"},status=status.HTTP_400_BAD_REQUEST)

            try:
                start_date_obj = date.fromisoformat(start_date)
                end_date_obj = date.fromisoformat(end_date)
            except:
                return Response({"success": False,"message": "Invalid date format. Use YYYY-MM-DD."},status=status.HTTP_400_BAD_REQUEST)

            bookings = bookings.filter(
                appointment_date__gte=start_date_obj,
                appointment_date__lte=end_date_obj
            )
            
        
        if appointment_type:
            bookings = bookings.filter(appointment_type=appointment_type)

        bookings_count = bookings.count()
        
        serializer = BookingDashboardSerializer(bookings, many=True)
        return Response({"success": True, "message": "Bookings retrieved successfully",
                         "count": bookings_count, "data": serializer.data}, status=status.HTTP_200_OK)
    


@api_view(["PUT"])
def update_manager_services(request):
    try:
        manager_id = request.data.get("manager_id")     
        category_id = request.data.get("category_id")
        services_name = request.data.get("services_name")
        is_active = request.data.get("is_active")

        if not manager_id or not category_id:
            return Response(
                {"sucess":False,"error": "manager_id and category_id are required"},
                status=400
            )

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response({"sucess":False,"error": "Category not found"})

        try:
            manager_service = Mangerservices.objects.get(manager_id=manager_id,category=category)
        except Mangerservices.DoesNotExist:
            return Response({"sucess":False,"error": "Manager service not found"})

        if services_name is not None:
            manager_service.services_name = services_name

        if is_active is not None:
            manager_service.is_active = is_active

        manager_service.save()

        return Response(
            { "success": True,
                "message": "Manager service updated successfully",
                "data": {
                    "manager_id": manager_id,
                    "category": category_id,
                    "services_name": manager_service.services_name,
                    "is_active": manager_service.is_active,
                }
            },
            status=200
        )

    except Exception as e:
        return Response({"sucess":False,"error": str(e)}, status=500)
   


@api_view(["POST"])
def bookingscount(request):
    json_request = JSONParser().parse(request)
    store_id = json_request.get("store_id")
    if not store_id:
        return Response({"success": False,"message": "store_id is required" })
    try:
        store_uuid = uuid.UUID(store_id)
    except: 
        return Response({"success": False,"message": "Invalid store_id UUID"})     
    bookings = Booking.objects.filter(store__id=store_uuid)
    total_bookings = bookings.count()

    today = date.today()
    today_bookings = bookings.filter(appointment_date=today).count()
    tomorrow = today + timedelta(days=1)
    tomarrow_bookings = bookings.filter(appointment_date=tomorrow).count()
    
    future_bookings = bookings.filter(appointment_date__gt=today).count()
    first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_day_last_month = today.replace(day=1) - timedelta(days=1)
    last_month_bookings = bookings.filter(
        appointment_date__gte=first_day_last_month,
        appointment_date__lte=last_day_last_month
    ).count()
    data = {
         "total_bookings" : total_bookings,
         "today_bookings" : today_bookings,
        "future_bookings" : future_bookings,
         "tomarrow_bookings" : tomarrow_bookings,
         "last_month_bookings" : last_month_bookings
    }
    return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


@api_view(["POST"])
def category_booking_count(request):
    
    json_request = JSONParser().parse(request)
    store_id = json_request.get("store_id")
    category_id = json_request.get("category")

    try:
        store_uuid = uuid.UUID(store_id)
    except:
        return Response({"success": False,"message": "Invalid UUID format"})

    bookings = Booking.objects.filter(store__id=store_uuid,)

    if category_id:
        bookings = bookings.filter(category__id=category_id)
        serializer = BookingGetSerializer(bookings, many=True)
        return Response({
            "success": True,
            "message": "Booking details retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    if category_id:
        bookings = bookings.filter(category__id=category_id)
    category_counts = (
        bookings.values("category__id", "category__name")
        .annotate(count=Count("booking_id"))
        .order_by("category__name")
    )
    

    return Response({"success": True,"message": "Booking count retrieved successfully",
        "data": {"booking_count": list(category_counts)}
    }, status=status.HTTP_200_OK)



@api_view(["PUT"])
def update_manager_booking(request):
    json_request = JSONParser().parse(request)

    booking_id = json_request.get("booking_id")
    booking_status = json_request.get("status")
    payment_status = json_request.get("payment_status")
    appointment_type = json_request.get("appointment_type")
    appointment_date = json_request.get("appointment_date")
    appointment_time = json_request.get("appointment_time")
    service_names = json_request.get("service")

    if not booking_id:
        return Response({"sucess":False,"error": "booking_id is required"}, status=400)

    try:
        booking = Booking.objects.get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)

    if booking_status is not None:
        booking.status = booking_status

    if payment_status is not None:
        booking.payment_status = payment_status

    if appointment_type is not None:
        booking.appointment_type = appointment_type

    if appointment_date is not None:
        booking.appointment_date = appointment_date

    if appointment_time is not None:
        booking.appointment_time = appointment_time

    booking.save()
    if service_names is not None:
        try:
            services = Service.objects.filter(name__in=service_names)

            if len(services) != len(service_names):
                return Response(
                    {"success": False, "error": "One or more service IDs are invalid"},status=400)
            booking.services.set(services)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=500)

    return Response({"success": True, "message": "Booking updated"}, status=200)


@api_view(["POST"])
def passcode_verify(request):

    data = JSONParser().parse(request)
    manager_id = data.get("manager_id")
    passcode = data.get("passcode")

    if not manager_id or not passcode:
        return Response(
            {"success": False, "message": "manager_id or passcode required !.. "},)
    
    try:
        manager = StoreManager.objects.get(id=manager_id,passcode=passcode)
        return Response(
            {"success": True, "message": "Passcode verified"},
            status=200
        )

    except StoreManager.DoesNotExist:
        return Response(
            {"success": False, "message": "Invalid passcode"})


@api_view(["POST"])
def get_services_by_categoryy(request):
    data = JSONParser().parse(request)
    category_id= data.get("category_id")
    if not category_id:
        return Response({"success": False, "message": "category_id is required"})
    try:
        services = Service.objects.filter(category__id=category_id)
        service_names = [s.name for s in services]
        

        return Response({"success": True, "service_names": service_names})
    except Exception as e:
        return Response(
            {"success": False, "message": str(e)},
            status=500
        )
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])   
def get_store_manager_profile(request):
    try:
        store_manager = StoreManager.objects.get(user=request.user)
        serializer = StoreManagerSerializer(store_manager)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except StoreManager.DoesNotExist:
        return Response({"success": False, "message":"No StoreManager profile found for this user"})
    

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_store_manager(request):
    try:
        details_raw = request.data.get("details")
        details = json.loads(details_raw) if isinstance(details_raw, str) else details_raw

        serializer = StoreConfigSerializer(data=details)
        if not serializer.is_valid():
            return Response({"success": False,"message": "Validation failed","errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        store = Store.objects.create(
            store_name=data["storeName"],
            store_contact=data["storeContact"],
            store_address=data["storeAddress"],
            gst=data["gstNumber"],
            dl=data["dlNumber"],
            gst_certificate=request.FILES.get("gstCertificate"), 
            dl_image=request.FILES.get("dlImage"),
            FFSI_image=request.FILES.get("ffsiImage")
        )

        manager_user = AdminUser.objects.create_user(
            email=data["managerEmail"],
            password=data["managerPassword"],
            role="manager"
        )

        store_manager = StoreManager.objects.create(
            store=store,
            user=manager_user,
            manager_name=data["managerName"],
            manager_contact=data["managerContact"]
        )

        return Response({"success": True,"message": "StoreManager created successfully"})

    except Exception as e:
        return Response({"success": False,"message": "Unexpected error occurred","details": str(e)
        },status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        