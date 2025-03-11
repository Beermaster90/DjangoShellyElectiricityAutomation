from django.contrib import admin
from .models import ShellyDevice, ElectricityPrice, DeviceAssignment

class ShellyDeviceAdmin(admin.ModelAdmin):
    list_display = (
        'device_id', 'familiar_name', 'shelly_api_key', 'shelly_device_name', 
        'run_hours_per_day', 'day_transfer_price', 'night_transfer_price', 
        'created_at', 'updated_at', 'user', 'status', 'last_contact'
    )
    search_fields = ('familiar_name',)
    readonly_fields = ('device_id', 'created_at', 'updated_at', 'user')
    
    # Fields to display in the form view
    fields = (
        'device_id', 'familiar_name', 'shelly_api_key', 'shelly_device_name', 
        'run_hours_per_day', 'day_transfer_price', 'night_transfer_price', 
        'created_at', 'updated_at', 'user', 'status', 'last_contact'
    )

    # Order Shelly devices descending by device_id
    ordering = ['-device_id']

    # Override save_model to set the current user as the owner
    def save_model(self, request, obj, form, change):
        if not change:  # Only set the user when creating a new object
            obj.user = request.user
        super().save_model(request, obj, form, change)

    # Override the get_queryset method to limit visible devices
    # Hide fields for everyone except superusers and specific groups
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)

        # Default hidden fields (replace values with asterisk '*')
        hidden_fields = ['shelly_api_key', 'day_transfer_price', 'night_transfer_price']

        if request.user.is_superuser:
            return fields  # Superusers see everything

        # If user is part of the 'commoners' group, allow visibility
        if request.user.groups.filter(name='commoners').exists():
            return fields  # Commoners see everything

        # Hide specific fields by replacing them with '*' (or omit them altogether)
        visible_fields = [f if f not in hidden_fields else '*' for f in fields]
        
        return visible_fields

    # Filter the queryset to show only the devices the user owns
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs  # Superusers should see all devices

        # Filter for 'commoners' or other users to show only their devices
        if request.user.groups.filter(name='commoners').exists():
            return qs  # Commoners see all devices

        return qs.filter(user=request.user)  # Other users see only their own devices

    # Override save_model to set the current user as the owner when creating a new device
    def save_model(self, request, obj, form, change):
        if not change:  # If it's a new object, set the current user as the owner
            obj.user = request.user
        super().save_model(request, obj, form, change)
    
    # Optionally, hide specific fields from being editable by non-superusers
    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)

        if request.user.is_superuser:
            return readonly  # Superusers have no additional read-only fields

        if request.user.groups.filter(name='commoners').exists():
            return readonly  # Commoners can edit all fields

        # Add fields to read-only for other users (if needed)
        return readonly + ('shelly_api_key', 'day_transfer_price', 'night_transfer_price')


# Register the ShellyDevice model with the updated admin class
admin.site.register(ShellyDevice, ShellyDeviceAdmin)

@admin.register(ElectricityPrice)
class ElectricityPriceAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time', 'price_kwh', 'created_at')  # Columns to display in the admin list
    search_fields = ('start_time', 'end_time')  # Allow searching by these fields
    list_filter = ('start_time', 'end_time')  # Filters for narrowing down records
    ordering = ('-start_time',)  # Order by start time, descending
    readonly_fields = ('created_at',)  # Make created_at field read-only

class DeviceAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'electricity_price', 'assigned_at')  # Columns to display in the admin list
    search_fields = ('user__username', 'device__familiar_name', 'electricity_price__start_time')  # Allow searching by these fields
    list_filter = ('user', 'device', 'electricity_price__start_time')  # Filters for narrowing down records
    ordering = ('-assigned_at',)  # Show most recent assignments first
    readonly_fields = ('assigned_at',)  # Prevent modification of assigned timestamps

    def get_queryset(self, request):
        """
        Restrict the queryset so normal users only see their own assignments.
        Superusers can see all assignments.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Superusers see all assignments
        return qs.filter(user=request.user)  # Normal users only see their own device assignments

# Register the DeviceAssignment model with the custom admin view
admin.site.register(DeviceAssignment, DeviceAssignmentAdmin)
