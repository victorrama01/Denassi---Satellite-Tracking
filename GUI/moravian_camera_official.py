"""
Forbedret Moravian Camera Python wrapper baseret på officiel Moravian SDK
Integreret med dit eksisterende teleskopsystem
"""

from __future__ import print_function
import sys, os
import time
import numpy as np
from ctypes import *
from astropy.io import fits
from datetime import datetime

class MoravianCameraOfficial:
    """Forbedret Moravian Camera klasse baseret på officiel SDK"""
    
    def __init__(self, dll_path=None):
        """Initialize Moravian camera
        
        Args:
            dll_path: Path to cXusb.dll (auto-detect if None)
        """
        self.cam_id = None
        self.cam_handle = None
        self.w = None
        self.h = None
        self.bin_x = 1
        self.bin_y = 1
        self.connected = False
        
        # Find DLL path
        if dll_path is None:
            dll_path = self._find_dll()
        
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"Moravian SDK not found: {dll_path}")
        
        # Load DLL
        try:
            self.cxdll = CDLL(dll_path)
            self._init_cdll()
            print(f"✅ Moravian SDK loaded: {dll_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load Moravian SDK: {e}")
        
        # Setup enumeration callback
        self._setup_enumeration()
    
    def _find_dll(self):
        """Find cXusb.dll in common locations"""
        possible_paths = [
            # Same directory as this script
            os.path.join(os.path.dirname(__file__), 'cXusb.dll'),
            # Common installation paths
            r"C:\Program Files\Moravian Instruments\cXusb.dll",
            r"C:\Program Files (x86)\Moravian Instruments\cXusb.dll",
            # Current working directory
            "cXusb.dll"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("cXusb.dll not found. Please install Moravian SDK or specify path.")
    
    def _init_cdll(self):
        """Initialize ctypes parameter types and return values for 64-bit Python"""
        self.cxdll.Initialize.restype = c_void_p
        self.cxdll.Release.argtypes = [c_void_p]
        self.cxdll.GetValue.argtypes = [c_void_p, c_uint32, c_void_p]
        self.cxdll.GetIntegerParameter.argtypes = [c_void_p, c_uint32, c_void_p]
        self.cxdll.GetStringParameter.argtypes = [c_void_p, c_uint32, c_uint32, c_void_p]
        self.cxdll.SetReadMode.argtypes = [c_void_p, c_uint32]
        self.cxdll.StartExposure.argtypes = [c_void_p, c_double, c_ubyte, c_int, c_int, c_int, c_int]
        self.cxdll.ImageReady.argtypes = [c_void_p, c_void_p]
        self.cxdll.ReadImage.argtypes = [c_void_p, c_uint32, c_void_p]
        self.cxdll.ReadImage.restype = c_ubyte
        self.cxdll.SetBinning.argtypes = [c_void_p, c_uint, c_uint]
        self.cxdll.GetLastErrorString.argtypes = [c_void_p, c_uint32, c_void_p]
        
        # Additional functions for temperature control
        try:
            self.cxdll.SetTemperature.argtypes = [c_void_p, c_float]
            self.cxdll.SetTemperature.restype = c_ubyte
        except:
            print("⚠️ Temperature control not available")
        
        try:
            self.cxdll.Open.argtypes = [c_void_p]
            self.cxdll.Open.restype = c_ubyte
            self.cxdll.Close.argtypes = [c_void_p]
            self.cxdll.Close.restype = c_ubyte
        except:
            print("⚠️ Open/Close functions not available")
        
        # Gain control functions
        try:
            self.cxdll.SetGain.argtypes = [c_void_p, c_uint]
            self.cxdll.SetGain.restype = c_ubyte
            self.cxdll.ConvertGain.argtypes = [c_void_p, c_uint, POINTER(c_double), POINTER(c_double)]
            self.cxdll.ConvertGain.restype = c_ubyte
        except:
            print("⚠️ Gain control not available")
        
        # Filter wheel functions
        try:
            self.cxdll.SetFilter.argtypes = [c_void_p, c_uint]
            self.cxdll.SetFilter.restype = c_ubyte
            self.cxdll.ReinitFilterWheel.argtypes = [c_void_p]
            self.cxdll.ReinitFilterWheel.restype = c_ubyte
            self.cxdll.EnumerateFilters.argtypes = [c_void_p, c_uint, c_uint, c_char_p, POINTER(c_uint)]
            self.cxdll.EnumerateFilters.restype = c_ubyte
            self.cxdll.EnumerateFilters2.argtypes = [c_void_p, c_uint, c_uint, c_char_p, POINTER(c_uint), POINTER(c_int)]
            self.cxdll.EnumerateFilters2.restype = c_ubyte
        except:
            print("⚠️ Filter wheel control not available")
        
        # Abort exposure function
        try:
            self.cxdll.AbortExposure.argtypes = [c_void_p, c_ubyte]
            self.cxdll.AbortExposure.restype = c_ubyte
        except:
            print("⚠️ Abort exposure not available")
    
    def _setup_enumeration(self):
        """Setup camera enumeration callback"""
        def py_enum_proc(c_id):
            self.cam_id = c_id
            print(f'Found camera ID: {self.cam_id}')
        
        self.ENUMPROC = CFUNCTYPE(None, c_uint)
        self.enum_proc = self.ENUMPROC(py_enum_proc)
    
    def enumerate_cameras(self):
        """Find available cameras
        
        Returns:
            int: Camera ID if found, None otherwise
        """
        print("Searching for Moravian cameras...")
        self.cxdll.Enumerate(self.enum_proc)
        if self.cam_id is not None:
            print(f"✅ Found camera with ID: {self.cam_id}")
        else:
            print("❌ No cameras found")
        return self.cam_id
    
    def connect(self, camera_id=None):
        """Connect to camera
        
        Args:
            camera_id: Specific camera ID (uses first found if None)
        
        Returns:
            bool: True if successful
        """
        try:
            # Use provided ID or find cameras
            if camera_id is not None:
                self.cam_id = camera_id
            elif self.cam_id is None:
                self.enumerate_cameras()
            
            if self.cam_id is None:
                raise RuntimeError("No camera ID available")
            
            # Initialize camera
            self.cam_handle = self.cxdll.Initialize(self.cam_id)
            if not self.cam_handle:
                raise RuntimeError("Failed to initialize camera")
            
            # Try to open camera if function exists
            try:
                if not self.cxdll.Open(self.cam_handle):
                    print("⚠️ Open function failed, but continuing...")
            except:
                pass  # Open function might not exist in all versions
            
            # Get camera parameters
            self.w = self.get_integer_parameter(1)  # gipChipW
            self.h = self.get_integer_parameter(2)  # gipChipD
            desc = self.get_string_parameter(0)     # gspCameraDescription
            
            print(f'✅ Connected to: {desc.strip()}')
            print(f'CCD size: {self.w} x {self.h} pixels')
            
            # Get temperature
            try:
                chip_temp = self.get_value(0)  # gvChipTemperature
                print(f'Current temperature: {chip_temp:.1f}°C')
            except:
                print("⚠️ Temperature reading not available")
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from camera"""
        if self.initialized():
            try:
                # Close camera if function exists
                if hasattr(self.cxdll, 'Close'):
                    self.cxdll.Close(self.cam_handle)
            except:
                pass
            
            self.cxdll.Release(self.cam_handle)
            self.cam_handle = None
            self.connected = False
            print("✅ Camera disconnected")
    
    def initialized(self):
        """Check if camera is initialized"""
        return self.cam_handle is not None
    
    def get_value(self, value_index):
        """Get floating point value from camera"""
        if self.initialized():
            v = c_float(-1.0)
            self.cxdll.GetValue(self.cam_handle, value_index, byref(v))
            return v.value
        return -1.0
    
    def get_integer_parameter(self, param_index):
        """Get integer parameter from camera"""
        if self.initialized():
            v = c_int32()
            self.cxdll.GetIntegerParameter(self.cam_handle, param_index, byref(v))
            return v.value
        return -1
    
    def get_string_parameter(self, param_index):
        """Get string parameter from camera"""
        if self.initialized():
            buf = create_string_buffer(128)
            self.cxdll.GetStringParameter(self.cam_handle, param_index, sizeof(buf) - 1, buf)
            return buf.value.decode('utf-8')
        return ''
    
    def set_binning(self, bin_x, bin_y):
        """Set camera binning
        
        Args:
            bin_x: X binning factor
            bin_y: Y binning factor
        """
        if self.initialized():
            self.bin_x = bin_x
            self.bin_y = bin_y
            self.cxdll.SetBinning(self.cam_handle, bin_x, bin_y)
            print(f"Binning set to: {bin_x} x {bin_y}")
    
    def set_temperature(self, temperature):
        """Set camera temperature
        
        Args:
            temperature: Target temperature in Celsius
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        try:
            result = self.cxdll.SetTemperature(self.cam_handle, c_float(temperature))
            if result:
                print(f"Target temperature set to: {temperature}°C")
                return True
            else:
                print(f"Failed to set temperature to {temperature}°C")
                return False
        except Exception as e:
            print(f"Temperature control not available: {e}")
            return False
    
    def get_temperature(self):
        """Get current camera temperature"""
        return self.get_value(0)  # gvChipTemperature
    
    def set_gain(self, gain):
        """Set camera gain
        
        Args:
            gain: Gain value (0 to max_gain)
            
        Returns:
            bool: True if successful
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        try:
            # Check max gain
            max_gain = self.get_integer_parameter(16)  # gipMaxGain
            if gain < 0 or gain > max_gain:
                raise ValueError(f"Gain {gain} out of range (0-{max_gain})")
            
            result = self.cxdll.SetGain(self.cam_handle, c_uint(gain))
            if result:
                print(f"Gain set to: {gain}")
                return True
            else:
                print(f"Failed to set gain to {gain}")
                return False
        except Exception as e:
            print(f"Gain control not available: {e}")
            return False
    
    def get_gain(self):
        """Get current camera gain
        
        Returns:
            float: Current gain value
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        return self.get_value(20)  # gvADCGain
    
    def get_max_gain(self):
        """Get maximum allowed gain
        
        Returns:
            int: Maximum gain value
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        return self.get_integer_parameter(16)  # gipMaxGain
    
    def convert_gain(self, gain):
        """Convert gain value to dB and multiplication factor
        
        Args:
            gain: Gain value to convert
            
        Returns:
            tuple: (gain_db, gain_times) or None if failed
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        try:
            gain_db = c_double()
            gain_times = c_double()
            
            result = self.cxdll.ConvertGain(self.cam_handle, c_uint(gain), 
                                          byref(gain_db), byref(gain_times))
            
            if result:
                return (gain_db.value, gain_times.value)
            else:
                return None
                
        except Exception as e:
            print(f"Gain conversion failed: {e}")
            return None
    
    def get_filter_count(self):
        """Get number of filters in filter wheel
        
        Returns:
            int: Number of filters, or 0 if no filter wheel
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        return self.get_integer_parameter(8)  # gipFilters
    
    def enumerate_filters(self):
        """Get list of all available filters
        
        Returns:
            list: List of tuples [(name, color), ...] or empty list if no filters
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        filters = []
        filter_count = self.get_filter_count()
        
        if filter_count == 0:
            return filters
        
        try:
            for i in range(filter_count):
                # Use EnumerateFilters2 for more detailed info
                desc_buffer = create_string_buffer(128)
                color = c_uint()
                offset = c_int()
                
                result = self.cxdll.EnumerateFilters2(
                    self.cam_handle, 
                    c_uint(i), 
                    c_uint(127),  # buffer size - 1
                    desc_buffer, 
                    byref(color), 
                    byref(offset)
                )
                
                if result:
                    filter_name = desc_buffer.value.decode('utf-8').strip()
                    filters.append({
                        'index': i,
                        'name': filter_name,
                        'color': color.value,
                        'offset': offset.value
                    })
                else:
                    # Fallback to basic EnumerateFilters
                    result = self.cxdll.EnumerateFilters(
                        self.cam_handle, 
                        c_uint(i), 
                        c_uint(127), 
                        desc_buffer, 
                        byref(color)
                    )
                    
                    if result:
                        filter_name = desc_buffer.value.decode('utf-8').strip()
                        filters.append({
                            'index': i,
                            'name': filter_name,
                            'color': color.value,
                            'offset': 0
                        })
            
            return filters
            
        except Exception as e:
            print(f"Filter enumeration failed: {e}")
            return []
    
    def set_filter(self, filter_index):
        """Set current filter position
        
        Args:
            filter_index: Filter position (0-based)
            
        Returns:
            bool: True if successful
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        filter_count = self.get_filter_count()
        if filter_count == 0:
            print("No filter wheel detected")
            return False
        
        if filter_index < 0 or filter_index >= filter_count:
            raise ValueError(f"Filter index {filter_index} out of range (0-{filter_count-1})")
        
        try:
            result = self.cxdll.SetFilter(self.cam_handle, c_uint(filter_index))
            if result:
                print(f"Filter set to position: {filter_index}")
                return True
            else:
                print(f"Failed to set filter to position {filter_index}")
                return False
                
        except Exception as e:
            print(f"Filter control failed: {e}")
            return False
    
    def reinit_filter_wheel(self):
        """Reinitialize filter wheel (home/calibrate)
        
        Returns:
            bool: True if successful
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        try:
            result = self.cxdll.ReinitFilterWheel(self.cam_handle)
            if result:
                print("Filter wheel reinitialized")
                return True
            else:
                print("Failed to reinitialize filter wheel")
                return False
                
        except Exception as e:
            print(f"Filter wheel reinit failed: {e}")
            return False
    
    def abort_exposure(self, download=False):
        """Abort current exposure
        
        Args:
            download: Whether to download partial image
            
        Returns:
            bool: True if successful
        """
        if not self.initialized():
            return False
        
        try:
            result = self.cxdll.AbortExposure(self.cam_handle, c_ubyte(1 if download else 0))
            if result:
                print("Exposure aborted")
                return True
            else:
                print("Failed to abort exposure")
                return False
                
        except Exception as e:
            print(f"Abort exposure failed: {e}")
            return False
    
    def image_ready(self):
        """Check if image is ready for download"""
        if self.initialized():
            v = c_bool(False)
            self.cxdll.ImageReady(self.cam_handle, byref(v))
            return v.value
        return False
    
    def get_camera_info(self):
        """Get comprehensive camera information"""
        if not self.initialized():
            return {}
        
        info = {
            'description': self.get_string_parameter(0),  # gspCameraDescription
            'manufacturer': self.get_string_parameter(1),  # gspManufacturer
            'serial': self.get_string_parameter(2),  # gspCameraSerial
            'chip_description': self.get_string_parameter(3),  # gspChipDescription
            'width': self.w,
            'height': self.h,
            'binning_x': self.bin_x,
            'binning_y': self.bin_y,
            'temperature': self.get_temperature(),
        }
        
        # Physical parameters
        try:
            info['pixel_width'] = self.get_integer_parameter(3) / 1000.0  # gipPixelW in nm -> µm
            info['pixel_height'] = self.get_integer_parameter(4) / 1000.0  # gipPixelD in nm -> µm
            info['max_binning_x'] = self.get_integer_parameter(5)  # gipMaxBinningX
            info['max_binning_y'] = self.get_integer_parameter(6)  # gipMaxBinningY
        except:
            pass
        
        # Gain information
        try:
            info['current_gain'] = self.get_gain()
            info['max_gain'] = self.get_max_gain()
            
            # Convert current gain to dB/times if possible
            gain_conversion = self.convert_gain(int(info['current_gain']))
            if gain_conversion:
                info['gain_db'] = gain_conversion[0]
                info['gain_times'] = gain_conversion[1]
        except:
            pass
        
        # Filter wheel information
        try:
            info['filter_count'] = self.get_filter_count()
            if info['filter_count'] > 0:
                info['filters'] = self.enumerate_filters()
        except:
            pass
        
        # Firmware/driver version
        try:
            info['firmware_major'] = self.get_integer_parameter(128)  # gipFirmwareMajor
            info['firmware_minor'] = self.get_integer_parameter(129)  # gipFirmwareMinor
            info['firmware_build'] = self.get_integer_parameter(130)  # gipFirmwareBuild
            info['driver_major'] = self.get_integer_parameter(131)    # gipDriverMajor
            info['driver_minor'] = self.get_integer_parameter(132)    # gipDriverMinor
            info['driver_build'] = self.get_integer_parameter(133)    # gipDriverBuild
        except:
            pass
        
        # Exposure limits
        try:
            info['min_exposure'] = self.get_integer_parameter(9)   # gipMinimalExposure (microseconds)
            info['max_exposure'] = self.get_integer_parameter(10)  # gipMaximalExposure (microseconds)
        except:
            pass
        
        # Boolean capabilities
        try:
            capabilities = {}
            # Check various camera capabilities
            capability_checks = {
                'cooler': 4,      # gbpCooler
                'shutter': 3,     # gbpShutter
                'filters': 6,     # gbpFilters
                'guide': 7,       # gbpGuide
                'gain': 13,       # gbpGain
                'gps': 16,        # gbpGPS
            }
            
            for name, index in capability_checks.items():
                try:
                    value = c_bool()
                    if self.cxdll.GetBooleanParameter(self.cam_handle, index, byref(value)):
                        capabilities[name] = value.value
                except:
                    capabilities[name] = False
            
            info['capabilities'] = capabilities
        except:
            pass
        
        return info
    
    def start_exposure(self, exp_time, use_shutter=True, x=0, y=0, width=None, height=None):
        """Start camera exposure
        
        Args:
            exp_time: Exposure time in seconds
            use_shutter: Whether to use shutter (True for light, False for dark)
            x, y: Starting coordinates for subframe
            width, height: Subframe dimensions (full chip if None)
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        # Calculate binned dimensions
        w = width or int(self.w / self.bin_x)
        h = height or int(self.h / self.bin_y)
        
        # Set read mode (0 = normal)
        self.cxdll.SetReadMode(self.cam_handle, 0)
        
        # Start exposure
        shutter = 1 if use_shutter else 0
        success = self.cxdll.StartExposure(self.cam_handle, c_double(exp_time), 
                                          shutter, x, y, w, h)
        
        if not success:
            error = self.get_last_error()
            raise RuntimeError(f"Failed to start exposure: {error}")
        
        print(f"Started {exp_time}s exposure ({w}x{h} pixels)")
        return True
    
    def wait_for_image(self, timeout=300):
        """Wait for image to be ready
        
        Args:
            timeout: Maximum wait time in seconds
        """
        start_time = time.time()
        while not self.image_ready():
            if time.time() - start_time > timeout:
                raise RuntimeError(f"Timeout waiting for image ({timeout}s)")
            time.sleep(0.01)
    
    def read_image(self):
        """Read image data from camera
        
        Returns:
            numpy.ndarray: Image data as 2D array
        """
        if not self.initialized():
            raise RuntimeError("Camera not connected")
        
        # Calculate image dimensions
        w = int(self.w / self.bin_x)
        h = int(self.h / self.bin_y)
        
        # Create buffer for 16-bit image
        buffer_size = w * h * 2  # 2 bytes per pixel for 16-bit
        p_image = create_string_buffer(buffer_size)
        
        # Read image
        result = self.cxdll.ReadImage(self.cam_handle, sizeof(p_image), p_image)
        
        if not result:
            error = self.get_last_error()
            raise RuntimeError(f"Failed to read image: {error}")
        
        # Convert to numpy array
        image_data = np.frombuffer(p_image.raw, dtype=np.uint16)
        image_data = image_data.reshape((h, w))
        
        print(f"Image read successfully: {w}x{h} pixels")
        return image_data
    
    def get_last_error(self):
        """Get last error message"""
        if self.initialized():
            p_error = create_string_buffer(2048)
            self.cxdll.GetLastErrorString(self.cam_handle, sizeof(p_error) - 1, p_error)
            return p_error.value.decode('utf-8')
        return "Camera not initialized"
    
    def take_image(self, exp_time, use_shutter=True, timeout=300):
        """Take a complete image (start, wait, read)
        
        Args:
            exp_time: Exposure time in seconds
            use_shutter: Whether to use shutter
            timeout: Maximum wait time
        
        Returns:
            numpy.ndarray: Image data
        """
        self.start_exposure(exp_time, use_shutter)
        
        # Wait for exposure plus readout time
        exposure_start = time.time()
        
        # Sleep for most of exposure time
        if exp_time > 0.5:
            time.sleep(exp_time - 0.2)  # Wake up slightly before expected completion
        
        self.wait_for_image(timeout)
        
        image_data = self.read_image()
        
        total_time = time.time() - exposure_start
        print(f"Total acquisition time: {total_time:.1f}s")
        
        return image_data
    
    def save_fits(self, image_data, filename, exp_time=None, image_type='Light'):
        """Save image as FITS file with proper headers
        
        Args:
            image_data: numpy array with image data
            filename: Output filename
            exp_time: Exposure time for header
            image_type: Type of image for header
        """
        # Create FITS header
        header = fits.Header()
        
        # Basic image info
        if exp_time is not None:
            header['EXPTIME'] = (exp_time, 'Exposure time in seconds')
        header['IMAGETYP'] = (image_type, 'Type of image')
        header['DATE-OBS'] = (datetime.utcnow().isoformat(), 'UTC observation start')
        
        # Camera info
        info = self.get_camera_info()
        header['INSTRUME'] = (info.get('description', 'Moravian Camera'), 'Camera model')
        header['XBINNING'] = (self.bin_x, 'X binning factor')
        header['YBINNING'] = (self.bin_y, 'Y binning factor')
        
        if 'temperature' in info:
            header['CCD-TEMP'] = (info['temperature'], 'CCD temperature in Celsius')
        
        if 'pixel_width' in info:
            header['XPIXSZ'] = (info['pixel_width'] * self.bin_x, 'X pixel size in micrometers')
            header['YPIXSZ'] = (info['pixel_height'] * self.bin_y, 'Y pixel size in micrometers')
        
        # Save FITS file
        hdu = fits.PrimaryHDU(image_data, header=header)
        hdu.writeto(filename, overwrite=True)
        print(f"✅ Saved: {filename}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Example usage and integration
if __name__ == "__main__":
    try:
        print("=== Moravian Camera Advanced Test ===")
        
        # Create camera instance
        camera = MoravianCameraOfficial()
        
        # Connect to camera
        if camera.connect():
            # Get comprehensive camera info
            info = camera.get_camera_info()
            print("\n=== Camera Information ===")
            for key, value in info.items():
                if key == 'filters' and isinstance(value, list):
                    print(f"  {key}:")
                    for i, filter_info in enumerate(value):
                        print(f"    [{i}] {filter_info}")
                elif key == 'capabilities' and isinstance(value, dict):
                    print(f"  {key}:")
                    for cap, enabled in value.items():
                        print(f"    {cap}: {'✅' if enabled else '❌'}")
                else:
                    print(f"  {key}: {value}")
            
            # Test gain control if available
            if info.get('capabilities', {}).get('gain', False):
                print(f"\n=== Gain Control Test ===")
                max_gain = camera.get_max_gain()
                current_gain = camera.get_gain()
                print(f"Current gain: {current_gain}")
                print(f"Max gain: {max_gain}")
                
                # Test gain conversion
                for test_gain in [0, max_gain//2, max_gain]:
                    conversion = camera.convert_gain(test_gain)
                    if conversion:
                        db, times = conversion
                        print(f"Gain {test_gain}: {db:.1f} dB, {times:.1f}x")
                
                # Set medium gain for imaging
                if max_gain > 0:
                    medium_gain = max_gain // 2
                    camera.set_gain(medium_gain)
                    print(f"Set gain to: {medium_gain}")
            
            # Test filter wheel if available
            if info.get('filter_count', 0) > 0:
                print(f"\n=== Filter Wheel Test ===")
                filters = camera.enumerate_filters()
                print(f"Available filters ({len(filters)}):")
                for f in filters:
                    print(f"  [{f['index']}] {f['name']} (Color: {f['color']}, Offset: {f['offset']})")
                
                # Test filter selection
                if len(filters) > 0:
                    print("Testing filter selection...")
                    camera.set_filter(0)  # Move to first filter
                    time.sleep(2)  # Wait for filter change
            
            # Set camera parameters
            camera.set_binning(2, 2)  # 2x2 binning
            camera.set_temperature(-10.0)  # Cool to -10°C
            
            # Take test image
            print("\n=== Taking Test Image ===")
            print("Starting 3-second exposure...")
            image = camera.take_image(3.0, use_shutter=True)
            
            # Save image with all metadata
            filename = f"moravian_advanced_test_{int(time.time())}.fits"
            camera.save_fits(image, filename, exp_time=3.0)
            
            print(f"\n✅ Advanced test completed!")
            print(f"Image shape: {image.shape}")
            print(f"Image statistics: min={image.min()}, max={image.max()}, mean={image.mean():.1f}")
            print(f"Image saved: {filename}")
        
        else:
            print("❌ Failed to connect to camera")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        camera.disconnect()