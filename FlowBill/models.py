from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
import uuid
from MySenzApp.models import *
from django.core.validators import MinValueValidator


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
    purchase_order = models.ForeignKey(PurchaseOrder,on_delete=models.PROTECT,related_name="grns")
    vendor = models.ForeignKey(Vendor,on_delete=models.SET_NULL,null=True,blank=True,related_name="grns")
    status = models.CharField(max_length=20, db_index=True)
    invoice_date = models.DateField(null=True, blank=True)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "grn"
        indexes = [
            models.Index(fields=["purchase_order"], name="grn_po_idx"),
            models.Index(fields=["status"], name="grn_status_idx"),
            models.Index(fields=["vendor"], name="grn_vendor_idx"),
        ]

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating and not self.grn_number:
            self.grn_number = f"GRN-WH-{self.id:07d}"
            super().save(update_fields=["grn_number"])

    def __str__(self):
        return self.grn_number




class GRNItem(models.Model):
    grn = models.ForeignKey(GRN, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product,on_delete=models.SET_NULL,null=True,blank=True,related_name="grn_items")
    batch_no = models.CharField(max_length=50)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    accepted_qty = models.PositiveIntegerField(default=0)
    received_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    excess_qty = models.PositiveIntegerField(default=0)
    free_qty = models.PositiveIntegerField(default=0)
    rejected_qty = models.PositiveIntegerField(default=0)

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margin = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    reason = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)

    class Meta:
        db_table = "grn_item"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "batch_no", "grn"],
                name="uniq_grn_product_batch"
            )
        ]
        indexes = [
            models.Index(fields=["product", "batch_no"], name="grnitem_prod_batch_idx"),
        ]

    def save(self, *args, **kwargs):
        self.margin = self.mrp - self.purchase_price
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

        if not created:
            batch.stock += self.accepted_qty
            batch.save(update_fields=["stock"])

    def __str__(self):
        product_name = self.product.name if self.product else "Unknown"
        return f"{self.grn.grn_number} | {product_name} | {self.accepted_qty}"




class ProductBatch(models.Model):
    grn = models.ForeignKey(GRN, on_delete=models.CASCADE, related_name="batches")
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name="product_batches")
    batch_no = models.CharField(max_length=50)
    expiry_date = models.DateField(null=True, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    margin_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_batch"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "batch_no"],
                name="uniq_product_batch"
            )
        ]
        indexes = [
            models.Index(fields=["product"], name="productbatch_product_idx"),
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




class StoreGrn(models.Model):

    grn_number = models.CharField(max_length=50, unique=True)
    store = models.ForeignKey(Store,on_delete=models.CASCADE)
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="store_grns") 
    status = models.CharField(max_length=20, default="completed") 
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0) 
    created_at = models.DateTimeField(auto_now_add=True) 
    
    def save(self,*args, **kwargs):
        if not self.grn_number:
            super().save(*args,**kwargs)
            self.grn_number= f"GRN-ST-{self.id:07d}"
            super().save(update_fields=["grn_number"])
        else:
            super().save(*args,**kwargs)

    def __str__(self):
        return self.grn_number
    
    class Meta:
        db_table = "storegrn"
        indexes = [
            models.Index(fields= ["indent"]),
            models.Index(fields=["status"])
        ]



class StoreGrnItem(models.Model):

    store_grn = models.ForeignKey(StoreGrn, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    batch_no = models.CharField(max_length=50)
    expiry_date = models.DateField(null=True, blank=True)

    accepted_qty = models.IntegerField(blank=True, null=True, default=0)
    received_qty = models.IntegerField(blank=True, null=True, default=0)
    damaged_qty = models.IntegerField(blank=True, null=True, default=0)
    excess_qty = models.IntegerField(blank=True, null=True, default=0)
    free_qty = models.IntegerField(blank=True, null=True, default=0)
    rejected_qty = models.IntegerField(default=0, blank=True, null=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)  
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margin_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    reason = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "store_grn_item"
        indexes = [
            models.Index(fields=["product", "batch_no"]),
        ]

    def save(self, *args, **kwargs):
        self.amount = (self.purchase_price or 0) * (self.accepted_qty or 0)
        super().save(*args, **kwargs)

        batch, created = Stock.objects.get_or_create(
            store=self.store_grn.store,
            storegrn=self.store_grn,   
            product=self.product,
            batch_no=self.batch_no,
            defaults={
                "expiry_date": self.expiry_date,
                "mrp": self.mrp,
                "purchase_price": self.purchase_price,
                "margin_price": self.margin_price,
                "gst_percent": self.gst_percent,
                "stock": self.accepted_qty or 0,
            }
        )
        if not created:
            batch.stock += (self.accepted_qty or 0)
            batch.save(update_fields=["stock"])



class Stock(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    storegrn = models.ForeignKey(StoreGrn,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stocks")
    batch_no = models.CharField(max_length=50)
    expiry_date = models.DateField(null=True, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    margin_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock"
        indexes = [
            models.Index(fields=["store", "product", "batch_no"]), 
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.store.store_name} | {self.product.name} | Batch {self.batch_no} | Stock {self.stock}"





class StoreGrnReturn(models.Model):
    storegrn_return_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, default="initiated")
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    store = models.ForeignKey(Store,on_delete=models.CASCADE)
    return_type = models.CharField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "storegrn_return"
        indexes = [
            models.Index(fields=["store", "status"]),
        ]

    def __str__(self):
        return self.storegrn_return_number

    def save(self, *args, **kwargs):
        if not self.storegrn_return_number:
            super().save(*args, **kwargs)
            self.storegrn_return_number = f"GRN-RET-{self.id:07d}ST"
            super().save(update_fields=["storegrn_return_number"])
        else:
            super().save(*args, **kwargs)


class StoreGrnReturnItem(models.Model):
    storegrn_return = models.ForeignKey(StoreGrnReturn, on_delete=models.CASCADE, related_name="items")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    batch_no = models.CharField(max_length=50)
    return_qty = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "storegrn_return_item"
        indexes = [
            models.Index(fields=["storegrn_return"]),
        ]




class Invoice(models.Model):
    store = models.ForeignKey(Store,on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice_no = models.CharField(max_length=30,blank=True, unique=True)
    status = models.CharField(max_length=10,choices=[("DRAFT", "DRAFT"), ("FINAL", "FINAL")])
    total = models.DecimalField(max_digits=10,decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    payment_method = models.CharField(max_length=30,blank=True)


    class Meta:
        db_table = "invoice"
        indexes = [models.Index(fields=["store", "customer", "invoice_no"]),
                   models.Index(fields=["status"])]
        
    def save(self, *args, **kwargs):
        creating = self.pk is None

        super().save(*args, **kwargs)

        if creating and not self.invoice_no:
            self.invoice_no = f"ELX-CHN-{self.id:07d}"
            super().save(update_fields=["invoice_no"])


        

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice,on_delete=models.PROTECT,related_name="items")
    item_type = models.CharField(max_length=10)
    stock = models.ForeignKey(Stock, null=True, blank=True, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE)
    package = models.ForeignKey(Packages, null=True, blank=True, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    mrp = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)])
    discount= models.DecimalField(max_digits=10, decimal_places=2, default=0,validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)])
    Sub_total = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)])

    class Meta:
        db_table = "invoice_item"
        indexes = [models.Index(fields=["invoice", "stock"])]


