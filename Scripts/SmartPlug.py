# import tinytuya
# from datetime import datetime, timezone, timedelta
# # from pywinauto import Desktop
# import subprocess
# import time
# import re
# from MainModule import JsonOperations
# from tkinter import messagebox

# # from pywinauto import Desktop
# # self.settings_win = Desktop(backend='uia').window(title='Settings')


# class WiproPlug():
#     def __init__(self):
#         #self.Plug_IP = None
#         from pywinauto import Desktop
#         self.JLogs = JsonOperations("json/DebugLogs.json")
#         self.JLogsData = self.JLogs.read_file()
#         self.JAllMOI = JsonOperations('json/AllMOIRun.json')
#         self.JAllMOIData = self.JAllMOI.read_file()
#         # self.mac = self.JAllMOIData["SP_MAC"]
#         self.SmartDevices = {"SP-06:da":{'id':'d729910ffcbc171328sfqa','key':'U/`W9t-aF[G|:ryC','mac':'10:5a:17:a9:06:da'}, "SP-e6:21":{'id':'d783b78d53e430fe99dipz','key':'Cbxx59CtiZ]=H(E+','mac':'10:5a:17:a5:e6:21'}}#id,key
#         self.ssid = "GRLSmartPlug"#Hotspot"
#         self.password = "G%SPHotSpot%L"#"12345678" 
#         self.band = "2.4 GHz"
#         # self.settings_win = Desktop(backend='uia').window(title='Settings')
#         self.dev = self.JAllMOIData["SP_MAC"]
#         self.Plug_IP = self.JAllMOIData["Plug_IP"]
#         # # Setup the device
#         # self.device = tinytuya.OutletDevice(dev_id=self.SmartDevices[self.dev]['id'], address=str(self.Plug_IP), local_key=self.SmartDevices[self.dev]['key'])
#         # self.device.set_version(3.3)

#     def CreateHotspot(self,dev):
#         try:
#             subprocess.Popen('start ms-settings:network-mobilehotspot', shell=True)
#             time.sleep(2)
#             self.mac = self.SmartDevices[dev]['mac']
#             self.JAllMOIData["SP_MAC"] = dev
#             self.JAllMOI.update_file(self.JAllMOIData)
#             from pywinauto import Desktop
#             self.settings_win = Desktop(backend='uia').window(title='Settings')

#             self.settings_win.set_focus()
#             self.toggle = self.settings_win.child_window(auto_id="SystemSettings_Connections_InternetSharingEnabled_ToggleSwitch",control_type="Button")
#             self.hotspot_state = self.toggle.get_toggle_state()
#             hotspot_status = self.VerifyHotspot()

#             if hotspot_status and self.hotspot_state == 0:
#                 self.toggling(1)
#             elif not hotspot_status:
#                 if self.hotspot_state == 1:
#                     self.toggling(0)
#                     time.sleep(5)
#                 try:
#                     edit_btn = self.settings_win.child_window(auto_id="SystemSettings_Connections_InternetSharingSetup_Button", control_type="Button")
#                     edit_btn.wait('enabled', timeout=5)
#                     edit_btn.click_input()
#                     print("Clicked Edit network info button")
#                     time.sleep(1)

#                     popup = self.settings_win.child_window(title="Edit network info", control_type="Window")
#                     popup.wait('visible', timeout=5)
#                     popup.set_focus()

#                     ssid_input = popup.child_window(auto_id="SystemSettings_Connections_InternetSharingSetup_NetworkNameTextBlock", control_type="Edit")
#                     password_input = popup.child_window(auto_id="SystemSettings_Connections_InternetSharingSetup_NetworkPassphraseTextBlock", control_type="Edit")
#                     # band_combo = popup.child_window(auto_id="SystemSettings_Connections_InternetSharingSetup_NetworkFrequencyComboBox", control_type="ComboBox")
#                     save_btn = popup.child_window(auto_id="PrimaryButton", control_type="Button")

#                     ssid_input.set_edit_text(self.ssid)
#                     password_input.set_edit_text(self.password)

