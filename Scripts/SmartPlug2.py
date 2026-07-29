import tinytuya
from datetime import datetime, timezone, timedelta
import subprocess
import time
import re
from MainModule import JsonOperations
from tkinter import messagebox

class WiproPlug():
    def __init__(self):
        self.JLogs = JsonOperations("json/DebugLogs.json")
        self.JLogsData = self.JLogs.read_file()
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.TConfig = JsonOperations("json/TestConfig.json")
        self.TConfigData = self.TConfig.read_file()
        self.SmartDevices = {"SP-06:da":{'id':'d729910ffcbc171328sfqa','key':'U/`W9t-aF[G|:ryC','mac':'10:5a:17:a9:06:da'}, "SP-e6:21":{'id':'d783b78d53e430fe99dipz','key':'Cbxx59CtiZ]=H(E+','mac':'10:5a:17:a5:e6:21'}}#id,key
        # self.ssid = "GRLSmartPlug"#Hotspot"
        # self.password = "G%SPHotSpot%L"#"12345678" 
        # self.band = "2.4 GHz"
        self.dev = self.JAllMOIData["SP_MAC"]
   
    def get_connected_devices(self,dev):
        print("Finding smartPlug")
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.mac = self.SmartDevices[dev]['mac']
        self.JAllMOIData["SP_MAC"] = dev
        self.JAllMOI.update_file(self.JAllMOIData)
        Plug_IP = ""
        try:
            output = subprocess.check_output("arp -a", shell=True).decode()
            devices = re.findall(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]+)\s+(\w+)", output)
            for ip, mac, type in devices:
                if mac == self.mac.replace(":","-"):
                    print(f"IP Address: {ip} | MAC Address: {mac} | Type: {type}")
                    Plug_IP = ip
                    self.TConfigData["Plug_IP"] = Plug_IP
                    self.TConfig.update_file(self.TConfigData)
                    self.TogglePlug("OFF&ON")
                    self.JAllMOIData['SPConnection'] = True
                    self.JAllMOI.update_file(self.JAllMOIData)
                    messagebox.showinfo("SmartPlug",  f"SmartPlug is connected to {dev}")
                    break
            else: messagebox.showinfo("SmartPlug",  f"SmartPlug {dev} is not discovered")
        except subprocess.CalledProcessError as e:
            print("Failed to retrieve ARP table:", e)

    def TogglePlug(self,req_state=None):
        try:         
            self.TConfigData = self.TConfig.read_file()
            self.JAllMOIData = self.JAllMOI.read_file()
            self.dev = self.JAllMOIData["SP_MAC"]
            Plug_IP = self.TConfigData["Plug_IP"]
            # print("Plug_IP:",Plug_IP,"dev:",self.dev)
            self.device = tinytuya.OutletDevice(dev_id=self.SmartDevices[self.dev]['id'], address=str(Plug_IP), local_key=self.SmartDevices[self.dev]['key'])
            self.device.set_version(3.3)
            if req_state == "OFF&ON":
                self.device.set_status(False, 1)
                print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))
                time.sleep(2)
                self.device.set_status(True, 1)
                print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))
            elif req_state == "ON":
                self.device.set_status(True, 1)
                print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))
            elif req_state == "OFF":
                self.device.set_status(False, 1)
                print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))
        except Exception as e:
            print("Failed to toggle hotspot:", e)

    def update_logs(self,logtype,log):
        dt_object = datetime.fromtimestamp(datetime.now().timestamp())
        self.JLogsData = self.JLogs.read_file()
        self.JLogsData.append([str(dt_object),logtype,log])
        self.JLogs.update_file(self.JLogsData)

# if __name__ == "__main__":
#     obj1 = WiproPlug()
#     obj1.MobileHotspot(1)
    # time.sleep(10)
    # ip = obj1.get_connected_devices()
    # time.sleep(5)
    # obj1.TogglePlug("192.168.137.155")

