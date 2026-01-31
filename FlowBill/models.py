from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
import uuid
from MySenzApp.models import Category,Store,SubCategory,Service
from decimal import Decimal 


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
    bank_state = models.CharField(max_length=50, blank=True, null=True)
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
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    product_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    hsn_Code = models.CharField(max_length=20, blank=True, null=True)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0,blank=True, null=True)  
    description = models.TextField(blank=True)   
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Medicine-specific fields 
    brand_name = models.CharField(max_length=100, blank=True, null=True) 
    molecule = models.CharField(max_length=100, blank=True, null=True) 
    uom = models.CharField(max_length=20, blank=True, null=True)  
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
        indexes = [ models.Index(fields=["sub_category"]), 
                   models.Index(fields=["brand_name"]), 
                   models.Index(fields=["material"]),
                 models.Index(fields=["category"])]



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
    class Meta:
        db_table="purchaseorder"
        indexes = [
            models.Index(fields=["vendor", "status"]),
        ]
        


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
    class Meta:
        db_table = "purchaseorderitem"



class Indent(models.Model):
    indent_number = models.CharField(max_length=20, unique=True, blank=True) 
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="indents") 
    status = models.CharField(max_length=150)
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
        indexes = [
            models.Index(fields=["store", "status"]),
        ]



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



class UOM(models.Model):
    name= models.CharField(max_length=20)

    def __str__(self):
        return self.name
    class Meta:
        db_table= "uom"



class GRN(models.Model):
    grn_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="grns")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE,null=True, blank=True)
    status = models.CharField(max_length=20) 
    invoice_date = models.DateField(null=True, blank=True)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "grn"
        indexes = [
          models.Index(fields= ["purchase_order"]),
          models.Index(fields= ["status"]),
          models.Index(fields= ["vendor"]),
          ]

    def __str__(self):
      return self.grn_number
    
    def save(self, *args, **kwargs): 
        if not self.grn_number: 
            super().save(*args, **kwargs) 
            self.grn_number = f"GRN-WH-{self.id:07d}" 
            super().save(update_fields=["grn_number"]) 
        else: 
            super().save(*args, **kwargs)



