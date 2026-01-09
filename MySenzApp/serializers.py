from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.response import Response


class TimestampMixin(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True, required=False)

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ["id", "username", "email", "role", "is_active"]



class StoreConfigSerializer(serializers.Serializer):
    storeName = serializers.CharField()
    storeContact = serializers.CharField()
    storeAddress = serializers.CharField()
    gstNumber = serializers.CharField()   
    dlNumber = serializers.CharField()   
    gstCertificate = serializers.ImageField(required=False, allow_null=True)
    dlImage = serializers.ImageField(required=False, allow_null=True)
    FFSIImage = serializers.ImageField(required=False, allow_null=True)
    managerEmail = serializers.EmailField()
    managerPassword = serializers.CharField(write_only=True)
    managerName = serializers.CharField()
    managerContact = serializers.CharField()



class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "store_name", "store_contact", "store_address"]

class StoreManagerSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)
    manager_email = serializers.EmailField(source="user.email", read_only=True)
    class Meta:
        model = StoreManager
        fields = ["id", "manager_name", "manager_contact", "manager_email", "store","is_active"]
        read_only_fields = ["created_at", "passcode"]

class StoreManagerDetailSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)
    manager_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = StoreManager
        fields = ["id", "manager_name", "manager_contact", "manager_email", "store","is_active"]


class SubcategorySerilalizer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    
    class Meta:
        model= SubCategory
        fields =["id","category","category_name","name","is_active"]



class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id","name","is_active"]


class ServiceDetailsSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True)
    subcategory = SubcategorySerilalizer(read_only=True) 
    subcategory_id = serializers.PrimaryKeyRelatedField( queryset=SubCategory.objects.all(), write_only=True)

    class Meta:
        model = Service
        fields = ["id","name","price","description","is_active","category","category_id","subcategory", "subcategory_id"]


class ServiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id","name", "description", "price", "category","subcategory"]


class ServiceSerializer(serializers.ModelSerializer):

    class Meta:
        
        model = Service
        fields = ["id","name", "description","price","category","show_in_ecom",
                  "home_care_enabled","instore_enabled","is_active","subcategory"]

class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ["id","start_time","end_time","is_active",]


class CustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "email", "name", "contact", "address", "created_at"]


class StoreManagerserviceSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = StoreManager
        fields = ["id","manager_name","manager_contact","user_email","store_name","subcategory_name","category_name","service_name",
            "is_active","created_at","updated_at"]
        

class StoreManagerServicesSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Mangerservices
        fields = ["id", "manager", "category", "category_name", "services_name", "is_active"]
class StoreManagerServicesSerializerupdate(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name")

    class Meta:
        model = Mangerservices
        fields = ["id", "manager", "category", "category_name", "services_name", "is_active"]
        
class ManagerServicesSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Mangerservices
        fields = ["category_name", "services_name", "is_active"]

    
class ManagerCategoryServiceSerializer(serializers.ModelSerializer):
    assignments = serializers.SerializerMethodField()

    class Meta:
        model = StoreManager
        fields = ["id", "manager_name", "is_active", "assignments"]

    def get_assignments(self, obj):
        return [
            {"category_name": c.name, "service_name": s.name, "is_active": obj.is_active}
            for c in obj.categories.all()
            for s in obj.services.all()
        ]





User = get_user_model()

class CustomerSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = AdminUser
        fields = ["email", "password"]

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        user = AdminUser.objects.create_user(email=email,password=password,role="customer")
        Customer.objects.create(user=user)
        return user


class CustomerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("User is inactive")
        data["user"] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account with this email")
        return value
    
class BookingSearchSerializer(serializers.ModelSerializer):
    customer_name=serializers.CharField(source="user.name",read_only=True)
    store_name = serializers.CharField(source="stor.store_name",read_only=True)
    servic_name= serializers.CharField(source="service.name",read_only=True)
    class Meta:
        model = Booking
        field= '__all__'
        

class BookingSerializer(serializers.ModelSerializer):
    services = serializers.ListField(child=serializers.UUIDField(), write_only=True)
    services_details = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Booking
        fields =["booking_id","user","customer_mobile","store","category","services","service_details","appointment_type","appointment_date","appointment_time",
            "booking_address","status","payment_status",]
        read_only_fields = ["booking-id"]

    def get_services_details(self, obj):
        services = obj.services.all()
        return [{"id": s.id, "name": s.name, "price": s.price} for s in services]
    
    def create(self, validated_data):
        services_data = validated_data.pop("services", [])
        booking = Booking.objects.create(**validated_data)
        booking.services.set(services_data)
        return booking
    
    def update(self, instance, validated_data):
        services_data = validated_data.pop("services", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        if services_data is not None:
            instance.services.set(services_data)
       
        return instance
    
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id","name","is_active"]

class BookingGetSerializer(serializers.ModelSerializer):
    user = CustomerSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    booking_date_formatted = serializers.SerializerMethodField()

    def get_booking_date_formatted(self, obj):
        return obj.booking_date.strftime("%Y-%m-%d %I:%M:%S %p")
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ["booking_id", "booking_date_formatted"]


class Bookingupdateserializer(serializers.ModelSerializer):
    class Meta:
        model =Booking
        fields=["category","service","appoinment_type","status","update_at"]
    
class CustomerSerilaizer(serializers.ModelSerializer):
    class meta:
        model=Customer
        fields=["id","name","contact","address","create_at"]

class BookingDetailsSerializer(serializers.ModelSerializer):
    customer=CustomerSerilaizer(read_only=True)
    class Meta:
        model = Booking 
        fields = ["booking_id","service","category",""]
        read_only_field=["customer_name","customer_email"]
        
class BookingDashboardSerializer(serializers.ModelSerializer):
    service_names = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    total_service_amount = serializers.SerializerMethodField()
    booking_code = serializers.SerializerMethodField()
    booking_date_formatted = serializers.SerializerMethodField()

    def get_service_names(self, obj):
        return [service.name for service in obj.services.all()]

    def get_customer_name(self, obj):
        
        customer = getattr(obj.user, "customer", None)
        return customer.name if customer else None

    def get_customer_email(self, obj):
        
        return getattr(obj.user, "email", None)

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_total_service_amount(self, obj):
        services = obj.services.all()
        total = sum([s.price for s in services if hasattr(s, "price")])
        return float(total)

    def get_booking_code(self, obj):
        
        short = str(obj.booking_id).replace("-", "")[:5].upper()
        return f"ELIX-{short}"

    def get_booking_date_formatted(self, obj):
        return obj.booking_date.strftime("%Y-%m-%d %I:%M:%S %p")

    class Meta:
        model = Booking
        fields = ["booking_id","booking_code","booking_date_formatted","appointment_type","appointment_date","appointment_time","status","payment_status","booking_address",
            # Relations
            "store","category","category_name","services","service_names",
            # Customer details
            "customer_mobile","customer_name","customer_email",
            # Computed
            "total_service_amount",
        ]
        read_only_fields = ["booking_id", "booking_date"]

