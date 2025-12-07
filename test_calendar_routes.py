"""
Test script for calendar routes - availability and booking
"""
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional

# Test constants
USER_ID = "691cdc31fb39528053b632d7"
ATTENDEE_EMAIL = "namitjain2111@gmail.com"
ATTENDEE_NAME = "Calendar Test"
BASE_URL = "http://localhost:8000"


async def test_get_availability():
    """Test GET /calendar/availability endpoint"""
    print("\n" + "="*60)
    print("Testing: GET /calendar/availability")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/calendar/availability",
                headers={"X-User-Id": USER_ID},
                params={"days": 14, "timezone": "UTC"}
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success!")
                print(f"Connected: {data.get('connected')}")
                print(f"Event Type ID: {data.get('event_type_id')}")
                print(f"Event Type Name: {data.get('event_type_name')}")
                print(f"Booking Link: {data.get('booking_link')}")
                
                slots = data.get('slots', [])
                print(f"\nAvailable Slots: {len(slots)}")
                
                if slots:
                    print("\nFirst 5 available slots:")
                    for i, slot in enumerate(slots[:5], 1):
                        start = slot.get('start')
                        end = slot.get('end')
                        timezone = slot.get('time_zone', 'UTC')
                        print(f"  {i}. Start: {start} | End: {end} | Timezone: {timezone}")
                    
                    return slots
                else:
                    print("⚠️  No available slots found")
                    return []
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except httpx.TimeoutException:
            print("❌ Request timed out")
            return []
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            return []


async def test_book_meeting(slots: list):
    """Test POST /calendar/book endpoint"""
    print("\n" + "="*60)
    print("Testing: POST /calendar/book")
    print("="*60)
    
    if not slots:
        print("❌ No available slots to book. Skipping booking test.")
        return None
    
    # Use the first available slot
    first_slot = slots[0]
    start_str = first_slot.get('start')
    end_str = first_slot.get('end')
    timezone = first_slot.get('time_zone', 'UTC')
    
    # Parse datetime strings if needed
    if isinstance(start_str, str):
        # Handle ISO format strings
        if start_str.endswith('Z'):
            start_str = start_str.replace('Z', '+00:00')
        start_dt = datetime.fromisoformat(start_str)
    else:
        start_dt = start_str
    
    if isinstance(end_str, str):
        if end_str.endswith('Z'):
            end_str = end_str.replace('Z', '+00:00')
        end_dt = datetime.fromisoformat(end_str)
    else:
        end_dt = end_str
    
    print(f"Booking slot:")
    print(f"  Start: {start_dt.isoformat()}")
    print(f"  End: {end_dt.isoformat()}")
    print(f"  Timezone: {timezone}")
    print(f"  Attendee: {ATTENDEE_NAME} ({ATTENDEE_EMAIL})")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "attendee_email": ATTENDEE_EMAIL,
                "attendee_name": ATTENDEE_NAME,
                "notes": "Test booking from calendar routes test script",
                "time_zone": timezone
            }
            
            response = await client.post(
                f"{BASE_URL}/calendar/book",
                headers={
                    "X-User-Id": USER_ID,
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Booking successful!")
                print(f"Success: {data.get('success')}")
                print(f"Booking ID: {data.get('booking_id')}")
                print(f"Booking URL: {data.get('booking_url')}")
                return data
            else:
                print(f"❌ Booking failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except httpx.TimeoutException:
            print("❌ Request timed out")
            return None
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    """Run all tests"""
    print("="*60)
    print("Calendar Routes Test Script")
    print("="*60)
    print(f"User ID: {USER_ID}")
    print(f"Attendee Email: {ATTENDEE_EMAIL}")
    print(f"Attendee Name: {ATTENDEE_NAME}")
    print(f"Base URL: {BASE_URL}")
    
    # Test 1: Get availability
    slots = await test_get_availability()
    
    # Test 2: Book meeting (only if slots are available)
    if slots:
        booking_result = await test_book_meeting(slots)
    else:
        print("\n⚠️  Skipping booking test - no available slots")
        booking_result = None
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Availability Test: {'✅ Passed' if slots else '❌ Failed/No Slots'}")
    print(f"Booking Test: {'✅ Passed' if booking_result and booking_result.get('success') else '❌ Failed/Skipped'}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

