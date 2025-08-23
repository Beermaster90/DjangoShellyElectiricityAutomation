from django.contrib import admin
from django.contrib.auth.models import User
from .models import ShellyDevice, ElectricityPrice, DeviceAssignment, AppSetting
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
import pytz

### SHELLY DEVICE ADMIN ###
class ShellyDeviceAdmin(admin.ModelAdmin):
    list_display = (
        'device_id', 'familiar_name', 'shelly_api_key', 'shelly_device_name', 
        'run_hours_per_day', 'day_transfer_price', 'night_transfer_price', 
        'created_at', 'updated_at', 'user', 'status', 'last_contact', 'relay_channel', 'shelly_server'
    )
    search_fields = ('familiar_name',)
    readonly_fields = ('device_id', 'created_at', 'updated_at')  # 'user' is editable for admins

    fields = (
        'device_id', 'familiar_name', 'shelly_api_key', 'shelly_device_name', 
        'run_hours_per_day', 'day_transfer_price', 'night_transfer_price', 
        'created_at', 'updated_at', 'user', 'status', 'last_contact', 'relay_channel', 'shelly_server'
    )

    ordering = ['-device_id']

    def save_model(self, request, obj, form, change):
        """ Ensure new devices are owned by the user who creates them if not set. """
        if not change and not request.user.is_superuser:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """ Limit users to only see their own devices. """
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Allow admins to select any user in dropdown.
        Ensure normal users see only themselves.
        """
        if db_field.name == "user":
            if request.user.is_superuser:
                kwargs["queryset"] = User.objects.all()  # Admins see all users
            else:
                kwargs["queryset"] = User.objects.filter(id=request.user.id)  # Users only see themselves
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(ShellyDevice, ShellyDeviceAdmin)


### ELECTRICITY PRICE ADMIN (View Only for Non-Admins) ###
@admin.register(ElectricityPrice)
class ElectricityPriceAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time', 'price_kwh', 'created_at')
    search_fields = ('start_time', 'end_time')
    list_filter = ('start_time', 'end_time')
    ordering = ('-start_time',)
    readonly_fields = ('start_time', 'end_time', 'price_kwh', 'created_at')  # All fields are read-only

    def has_add_permission(self, request):
        return request.user.is_superuser  # Only admins can add

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser  # Only admins can edit

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only admins can delete


### DEVICE ASSIGNMENT ADMIN (Users Can Manage Their Own Assignments) ###
class DeviceAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'get_start_time_local', 'get_end_time_local', 'assigned_at')
    search_fields = ('user__username', 'device__familiar_name', 'electricity_price__start_time')
    list_filter = ('user', 'device', 'electricity_price__start_time')
    ordering = ('-assigned_at',)
    readonly_fields = ('assigned_at',)  # Users cannot modify the assignment timestamp

    def get_queryset(self, request):
        """ Limit users to only see their own assignments. """
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Ensure admins can assign devices to any user.
        Regular users can only assign devices to themselves.
        Show electricity price dropdown in local (Finnish) time.
        """
        if db_field.name == "device" and not request.user.is_superuser:
            kwargs["queryset"] = ShellyDevice.objects.filter(user=request.user)

        if db_field.name == "user":
            if request.user.is_superuser:
                kwargs["queryset"] = User.objects.all()  # Admins see all users
            else:
                kwargs["queryset"] = User.objects.filter(id=request.user.id)  # Users only see themselves

        if db_field.name == "electricity_price":
            local_tz = pytz.timezone('Europe/Helsinki')
            queryset = kwargs.get("queryset", ElectricityPrice.objects.all())
            # Attach a display string for local time, but use .replace(tzinfo=pytz.UTC) if naive
            for price in queryset:
                dt = price.start_time
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
                local_dt = dt.astimezone(local_tz)
                price.local_time_display = local_dt.strftime('%Y-%m-%d %H:%M')
                price.utc_time_display = dt.strftime('%Y-%m-%d %H:%M')
            kwargs["queryset"] = queryset

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def label_from_instance(self, obj):
        # Show both local and UTC time in dropdown
        if hasattr(obj, 'local_time_display') and hasattr(obj, 'utc_time_display'):
            return f"{obj.local_time_display} (local) [{obj.utc_time_display} UTC] ({obj.price_kwh} c/kWh)"
        return super().label_from_instance(obj)

    def save_model(self, request, obj, form, change):
        """ Ensure non-admin users can only assign devices to themselves. """
        if not request.user.is_superuser:
            obj.user = request.user  # Force user field to be request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """ Allow users to delete **only their own** assignments. """
        if request.user.is_superuser:
            return True  # Admins can delete everything
        return obj is None or obj.user == request.user  # Users can delete only their own assignments

    def get_readonly_fields(self, request, obj=None):
        """ Hide the 'user' field from non-admins (automatically set to request.user). """
        readonly = super().get_readonly_fields(request, obj)
        return readonly if request.user.is_superuser else readonly + ('user',)

    def get_start_time_local(self, obj):
        local_tz = pytz.timezone('Europe/Helsinki')
        local_dt = obj.electricity_price.start_time.astimezone(local_tz)
        return local_dt.strftime('%Y-%m-%d %H:%M')
    get_start_time_local.short_description = 'Start Time (Local)'

    def get_end_time_local(self, obj):
        local_tz = pytz.timezone('Europe/Helsinki')
        local_dt = obj.electricity_price.end_time.astimezone(local_tz)
        return local_dt.strftime('%Y-%m-%d %H:%M')
    get_end_time_local.short_description = 'End Time (Local)'

admin.site.register(DeviceAssignment, DeviceAssignmentAdmin)

admin.site.register(AppSetting)

