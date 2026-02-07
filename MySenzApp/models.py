import uuid,random,string 
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class AdminUserManager(BaseUserManager):
    def create_user(self, email, password=None, role="customer", **extra_fields):

        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "superadmin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)
    class Meta:
        db_table="adminusermanager"



class AdminUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # 🔑 UUID instead of int
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, default="customer")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = AdminUserManager()

    def __str__(self):
        return self.email
    class Meta:
        db_table="adminusers"    



class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(AdminUser, on_delete=models.CASCADE, related_name="customer")
    name = models.CharField(max_length=200)
    contact = models.CharField(max_length=20,db_index=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    class Meta:
        db_table = "customer"
    


class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.start_time}-{self.end_time} (Day {self.day_of_week})"
    class Meta:
        db_table="timeslot"



class Store(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_name = models.CharField(max_length=150)
    store_code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    store_contact = models.CharField(max_length=20)
    store_address = models.TextField()
    gst = models.CharField(max_length=15, unique=True)
    dl = models.CharField(max_length=12, unique=True)
    store_formate = models.CharField(max_length=50, blank=True, null=True)
    store_category = models.CharField(max_length=50, blank=True, null=True)
    create_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    
    gst_certificate = models.ImageField(upload_to="store/gst_certificates/", null=True, blank=True)
    dl_image = models.ImageField(upload_to="store/drug_license/", null=True, blank=True)
    FFSI_image = models.ImageField(upload_to="store/FFSI_image/", null=True, blank=True)
    clinicalLicense_image = models.ImageField(upload_to="store/clinical_license/", null=True, blank=True)
    fireSafetyLicense_image = models.ImageField(upload_to="store/fire_safety_license/", null=True, blank=True)


    class Meta:
        db_table = "store"

    def save(self, *args, **kwargs):
        if not self.store_code:
            last_store = Store.objects.order_by('-create_at').first()
            if last_store and last_store.store_code:
                try:
                    last_num = int(last_store.store_code.split('-')[1])
                except (IndexError, ValueError):
                    last_num = 0
            else:
                last_num = 0

            self.store_code = f"ST-{last_num + 1:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.store_name

        


class StorePartner(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="partners")
    partner_name = models.CharField(max_length=150)
    partner_contact = models.CharField(max_length=20)
    partner_email = models.EmailField()
    partner_gst = models.CharField(max_length=15, blank=True, null=True)
    partner_adhar = models.CharField(max_length=12, blank=True, null=True)
    partner_pan = models.CharField(max_length=10, blank=True, null=True)

    company_name = models.CharField(max_length=150, blank=True, null=True)
    gst = models.CharField(max_length=15, blank=True, null=True)
    company_email = models.EmailField(blank=True, null=True)
    company_pan = models.CharField(max_length=10, blank=True, null=True)

    partner_adhar_image = models.ImageField(upload_to="storepartner/adhar_images/", blank=True, null=True)
    partner_pan_image = models.ImageField(upload_to="storepartner/pan_images/", blank=True, null=True)
    company_gst_certificate = models.ImageField(upload_to="storepartner/company_gst_certificates/", blank=True, null=True)
    company_pan_image = models.ImageField(upload_to="storepartner/company_pan_images/", blank=True, null=True)
    incorporation_certificate = models.ImageField(upload_to="storepartner/incorporation_certificates/", blank=True, null=True)


    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of shares")

    bank_name = models.CharField(max_length=100)
    branch_name = models.CharField(max_length=100, blank=True, null=True)
    bank_state = models.CharField(max_length=50, blank=True, null=True)
    account_holder_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=11)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    bank_address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.partner_name} - {self.store.store_name}"

    class Meta:

        db_table = "storepartner"

        indexes = [
            models.Index(fields=[ "store","partner_name"]),
        ]



class Category(models.Model):
    name = models.CharField(max_length=100,unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table="categorys"



class SubCategory(models.Model): 
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories") 
    name = models.CharField(max_length=100, unique=True) 
    discount = models.DecimalField(max_digits=5, decimal_places=2,null=True, blank=True)
    is_active = models.BooleanField(default=True) 

    def __str__(self): 
        return f"{self.category.name} - {self.name}"
     
    class Meta: 
        db_table = "subcategories"



class Service(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory,on_delete=models.CASCADE)
    name = models.CharField(max_length=255,unique=True)
    description = models.TextField(blank=True)
    price = models.IntegerField()
    show_in_ecom = models.BooleanField(default=True)
    home_care_enabled = models.BooleanField(default=True)
    instore_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    class Meta:
        db_table="services"



class Storeservices(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="services")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory,on_delete=models.CASCADE)
    services_name = ArrayField(models.CharField(max_length=150), default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table="Storeservices"



class Booking(models.Model):
    
    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("Customer", on_delete=models.CASCADE)
    customer_mobile = models.CharField(max_length=15)
    store = models.ForeignKey("Store", on_delete=models.CASCADE)
    category = models.ForeignKey("Category", on_delete=models.CASCADE)
    services = models.ManyToManyField("Service", related_name="bookings")

    appointment_type = models.CharField(max_length=20)
    appointment_date = models.DateField()
    appointment_time = ArrayField(models.CharField(max_length=150), default=list)

    booking_address = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="new booking")
    booking_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        return f"Booking {self.booking_id} - Services: {[s.name for s in self.services.all()]}"

    class Meta:
        db_table = "booking"
        indexes = [
            models.Index(fields=["store", "status","payment_status"]),
        ]



class BookingStatus(models.Model):
    status = models.CharField(max_length=50)
    class Meta:
        db_table="bookingstatus"



class PaymentStatus(models.Model):
    status = models.CharField(max_length=50)
    class Meta:
        db_table="paymentstatus"



ser = get_user_model()
def generate_passcode(length=6):
    return ''.join(random.choices(string.digits, k=length)) 



class StoreManager(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="managers")
    user = models.OneToOneField(AdminUser, on_delete=models.CASCADE, related_name="store_manager")
    is_active = models.BooleanField(default=True)
    manager_name = models.CharField(max_length=150)
    manager_contact = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    passcode = models.CharField(max_length=10, default=generate_passcode)

    def __str__(self):
        return f"{self.manager_name} ({self.user.email})"
    class Meta:
        db_table="storemanager"




class AppointmentStatusLog(models.Model):
    appointment = models.ForeignKey(Booking, on_delete=models.CASCADE)
    status = models.CharField(max_length=30)
    updated_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table="appoinmentstatuslog"



