import threading
from functools import wraps
from django.core.mail import send_mail
from django.conf import settings


class DocumentManager:
    @staticmethod
    def fetch_row(model_class, filters={}, field_list=[]):
        try:
            data = model_class.filter(**filters).only(*field_list).first()
            return data
        except Exception:
            return None

    @staticmethod
    def fetch_all_rows(model_class, filters={}, field_list=[], sort_list=[], lower_limit=None, upper_limit=None):
        qs = model_class.filter(**filters).only(*field_list)
        if sort_list:
            qs = qs.order_by(*sort_list)
        if lower_limit is not None and upper_limit is not None:
            qs = qs[lower_limit:upper_limit]
        return qs


    @staticmethod
    def edit_rows(model_class, filters=None, update_data=None):
        filters = filters or {}
        update_data = update_data or {}
        updated_count = model_class.filter(**filters).update(**update_data)
        return bool(updated_count)


    # @staticmethod
    # def store_rows(model_class, data={}):
    #     obj = model_class(**data)
    #     obj.save()
    #     return obj

    @staticmethod
    def store_rows(model_class, data={}):
        m2m_fields = {}
        
        # Separate out ManyToMany fields
        for key in list(data.keys()):
            try:
                field = model_class._meta.get_field(key)
                if field.many_to_many:
                    m2m_fields[key] = data.pop(key)
            except Exception:
                continue

        # Create and save the object
        obj = model_class(**data)
        obj.save()

        # Assign ManyToMany relationships
        for key, values in m2m_fields.items():
            getattr(obj, key).set(values)

        return obj


    @staticmethod
    def remove_rows(model_class, filters={}):
        deleted_count, _ = model_class.filter(**filters).delete()
        return bool(deleted_count)

    @staticmethod
    def count_rows(model_class, filters={}):
        return model_class.filter(**filters).count()


# Background decorator
def run_in_background(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return True
    return wrapper

# email sender
@run_in_background
def send_po_email(subject, message, recipient):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=False,
    )
