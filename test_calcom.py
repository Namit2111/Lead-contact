"""
Test script for Cal.com integration
Run this to test calendar availability and booking functionality
"""
import asyncio
import httpx
from datetime import datetime, timedelta
from integrations.calcom_client import CalComClient


async def test_calcom_integration():
    """Test Cal.com API integration"""
    
    # Get API key from user
    api_key = input("Enter your Cal.com API key: ").strip()
    if not api_key:
        print("❌ API key required")
        return
    
    print("\n🔍 Testing Cal.com connection...")
    
    try:
        client = CalComClient(api_key)
        
        # Test 1: Get user info
        print("\n1️⃣ Testing: Get user info...")
        user_info = await client.get_me()
        print(f"✅ Connected as: {user_info.get('username')} ({user_info.get('email')})")
        
        # Test 2: Get event types
        print("\n2️⃣ Testing: Get event types...")
        event_types = await client.get_event_types()
        print(f"✅ Found {len(event_types)} event types:")
        for et in event_types:
            title = et.get("title") or et.get("name")
            duration = et.get("length") or et.get("duration")
            slug = et.get("slug") or et.get("slugPath")
            print(f"   - {title} ({duration} min) - ID: {et.get('id')}, Slug: {slug}")
        
        if not event_types:
            print("❌ No event types found. Please create an event type in Cal.com first.")
            return
        
        # Select first event type
        selected_type = event_types[0]
        event_type_id = selected_type.get('id')
        print(f"\n📅 Using event type: {(selected_type.get('title') or selected_type.get('name'))} (ID: {event_type_id})")
        
        # Test 3: Get availability
        print("\n3️⃣ Testing: Get availability (next 7 days)...")
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=7)
        
        slots = await client.get_availability(
            event_type_id=event_type_id,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ Found {len(slots)} available slots:")
        for i, slot in enumerate(slots[:10], 1):  # Show first 10
            if isinstance(slot, dict):
                start = slot.get("start") or slot.get("time")
                end = slot.get("end") or slot.get("endTime")
                print(f"   {i}. {start} - {end}")
        
        if len(slots) > 10:
            print(f"   ... and {len(slots) - 10} more slots")
        
        # Test 4: Book a meeting (optional - commented out to avoid accidental bookings)
        print("\n4️⃣ Testing: Booking capability...")
        print("   ⚠️  Skipping actual booking to avoid accidental meetings")
        print("   💡 To test booking, uncomment the code below and provide test details")
        
        # Uncomment below to test actual booking:
        """
        if slots:
            first_slot = slots[0]
            # Parse slot time
            slot_time = datetime.fromisoformat(f"{first_slot['date']}T{first_slot['time']}")
            end_time = slot_time + timedelta(minutes=selected_type.get('length', 30))
            
            booking = await client.create_booking(
                event_type_id=event_type_id,
                start_time=slot_time,
                end_time=end_time,
                attendee_email="test@example.com",
                attendee_name="Test User",
                notes="Test booking from integration script"
            )
            print(f"✅ Meeting booked! Booking ID: {booking.get('id')}")
        """
        
        print("\n✅ All tests passed! Cal.com integration is working correctly.")
        print(f"\n📝 Summary:")
        print(f"   - Username: {user_info.get('username')}")
        print(f"   - Event Types: {len(event_types)}")
        print(f"   - Available Slots (next 7 days): {len(slots)}")
        print(f"   - Booking Link: https://cal.com/{user_info.get('username')}/{selected_type.get('slug')}")
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_backend_endpoints():
    """Test backend API endpoints"""
    print("\n" + "="*60)
    print("Testing Backend API Endpoints")
    print("="*60)
    
    base_url = "http://localhost:8000"
    user_id = input("\nEnter your user ID: ").strip()
    
    if not user_id:
        print("❌ User ID required")
        return
    
    async with httpx.AsyncClient() as client:
        # Test calendar status
        print("\n1️⃣ Testing: GET /calendar/status")
        response = await client.get(
            f"{base_url}/calendar/status",
            headers={"X-User-Id": user_id}
        )
        print(f"   Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"   Connected: {data.get('connected')}")
            if data.get('connected'):
                print(f"   Username: {data.get('username')}")
                print(f"   Event Type: {data.get('event_type_name')}")
        
        # Test internal availability endpoint
        print("\n2️⃣ Testing: GET /internal/calendar-availability/{user_id}")
        response = await client.get(
            f"{base_url}/internal/calendar-availability/{user_id}"
        )
        print(f"   Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"   Connected: {data.get('connected')}")
            if data.get('connected'):
                slots = data.get('available_slots', [])
                print(f"   Available Slots: {len(slots)}")
                print(f"   Booking Link: {data.get('booking_link')}")
                if slots:
                    print(f"   First 3 slots:")
                    for slot in slots[:3]:
                        print(f"     - {slot.get('date')} at {slot.get('time')}")


if __name__ == "__main__":
    print("="*60)
    print("Cal.com Integration Test Script")
    print("="*60)
    print("\nChoose test mode:")
    print("1. Test Cal.com API directly")
    print("2. Test Backend API endpoints")
    print("3. Both")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        asyncio.run(test_calcom_integration())
    elif choice == "2":
        asyncio.run(test_backend_endpoints())
    elif choice == "3":
        asyncio.run(test_calcom_integration())
        asyncio.run(test_backend_endpoints())
    else:
        print("Invalid choice")