#                     # # Open dropdown and select 2.4 GHz
#                     # band_combo.select(self.band)
#                     # print("Selected band as 2.4 GHz")

#                     save_btn.click_input()
#                     print(f"Updated SSID to '{self.ssid}' and password to '{self.password}'")
#                     time.sleep(1)
#                     # turn on hotspot
#                     self.toggling(1) 
#                     self.VerifyHotspot()

#                 except Exception as e:
#                     print("Failed to update SSID, password, or band:", e)
#                     return
            
#             self.MobileHotspot(1)
#         except Exception as e:
#             print("Failed to update SSID, password, or band:", e)
#             subprocess.call('taskkill /f /im SystemSettings.exe', shell=True) #Closes settings window
#             messagebox.showwarning("WIFI module", "WIFI module is not available in you system, to turn on mobile hotspot")

#     #Check for default hotspot is defined.
#     def VerifyHotspot(self):
#         from pywinauto import Desktop
#         self.settings_win = Desktop(backend='uia').window(title='Settings')
#         # verify hotspot details
#         try:
#             #time.sleep(1)
#             self.settings_win.set_focus()
#             ssid_label = self.settings_win.child_window(auto_id="SystemSettings_Connections_InternetSharingSsid_ValueTextBlock", control_type="Text")
#             password_label = self.settings_win.child_window(auto_id="SystemSettings_Connections_InternetSharingPasskey_ValueTextBlock", control_type="Text")
#             # band_label = self.settings_win.child_window(auto_id="SystemSettings_Connections_InternetSharingFrequency_ValueTextBlock", control_type="Text")
  
 
#             actual_ssid = ssid_label.window_text()
#             actual_password = password_label.window_text()
#             # actual_band = band_label.window_text()

#             print(f"Verified SSID: {actual_ssid}")
#             print(f"Verified Password: {actual_password}")
#             # print(f"Verified Band: {actual_band}")

#             if actual_ssid != self.ssid or actual_password != self.password: #or actual_band != self.band:
#                 print("Mismatch detected. UI might not have updated yet")
#                 return False
#             return True
#         except Exception as e:
#             print("Failed to verify updated values:", e)

#     def MobileHotspot(self,req_stste = None):
#         from pywinauto import Desktop
#         self.settings_win = Desktop(backend='uia').window(title='Settings')
#         try:
#             self.settings_win.set_focus()
#             self.hotspot_state = self.toggle.get_toggle_state()
#             if self.hotspot_state == 1:subprocess.call('taskkill /f /im SystemSettings.exe', shell=True) #Closes settings window
#             print(f"Current Hotspot State: {'ON' if self.hotspot_state == 1 else 'OFF'}")
#             if req_stste == 0:
#                 self.JAllMOIData["Plug_IP"] = ""
#                 self.JAllMOI.update_file(self.JAllMOIData)
#             if self.hotspot_state != req_stste :
#                 # Toggle it
#                 self.toggling(req_stste)
#                 print("Toggled the Mobile Hotspot switch.")
#                 print(f"Device is turned {'ON' if req_stste == 1 else 'OFF'}")
#             # Connect to desired device
#             self.Plug_IP = self.JAllMOIData["Plug_IP"]
#             if req_stste == 1:
#                 while True:
#                     time.sleep(10)
#                     self.get_connected_devices()
#                     if self.Plug_IP is not None: break
#                     else:
#                         print("TURN OFF")
#                         self.toggling(0)#self.toggle.click_input()  #off
#                         time.sleep(3)
#                         print("TURN ON")
#                         self.toggling(1)#self.toggle.click_input()  #on
#             self.update_logs("UI", "SmartPlug is connected")
#             print(self.Plug_IP)
#             messagebox.showinfo("Smart Plug", f"{self.dev} Smart plug is connected")
#         except Exception as e:
#             print("Failed to toggle hotspot:", e)

