"""
Test script for measuring camera filter switch time
"""

import time
from moravian_camera_official import MoravianCameraOfficial

def test_filter_switch_time(num_switches=10):
    """
    Test how long it takes to switch filters on the camera
    
    Args:
        num_switches: Number of filter switches to test
    """
    
    print("=" * 60)
    print("CAMERA FILTER SWITCH TIME TEST")
    print("=" * 60)
    
    try:
        # Connect to camera
        print("\nConnecting to camera...")
        camera = MoravianCameraOfficial()
        camera.connect()
        print("✓ Camera connected")
        
        # Get number of filters
        n_filters = camera.get_filter_count()
        print(f"✓ Number of filters: {n_filters}")
        
        if n_filters < 2:
            print("✗ Camera has less than 2 filters - cannot test switching")
            camera.disconnect()
            return
        
        # Get filter names
        filter_names = camera.enumerate_filters()
        print(f"✓ Filter names: {filter_names}")
        
        # Test filter switching
        print(f"\nTesting {num_switches} filter switches...")
        print("-" * 60)
        
        switch_times = []
        
        for i in range(num_switches):
            # Switch between filter 0 and 1
            current_filter = i % n_filters
            next_filter = (i + 1) % n_filters
            
            # Measure time for switch
            start_time = time.time()
            camera.set_filter(next_filter)
            end_time = time.time()
            
            elapsed = end_time - start_time
            switch_times.append(elapsed)
            
            print(f"Switch {i+1:2d}: Filter {current_filter} → {next_filter} | Time: {elapsed:.4f} sec")
        
        # Calculate statistics
        print("-" * 60)
        print("\nSTATISTICS:")
        print(f"Min time:  {min(switch_times):.4f} sec")
        print(f"Max time:  {max(switch_times):.4f} sec")
        print(f"Avg time:  {sum(switch_times)/len(switch_times):.4f} sec")
        print(f"Total time: {sum(switch_times):.2f} sec")
        
        # Disconnect
        camera.disconnect()
        print("\n✓ Camera disconnected")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run test with 10 switches (default)
    test_filter_switch_time(num_switches=10)
    
    # Uncomment to test with more switches
    # test_filter_switch_time(num_switches=20)
