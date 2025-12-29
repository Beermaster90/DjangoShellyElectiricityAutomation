from django.contrib.auth.models import User
from app.models import DeviceAssignment, ElectricityPrice, ShellyDevice

# Get users
kirsti = User.objects.filter(username='kirsti').first()
eero = User.objects.filter(username='eero').first()

if not kirsti or not eero:
    print("Users not found!")
    print(f"Kirsti: {kirsti}")
    print(f"Eero: {eero}")
else:
    print("=== USERS ===")
    print(f"Kirsti ID: {kirsti.id}")
    print(f"Eero ID: {eero.id}")
    print()
    
    for user in [kirsti, eero]:
        print(f"\n{'='*50}")
        print(f"=== {user.username.upper()} ===")
        print('='*50)
        
        # Get assignments
        assignments = DeviceAssignment.objects.filter(user=user)
        print(f"Total assignments: {assignments.count()}")
        
        # Get unique periods
        unique_prices = assignments.values_list('electricity_price_id', flat=True).distinct()
        print(f"Unique assigned periods: {len(list(unique_prices))}")
        
        if assignments.exists():
            # Calculate average price
            prices = []
            for a in assignments.select_related('electricity_price'):
                prices.append(float(a.electricity_price.price_per_kwh))
            
            avg_price = sum(prices) / len(prices) if prices else 0
            
            # Get date range
            first_assignment = assignments.select_related('electricity_price').order_by('electricity_price__start_time').first()
            last_assignment = assignments.select_related('electricity_price').order_by('-electricity_price__start_time').first()
            
            print(f"Date range: {first_assignment.electricity_price.start_time} to {last_assignment.electricity_price.start_time}")
            print(f"Average spot price: {avg_price:.4f} c/kWh")
            
            # Get device settings
            device = ShellyDevice.objects.filter(user=user).first()
            if device:
                print(f"Day transfer: {device.day_transfer_price} c/kWh")
                print(f"Night transfer: {device.night_transfer_price} c/kWh")
                
                # Calculate with transfer (50/50 day/night assumption)
                day_t = float(device.day_transfer_price)
                night_t = float(device.night_transfer_price)
                avg_transfer = (day_t + night_t) / 2
                avg_with_transfer = avg_price + avg_transfer
                avg_with_vat = avg_with_transfer * 1.255
                
                print(f"Avg spot + transfer: {avg_with_transfer:.4f} c/kWh")
                print(f"Avg with VAT (25.5%): {avg_with_vat:.4f} c/kWh")
                
                # Show price distribution
                print(f"\nPrice distribution (first 10 assignments):")
                for a in assignments.select_related('electricity_price').order_by('electricity_price__start_time')[:10]:
                    price = float(a.electricity_price.price_per_kwh)
                    print(f"  {a.electricity_price.start_time}: {price:.4f} c/kWh")
                
                print(f"\nPrice distribution (sample from middle):")
                mid_start = assignments.count() // 2
                for a in assignments.select_related('electricity_price').order_by('electricity_price__start_time')[mid_start:mid_start+10]:
                    price = float(a.electricity_price.price_per_kwh)
                    print(f"  {a.electricity_price.start_time}: {price:.4f} c/kWh")