#     def toggling(self, req_state=None, attempts=5):
#         from pywinauto import Desktop
#         self.settings_win = Desktop(backend='uia').window(title='Settings')
#         # print("hotspot_state:", self.hotspot_state, "req_state:", req_state)
#         self.settings_win.set_focus()
#         if self.hotspot_state == req_state:
#             return  # Base case: already in desired state
#         if attempts == 0:
#             print("Max attempts reached. Toggle failed.")
#             return
#         self.toggle.click_input()
#         time.sleep(0.5)  # Optional: allow UI to update
#         self.hotspot_state = self.toggle.get_toggle_state()
#         self.toggling(req_state, attempts - 1)
    
#     def get_connected_devices(self):
#         print("Finding smartPlug")
#         # base_mac = "10:5a:17:a5:e6:21"
#         self.Plug_IP = ""
        
#         try:
#             output = subprocess.check_output("arp -a", shell=True).decode()
#             devices = re.findall(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]+)\s+(\w+)", output)
#             for ip, mac, type in devices:
#                 if mac == self.mac.replace(":","-"):
#                     print(f"IP Address: {ip} | MAC Address: {mac} | Type: {type}")
#                     self.Plug_IP = ip
#                     # subprocess.call('taskkill /f /im SystemSettings.exe', shell=True) #Closes settings window
#                     self.TogglePlug("OFF&ON")
#                     self.JAllMOIData['SPConnection'] = True
#                     break
#             # if not self.Plug_IP: messagebox.showerror("Smart Plug", "Make sure right Smart Plug is connected to power supply")
#             self.JAllMOIData["Plug_IP"] = self.Plug_IP
#             self.JAllMOI.update_file(self.JAllMOIData)
#             # self.TogglePlug("OFF&ON")
#         except subprocess.CalledProcessError as e:
#             print("Failed to retrieve ARP table:", e)

#     def MatchIPMAC(self):
#         ip_to_check = self.Plug_IP
#         mac_to_check = self.SmartDevices[self.dev]['mac']
#         output = subprocess.check_output("arp -a", shell=True).decode()

#         # Normalize MAC address (convert - to : and lowercase)
#         mac_to_check = mac_to_check.lower().replace('-', ':')

#         # Match IP and MAC from arp -a output
#         devices = re.findall(r"(\d+\.\d+\.\d+\.\d+)\s+([-\w]+)\s+\w+", output)
#         for ip, mac in devices:
#             normalized_mac = mac.lower().replace('-', ':')
#             if ip == ip_to_check and normalized_mac == mac_to_check:
#                 return True
#         return False

#     def TogglePlug(self,req_state=None):
#         try:         
#             # IST = timezone(timedelta(hours=5, minutes=30))
#             # Setup the device
#             print(self.Plug_IP)
#             self.device = tinytuya.OutletDevice(dev_id=self.SmartDevices[self.dev]['id'], address=str(self.Plug_IP), local_key=self.SmartDevices[self.dev]['key'])
#             self.device.set_version(3.3)
#             if req_state == "OFF&ON":
#                 self.device.set_status(False, 1)
#                 print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))
#                 time.sleep(3)
#                 self.device.set_status(True, 1)
#                 print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))
#             elif req_state == "ON":
#                 self.device.set_status(True, 1)
#                 print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))
#             elif req_state == "OFF":
#                 self.device.set_status(False, 1)
#                 print("SmartPlug status:",self.device.status().get("dps", {}).get("1", None))

#         except Exception as e:
#             print("Failed to toggle hotspot:", e)

#     def update_logs(self,logtype,log):
#         dt_object = datetime.fromtimestamp(datetime.now().timestamp())
#         self.JLogsData = self.JLogs.read_file()
#         self.JLogsData.append([str(dt_object),logtype,log])
#         self.JLogs.update_file(self.JLogsData)

# # if __name__ == "__main__":
# #     obj1 = WiproPlug()
# #     obj1.MobileHotspot(1)
#     # time.sleep(10)
#     # ip = obj1.get_connected_devices()
#     # time.sleep(5)
#     # obj1.TogglePlug("192.168.137.155")

