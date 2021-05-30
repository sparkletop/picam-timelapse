from time import sleep
from picamera import PiCamera
# import RPi.GPIO as GPIO
from datetime import datetime
import os, yaml, math, time

HOME_DIR = '/home/pi'
USB_DIR = '/mnt'
USB_DEVICE = '/dev/sda1'
DEFAULT_CONFIG_FILE_NAME = 'timelapse_config.yaml'

# Todo: Ability to use different config files via command line arguments
# Todo: Port os.system to subprocess
# Todo: add support for Camera Module v1
# Todo: Port led controls to RPi.GPIO (so that the filesystem on the pi can be readonly)
# https://raspberrypi.stackexchange.com/questions/697/how-do-i-control-the-system-leds-using-my-software

def run_in_bash(command):
    os.system(f"bash -c '{command}'")

def mount_usb_drive():
    """Mount attached USB device and flash onboard led"""
    led_flash(0)
    run_in_bash(f"sudo mount -o uid=1000,gid=1000 {USB_DEVICE} {USB_DIR}")
    
def unmount_usb_drive():
    """Unmount attached USB device and flash onboard led"""
    run_in_bash(f"sudo umount {USB_DEVICE}")
    led_flash(1)


def led_flash(final_state=1):
    """Flash the pi's onboard LED to indicate read/write activity"""
    for _ in range(5):
        for i in range(2):
            run_in_bash(f"echo {i} | sudo tee /sys/class/leds/led0/brightness > /dev/null 2>&1")
            sleep(0.05)
    
    run_in_bash(f"echo {final_state} | sudo tee /sys/class/leds/led0/brightness > /dev/null 2>&1")

def init_cam(width=1024, height=768, iso=100, shutter_speed='auto', shutter_speed_fixed=True, rotation=0):
    """Returns an initialized instance of PiCamera with the desired settings applied"""
    
    camera = PiCamera()

    # Basic camera config
    camera.resolution = (width, height)
    camera.iso = iso
    camera.rotation = rotation

    # Let camera adjust exposure and white balance
    camera.start_preview()
    sleep(5)
    
    # Autoadjust the white balance
    awb = camera.awb_gains
    camera.awb_mode = 'off'
    camera.awb_gains = awb

    # Adjust shutter speed (in microseconds!)
    camera.shutter_speed = camera.exposure_speed if shutter_speed == 'auto' else shutter_speed * 1000000
    
    if shutter_speed_fixed:
        camera.exposure_mode = 'off'

    camera.stop_preview()

    # Log camera settings to log file
    print("Camera initialised with these settings:", {
        'resolution': camera.resolution,
        'shutter speed': camera.shutter_speed,
        'iso': camera.iso,
        'exposure mode': camera.exposure_mode,
        'white balance auto mode': camera.awb_mode,
        'white balance': camera.awb_gains,
    })

    run_in_bash('echo gpio | sudo tee /sys/class/leds/led0/trigger > /dev/null 2>&1')

    return camera

def capture_sequence(camera, interval, num_captures, sequence_dir, num_digits, format, jpeg_quality):
    """Main timelapse capture loop"""
    
    capture_num = 0

    print("Starting timelapse capture loop")

    first_capture_timestamp = datetime.now()
    
    while capture_num < num_captures:
        
        start = time.time()
        mount_usb_drive()

        capture_num_zero_padded = str(capture_num).zfill(num_digits)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H.%M.%S')

        target_path = os.path.join(
            sequence_dir,
            f"img_{capture_num_zero_padded}_{timestamp}.{format}"
            )
        
        camera.capture(target_path, format, quality=jpeg_quality)

        # Todo: Write summary (so far) to log file
        # This should overwrite existing log file for current sequence
        print(f"Capture number {capture_num} done")
        print({
            'begin time': first_capture_timestamp,
            'end time': timestamp,
            'number of captures': capture_num,
            'sequence finished': not capture_num < num_captures
        })

        unmount_usb_drive()
        capture_num += 1

        end = time.time()
        sleep(interval - (end - start))

if __name__ == "__main__":
    """Capture a timelapse image sequence with the Raspberry Pi Camera Module"""

    mount_usb_drive()

    custom_config = os.path.join(USB_DIR, DEFAULT_CONFIG_FILE_NAME)
    
    config_file = custom_config if os.path.exists(custom_config) else os.path.join(HOME_DIR, DEFAULT_CONFIG_FILE_NAME)
    
    with open(config_file) as data:
        config = yaml.safe_load(data)

    sleep(config['timelapse']['initial_wait_time'])
    
    seq_start_time = datetime.now().strftime('%Y-%m-%d_%H.%M')
    
    sequence_dir = os.path.join(USB_DIR, config['timelapse']['sequence_name'] + '_' + seq_start_time)
    os.makedirs(sequence_dir)

    unmount_usb_drive()
    
    # Todo: Make a start summary -> log

    if config['timelapse']['num_captures'] < 1:
        max_captures = math.inf
        num_digits = 6
    else:
        max_captures = config['timelapse']['num_captures']
        num_digits = len(str(max_captures))

    cam = init_cam(
        config['camera']['resolution']['width'],
        config['camera']['resolution']['height'],
        config['camera']['iso'],
        config['camera']['shutter_speed'],
        config['camera']['shutter_speed_fixed'],
        config['camera']['rotation']
        )
    
    capture_sequence(
        cam,
        config['timelapse']['interval'],
        max_captures,
        sequence_dir,
        num_digits,
        config['camera']['format'],
        config['camera']['jpeg_quality']
        )
    
    cam.close()

    # Slow flash pattern to indicate sequence has finished
    while True:
        for i in range(2):
            run_in_bash(f"echo {i} | sudo tee /sys/class/leds/led0/brightness > /dev/null 2>&1")
            sleep(1)

print("Done!")
