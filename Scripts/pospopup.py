import serial
import time

try:

    # Replace 'COM3' with the appropriate serial port
    ser = serial.Serial('COM6', 115200, timeout=1)
    time.sleep(2)  # Wait for the serial connection to initializeID

    def send_command(command):
        ser.write((command + '\n').encode())
        time.sleep(1)  # Adjust delay based on the operation duration

    def move_x(steps):
        send_command(f"MOVE_X {steps}")

    def move_y(steps):
        send_command(f"MOVE_Y {steps}")

    def move_z(steps):
        send_command(f"MOVE_Z {steps}")

    def home():
        send_command("HOME")

    def Settings():
        send_command(f"Settings {100}:{200}")
    # Example usage
    # move_x(1000)
    # move_y(1000)
    # while True:
    #     move_z(600)
    #     home()
    #     time.sleep(3)
    time.sleep()
    Settings()
    # Close the serial connection
    ser.close()

except Exception as e:
    print(e)
