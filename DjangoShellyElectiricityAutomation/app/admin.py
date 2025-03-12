from django.contrib import admin
from .models import ShellyDevice, ElectricityPrice, DeviceAssignment

### SHELLY DEVICE ADMIN ###
class ShellyDeviceAdmin(admin.ModelAdmin):
    list_display = (
        'device_id', 'familiar_name', 'shelly_api_key', 'shelly_device_name', 
        'run_hours_per_day', 'day_transfer_price', 'night_transfer_price', 
        'created_at', 'updated_at', 'user', 'status', 'last_contact'
    )
    search_fields = ('familiar_name',)
    readonly_fields = ('device_id', 'created_at', 'updated_at', 'user')  # Users cannot change ownership

    fields = (
        'device_id', 'familiar_name', 'shelly_api_key', 'shelly_device_name', 
        'run_hours_per_day', 'day_transfer_price', 'night_transfer_price', 
        'created_at', 'updated_at', 'user', 'status', 'last_contact'
    )

    ordering = ['-device_id']

    def save_model(self, request, obj, form, change):
        """ Ensure new devices are owned by the user who creates them. """
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """ Limit users to only see their own devices. """
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(user=request.user)

    def get_readonly_fields(self, request, obj=None):
        """ Allow users to modify all fields **except** ownership-related fields. """
        readonly = super().get_readonly_fields(request, obj)
        return readonly if request.user.is_superuser else readonly  # No extra read-only fields needed


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
    list_display = ('user', 'device', 'electricity_price', 'assigned_at')
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
        Ensure users can only:
        - Assign devices they own.
        - Assign themselves (hide other users).
        """
        if db_field.name == "device" and not request.user.is_superuser:
            kwargs["queryset"] = ShellyDevice.objects.filter(user=request.user)

        if db_field.name == "user" and not request.user.is_superuser:
            kwargs["queryset"] = kwargs["queryset"].filter(username=request.user.username)
            return None  # Hide the "user" field (set automatically)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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

admin.site.register(DeviceAssignment, DeviceAssignmentAdmin)
