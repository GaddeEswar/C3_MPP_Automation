import serial
import serial.tools
import serial.tools.list_ports
import time
from MainModule import JsonOperations,APIOperations
from tkinter import messagebox

class PosTool():
    def __init__(self):
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.JTestConf = JsonOperations('json/TestConfig.json')
        self.JTestConfData = self.JTestConf.read_file()
        self.ser = None   # store serial reference
        self.ARDUINO_VID_PID = {
                            (0x2341, 0x0043),  # Uno R3
                            (0x2341, 0x0010),  # Mega 2560
                            (0x2341, 0x0042),  # Mega 2560 R3
                            (0x2341, 0x8036),  # Leonardo
                            (0x2341, 0x8037),  # Micro
                            (0x2341, 0x003D),  # Due Prog
                            (0x2341, 0x003E),  # Due Native
                            (0x2341, 0x804D),  # Zero / MKR
                            (0x2341, 0x804E),  # MKRZero / MKR1000
                            (0x1A86, 0x7523),  # CH340 clones
                            (0x0403, 0x6001),  # FTDI-based
                            }
        
    def GetAvailablePorts(self):
        availablePort =[]
        self.ports = serial.tools.list_ports.comports()
        print("ports:",self.ports)
        allports = []
        for port in self.ports:
            availablePort.append(port.device)
            allports.append(({"device": port.device,"vid": port.vid,"pid": port.pid}))
        print("PORTS:",availablePort)
        self.JTestConfData['ports'] = allports
        self.JTestConf.update_file(self.JTestConfData)
        return availablePort
    
    def Connection(self,port='COM5'):
        try:
            self.JTestConfData = self.JTestConf.read_file()
            allports = self.JTestConfData['ports']
            print("connecting port:",port)
            print("allports:",allports)
            for p in allports:
                if port == p.get("device"):
                    if (p.get("vid"), p.get("pid")) in self.ARDUINO_VID_PID:
                        self.ser = serial.Serial(port, 115200, timeout=1)
                        time.sleep(2)  # Wait for the serial connection to initialize
                        print("ser:",self.ser)
                        print("Connected to Arduino:",self.ser)
                        return self.ser
            # else: messagebox.showwarning('Arduino connection', f"Selected {port} is not connected to arduino")
        except serial.SerialException as e:
            print("Arduino connection error:", e)
            self.ser = None
            messagebox.showerror('Arduino connection Error', e)
            return None
        except Exception as e:
            print("Unexpected error:", e)
            self.ser = None
            return None

    def Disconnection(self):
        if self.ser and self.ser.is_open:
            try: 
                self.ser.close()
                print(f"Disconnected from {self.ser.port}")
            except Exception as e:
                print("Error closing port:", e)
        else:
            print("No active connection to close")
        self.ser = None

    def SendCommands(self,connection,command):
        try:
            self.JAllMOIData = self.JAllMOI.read_file()
            if "MOVE_Z Home" not in command and not self.JAllMOIData['Run']['PositionToolRemoved']:
                print("command:",command)
                connection.write((command + '\n').encode())
                self.JAllMOIData['Run']['PositionToolRemoved'] = True
                self.JAllMOI.update_file(self.JAllMOIData)
                time.sleep(1)  # Adjust delay based on the operation duration
            elif "MOVE_Z Home" in command and self.JAllMOIData['Run']['PositionToolRemoved']:
                print("command:",command)
                connection.write((command + '\n').encode())
                self.JAllMOIData['Run']['PositionToolRemoved'] = False
                self.JAllMOI.update_file(self.JAllMOIData)
            else:
                print("command:",command)
                connection.write((command + '\n').encode())
        except Exception as e:
            print("SendCommands error:",e) 

    def ReadSerial(self,connection):
        try:
            while True:
                # Read data from Arduino
                if connection.in_waiting > 0:
                    # Read a line of data from Arduino
                    line = connection.readline().decode('utf-8').rstrip() 
                    # Convert the line into an integer (if applicable)
                    try:
                        variable_value = int(line)
                        print(f"Received value: {variable_value}")
                    except ValueError:
                        print(f"Received non-numeric data: {line}")
                # else: break
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            # Close the serial connection
            if connection:
                connection.close()


# obj =  PosTool()
# obj.Connection(port='COM5')
# ports = obj.GetAvailablePorts()
# print(ports)
# status = obj.Connection()

# obj.SendCommands(status,f"SetDefaultPressure")
# obj.ReadSerial(status)
# print(status)