class GRNItem(models.Model):
    grn = models.ForeignKey(GRN, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    batch_no = models.CharField(max_length=50)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    accepted_qty = models.IntegerField(blank=True, null=True)
    received_qty = models.IntegerField(blank=True, null=True)
    damaged_qty = models.IntegerField(blank=True, null=True)
    excess_qty = models.IntegerField(blank=True, null=True)
    free_qty = models.IntegerField(blank=True, null=True)
    rejected_qty = models.IntegerField(default=0, blank=True, null=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)  # vendor rate
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # % or INR
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margin = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    reason = models.CharField(max_length=50, blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "grn_item"
        indexes = [
            models.Index(fields=["product", "batch_no"]),
        ]
    
    def calculate_margin(self):
        mrp = Decimal(self.mrp)
        purchase_price = Decimal(self.purchase_price)
        return mrp - purchase_price

    def save(self, *args, **kwargs):
        self.margin = self.calculate_margin()
        self.amount = self.purchase_price * self.accepted_qty
        super().save(*args, **kwargs)

        batch, created = ProductBatch.objects.get_or_create(
            product=self.product,
            batch_no=self.batch_no,
            defaults={
                "grn": self.grn,
                "expiry_date": self.expiry_date,
                "mrp": self.mrp,
                "purchase_price": self.purchase_price,
                "margin_price": self.margin,
                "stock": self.accepted_qty,
            }
        )
        batch.stock += self.accepted_qty
        batch.save(update_fields=["stock"])
    def __str__(self):
        name = self.product.name if self.product else "unknown"
        return f"{self.grn.grn_number} | {name} | {self.accepted_qty}/{self.rejected_qty}"



class ProductBatch(models.Model):
    grn = models.ForeignKey(GRN, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    batch_no = models.CharField(max_length=50)
    expiry_date = models.DateField(null=True, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    margin_price = models.DecimalField(max_digits=10,decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = "product_batch"
        indexes = [
            models.Index(fields=["product", "batch_no"]),
            models.Index(fields=[ "product"]),
        ]

    def __str__(self):
        return f"{self.product.name} | Batch {self.batch_no} | Stock {self.stock}"



class Dispatch(models.Model):
    
    dispatch_id = models.CharField(max_length=15,unique=True,blank=True)
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE,related_name="dispatches")
    store = models.ForeignKey(Store, on_delete=models.CASCADE,related_name="dispatches")
    status = models.CharField(max_length=20, default="dispatched")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs): 
        if not self.dispatch_id: 
            super().save(*args, **kwargs) 
            self.dispatch_id = f"GRN-WH-{self.id:07d}" 
            super().save(update_fields=["dispatch_id"]) 
        else: 
            super().save(*args, **kwargs)

    class Meta:
        db_table = "dispatch"
        indexes = [ models.Index(fields=["store","status"])]



class DispatchItem(models.Model):
    
    dispatch = models.ForeignKey(Dispatch,on_delete=models.CASCADE,related_name="items")
    indent_item = models.ForeignKey(IndentItem, on_delete=models.CASCADE) 
    product_batch = models.ForeignKey(ProductBatch, on_delete=models.CASCADE) 
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "dispatchitem"



class Recipe(models.Model):
    recipe_id = models.CharField(max_length=20, unique=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipe"

        indexes = [
            models.Index(fields=["service"]),
        ]
    def save(self, *args, **kwargs):
        if not self.recipe_id:
            super().save(*args, **kwargs)
            self.recipe_id = f"RCP-{self.id:05d}"
            super().save(update_fields=["recipe_id"])
        else:
            super().save(*args, **kwargs)



class Recipeiterm(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    version = models.PositiveIntegerField(default=1)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recipeitem"
        indexes = [
            models.Index(fields=["recipe","product","version"]),
        ]



class GRNReturn(models.Model):
    grn_return_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="returns")
    status = models.CharField(max_length=20, default="initiated") 
    vendor_type = models.CharField(max_length=20)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        db_table = "grn_return"
        indexes = [
            models.Index(fields=["vendor", "status"]),
        ]

    def __str__(self):
        return self.grn_return_number

    def save(self, *args, **kwargs):
        if not self.grn_return_number:
            super().save(*args, **kwargs)
            self.grn_return_number = f"GRN-RET-{self.id:07d}"
            super().save(update_fields=["grn_return_number"])
        else:
            super().save(*args, **kwargs)



class GRNReturnItem(models.Model):
    grn_return = models.ForeignKey(GRNReturn, on_delete=models.CASCADE, related_name="items")
    product_item = models.ForeignKey(ProductBatch,on_delete=models.CASCADE)
    batch_no = models.CharField(max_length=50)
    return_quantity = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "grn_return_item"
        indexes = [
            models.Index(fields=["grn_return", "product_item"]),
        ]



class CreditNote(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    grn = models.ForeignKey(GRNReturn, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=50,default="CreditNote")
    active = models.BooleanField(default=True) 
    insert_type = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "credit_note"




class InedentReturn(models.Model):
    indent_return_number = models.CharField(max_length=50, unique=True)
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="returns")
    status = models.CharField(max_length=20, default="initiated")  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "indent_return"
        indexes = [
            models.Index(fields=["indent", "status"]),
        ]

    def __str__(self):
        return self.indent_return_number

    def save(self, *args, **kwargs):
        if not self.indent_return_number:
            super().save(*args, **kwargs)
            self.indent_return_number = f"IND-RET-{self.id:07d}"
            super().save(update_fields=["indent_return_number"])
        else:
            super().save(*args, **kwargs)



class IndentReturnItem(models.Model):
    indent_return = models.ForeignKey(InedentReturn, on_delete=models.CASCADE, related_name="items")
    indent_item = models.ForeignKey(IndentItem, on_delete=models.CASCADE)
    return_quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)

    class Meta:
        db_table = "indent_return_item"
        indexes = [
            models.Index(fields=["indent_return", "indent_item"]),
        ]




class Packages(models.Model):
    package_name = models.CharField(max_length=100,db_index=True)
    package_type = models.CharField(max_length=50)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    discount = models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "packages"

class PackagesItem(models.Model):
    packages = models.ForeignKey(Packages,on_delete=models.CASCADE,db_index=True)
    product = models.ForeignKey(Product,on_delete=models.CASCADE,blank=True,null=True)
    service = models.ForeignKey(Service,on_delete=models.CASCADE,blank=True,null=True)
    item_type = models.CharField(max_length=50)
    qty = models.PositiveIntegerField()
    

    class Meta:
        db_table = "packages_item"






# class StoreGrn(models.Model):
#     grn_number = models.CharField(max_length=50, unique=True)
#     indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="store_grns") 
#     status = models.CharField(max_length=20, default="created") 
#     received_date = models.DateField(auto_now_add=True) 
#     net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0) 
#     created_at = models.DateTimeField(auto_now_add=True) 
#     updated_at = models.DateTimeField(auto_now=True)

#     def save(self,*args, **kwargs):
#         if not self.grn_number:
#             super().save(*args,**kwargs)
#             self.grn_number= f"GRN-ST-{self.id:07d}"
#             super().save(update_fields=["grn_number"])
#         else:
#             super().save(*args,**kwargs)

#     def __str__(self):
#         return self.grn_number
    
#     class Meta:
#         db_table = "storegrn"