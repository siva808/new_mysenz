from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
import uuid
from MySenzApp.models import Category,Store,SubCategory



class Vendor(models.Model):
    
    vendor_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    address = models.TextField()
    mobile = models.CharField(max_length=15)
    email = models.EmailField()

    gst = models.CharField(max_length=15)
    category = models.ForeignKey(Category,on_delete=models.CASCADE)
    sub_categories = ArrayField(models.CharField(max_length=50), default=list, blank=True)

    #banke details 

    bank_name = models.CharField(max_length=100) 
    branch_name = models.CharField(max_length=100, blank=True, null=True) 
    account_holder_name = models.CharField(max_length=100) 
    account_number = models.CharField(max_length=30) 
    ifsc_code = models.CharField(max_length=11) 
    swift_code = models.CharField(max_length=15, blank=True, null=True) 
    upi_id = models.CharField(max_length=50, blank=True, null=True) 
    pan_number = models.CharField(max_length=10, blank=True, null=True) 
    bank_address = models.TextField(blank=True, null=True)

    #payment method
    payment = models.CharField(max_length=50,default="CREDIT")
    credit_days = models.PositiveIntegerField(default=0)

    #common fields 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    

    def save(self, *args, **kwargs): 
        if not self.vendor_id:
            unique_code = uuid.uuid4().hex[:8].upper()
            self.vendor_id = f"VND-{unique_code}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    class Meta:
        db_table = "vendor"
    


class Product(models.Model):
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="products")
    product_id = models.CharField(max_length=20, unique=True, blank=True)

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1) 
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Medicine-specific fields 
    brand_name = models.CharField(max_length=100, blank=True, null=True) 
    molecule = models.CharField(max_length=100, blank=True, null=True) 
    uom = models.CharField(max_length=20, blank=True, null=True) # strip, box, tablet 

    # optical fields
    shape = models.CharField(max_length=50, blank=True, null=True) 
    material = models.CharField(max_length=50, blank=True, null=True) 
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)


    #coomon fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def save(self, *args, **kwargs):

        if not self.id:  
            super().save(*args, **kwargs)
        if not self.product_id:
            self.product_id = f"PRD-WH-{self.id:06d}"
            super().save(update_fields=["product_id"])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = "product"

    



class PurchaseOrder(models.Model):

    po_number = models.CharField(max_length=20, unique=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    order_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, default="created")  # created, received, cancelled
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    #common fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.po_number:
            super().save(*args, **kwargs)
            self.po_number = f"PO-WH-{self.id:06d}"
            super().save(update_fields=["po_number"])
        else:
            super().save(*args, **kwargs)

    def recalc_total(self): 
        self.total_amount = sum(item.subtotal for item in self.items.all())
        self.save(update_fields=["total_amount"])

    def __str__(self):
        return self.po_number


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)

    qty = models.PositiveIntegerField()
    uom = models.CharField(max_length=20)  # Nos, ml, strip, etc.
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        if self.product:
            return f"{self.product.name} x {self.qty} {self.uom}"
        
        return f"Item {self.id}"




class Indent(models.Model):
    indent_number = models.CharField(max_length=20, unique=True, blank=True) 
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="indents") 
    status = models.CharField( max_length=150)
    suggested_vendors = ArrayField(models.IntegerField(), default=list, blank=True)
    remarkers = models.CharField(max_length=150)

    #coomen fields
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True) 
    
    def save(self, *args, **kwargs): 
        if not self.indent_number: 
            super().save(*args, **kwargs) 
            self.indent_number = f"IND-{self.id:06d}" 
            super().save(update_fields=["indent_number"]) 
        else: 
            super().save(*args, **kwargs) 
        def __str__(self): 
            return self.indent_number 
    class Meta: 
        db_table = "indent" 

class IndentItem(models.Model): 
    
    indent = models.ForeignKey(Indent, related_name="items", on_delete=models.CASCADE) 
    product = models.ForeignKey(Product, on_delete=models.CASCADE , null=True, blank=True) 
    quantity = models.PositiveIntegerField() 

    def __str__(self):

        return f"{self.product.name} x {self.quantity}"
     
    class Meta: 
        db_table = "indent_item"

class IndentStatus(models.Model):
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.status
    

class GRN(models.Model):
    grn_number = models.CharField(max_length=50, unique=True)
    grn_type = models.CharField(max_length=16,)

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="grns")
    status = models.CharField(max_length=20, choices=[("Partial", "Partial"), ("Full", "Full")])

    dispatch_id = models.IntegerField(null=True, blank=True) 
    request_id=models.CharField(max_length=64,unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "grn"
        indexes = [
          models.Index(fields= ["purchase_order"]),
          models.Index(fields= ["status"]),]

    def __str__(self):
      return self.grn_number


class GRNItem(models.Model):

    grn = models.ForeignKey(GRN, on_delete=models.CASCADE, related_name="items")

    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)

    batch_no = models.CharField(max_length=50)
    manufacturing_date= models.DateField(null=True,blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    #subcategory 
    accepted_qty = models.IntegerField()
    received_qty =models.IntegerField()
    damaged_qty = models.IntegerField()
    expired_qty = models.IntegerField()

    rejected_qty = models.IntegerField(default=0)
    finala_ptr = models.IntegerField()
    uom= models.CharField(max_length=20)
    mrp= models.IntegerField()
    reason = models.CharField(max_length=50,blank=True)

    creted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table="grn_item"
        indexes = [
            models.Index(fields=["product","batch_no"]),
        ]

    def __str__(self):
        name = self.product.name if self.product else "unknown"
        return f"{self.grn.grn_number} | {name} | {self.accepted_qty}/{self.rejected_qty}"



class UOM(models.Model):
    name= models.CharField(max_length=20)

    def __str__(self):
        return self.name
    class Meta:
        db_table= "uom"


#class subcategory()
# category based to created fk
#  discount percentage
# verify to discount verfication discount 
#mrp to 20 from 70 

