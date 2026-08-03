import csv
# import shutil
import sys, subprocess
import tkinter as tk
from tkinter import font,messagebox,ttk,simpledialog,BooleanVar
from tkinter import filedialog
import threading
from Scripts.ExcerciseValidation import ExcerciseValidation
from Scripts.offlineValidation import OfflineValidation
from Scripts.OfflineValidationNew import TestValidation
from Scripts.offlineValidationMPPTPT import OfflineValidationMPPTPT
from Scripts.MainModule import JsonOperations,APIOperations,GeneralMethods,Server
from Scripts.AllMOIRun import ALLMOIModule
# from Scripts.CSVReports import CSVreport
from Scripts.postool import PosTool
from Scripts.OptimumPosition import GetOptimumPosition
from Scripts.LIcenseVerifyMini import GrlEthernetLink_C2
from Scripts.JsonSchema import C3_MPP_JsonSchema,C3_MPP_PdfSchema

#from Scripts.OtherReports import XLreport
from Scripts.RunTests import RunTests
from Scripts.ReportAnly import JsonReports
import tkfilebrowser
from tkinter.filedialog import askopenfilename
import datetime,time
from datetime import datetime,date
from pathlib import Path
# import json
import orjson
import traceback
import os
from Scripts.SQLite import SQLiteConnection 
from Scripts.ExcelReport import ExcelReports
from pymongo import MongoClient
import pandas as pd
import xml.etree.ElementTree as ET
from scapy.all import IP as ScapyIP, ICMP, sr1
from Scripts.SmartPlug2 import WiproPlug

class MPPGUI(tk.Tk):    
    def __init__(self):
        super().__init__()
        #Get inputs from JSON
        self.Jsettings = JsonOperations('json/setting.json')
        self.JsettingsData =self.Jsettings.read_file()
        self.Jtester = JsonOperations('json/Tester.json')
        self.JtesterData =self.Jtester.read_file()
        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.JQI = JsonOperations('json/QIconfig.json')
        self.JQIData = self.JQI.read_file()
        self.JMOI = JsonOperations('json/MOIJson.json')
        self.JMOIData = self.JMOI.read_file()
        self.JTestConf = JsonOperations('json/TestConfig.json')
        self.JTestConfData = self.JTestConf.read_file()
        self.JTCP = JsonOperations('json/Test_config_properties.json')
        self.JTCPData = self.JTCP.read_file()
        self.JLogs = JsonOperations("json/DebugLogs.json")
        self.JLogsData = self.JLogs.read_file()
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.TesterConfig = JsonOperations('json/TesterConfig.json')
        self.TesterConfigData = self.TesterConfig.read_file()
        self.JEsdf = JsonOperations('json/ESDF.json')
        self.JEsdfData = self.JEsdf.read_file()
        self.EsdfTest = JsonOperations('json/TestsComp.json')
        self.EsdfTestData = self.EsdfTest.read_file()
        self.TestResultsjson = JsonOperations("json/TestResults.json")
        self.TestData = self.TestResultsjson.read_file()
        # self.JCTS = JsonOperations(f"json/CTSvalidation/{self.JsettingsData['Offline_validation']['CTSConfig']}")
        # self.JCTSData = self.JCTS.read_file()
        # self.JsettingsData['Runall'] = True
        self.AllRun = self.JsettingsData['Runall']
        self.JsettingsData['RunEx'] = False
        self.ExRun = self.JsettingsData['RunEx']
        self.poolvar = tk.StringVar(value="0x010E")
        self.sts = False
        self.postool = PosTool()
        self.SQLConn = SQLiteConnection()
        self.ExcelRep = ExcelReports()
        self.TesterConnection = False
        # self.SQLConn.ExecutebyQuery(f"UPDATE TestCaseCompleteDetailsView SET TestResults = 'NA'")

        # self.JAllMOIData["Plug_IP"] = ""
        # self.JAllMOI.update_file(self.JAllMOIData)
        #set thead to true by default
        self.projloaded = False
        self.JsettingsData['_stop_flag']=True
        self.JsettingsData['_Logs_flag']=True
        self.Jsettings.update_file(self.JsettingsData)
        self.smartplug_obj = WiproPlug()
        self.SPConnection = False
        self.alloptimumcoils = []
        #Color codes
        self.Ccodes = {"blue" : '#23275C', "grey" : '#808080', "frame_bg" : '#FBFCF8', "text_bg" : '#FAFAFA', "lyt_cyan" : '#D1DADC', "white": '#FFFFFF', "black" : "#000000", "green" : "#00FF00", "red" : "#FF0000"}
        #MoveLogs
        self.MoveDebugLogstoLogs()
        #clear Logs
        if self.JLogsData is not None:
            self.JLogsData.clear()
            self.JLogs.update_file(self.JLogsData)
        self.logscount = 0
        #Process list
        self._stop_flag = False
        self.progLogs = []
        # self.OfflineProjs = []
        self.TestStartTime = None
        self.PrevUIlogs = []
        #Set switch as Offline and mode as TPT
        # self.JAllMOIData['Product'] = "C3"
        # self.JAllMOIData['Mode'] = 'TPT'
        # self.JAllMOIData['Certificate'] = 'V_1.3.3'
        # self.JAllMOIData['PowerProfile'] = 'BPP'
        # self.JAllMOIData['Switch'] ="Offline"
        # self.Jsettings.update_file(self.JsettingsData)

        # self.JAllMOIData['Run']['Project'] = ""
        self.JAllMOIData['Run']['EnableSmartSwitch'] = False
        self.JAllMOIData['Run']['PowerOFF&ON'] = False
        self.JAllMOIData['SPConnection'] = False
        self.JAllMOIData['Run']['TAD'] = False
        self.JAllMOI.update_file(self.JAllMOIData)

        # self.JsettingsData=self.Jsettings.read_file()
    def CreateAPP(self):
        #main setup
        self.title(f"MPP Test Automation | Version : {self.JsettingsData['SWversion']}")
        self.geometry("1050x795")  
        self.iconbitmap("Resources\\img\\GRLPFO.ico")
        self.resizable(False,False)
        # self.protocol("WM_DELETE_WINDOW", self.on_closing)
        #Fonts
        self.FT12BW = font.Font(family='Calibri', size=12, weight='bold')
        self.FT8BW = font.Font(family='Calibri', size=8, weight='bold')
        self.FT10BW = font.Font(family='Calibri', size=10, weight='bold')
        self.FT15BW = font.Font(family='Calibri', size=15, weight='bold')
        #Widget menu
        self.SM1_frame = Menu(self,height=795,width=100,bg=self.Ccodes["blue"],x=0,y=0)
        self.SM2_frame = Menu(self,height=795,width=950,bg=self.Ccodes["grey"],x=100,y=0)
        #Add Combo to choose Mode
        self.Product = self.JAllMOIData['Product']
        self.Mode = self.JAllMOIData['Mode']
        self.switch = self.JAllMOIData['Switch'] 
        self.Offline = tk.PhotoImage(file='./Resources/img/Offline.png')
        self.Online = tk.PhotoImage(file='./Resources/img/Online.png')
        self.TPRTGIMG = tk.PhotoImage(file='./Resources/img/TPR.png')
        self.TPTTGIMG = tk.PhotoImage(file='./Resources/img/TPT.png')    
        # self.RN_FR6 = tk.Frame(self.SM2_frame)
        Labels(self.SM1_frame,text="Product:",x=2,y=2,width=13,bg=self.Ccodes["blue"],fg=self.Ccodes["white"],font=self.FT10BW)
        self.ProdCB = Combo(self.SM1_frame,width=12,name="prodcb",state="readonly",font=self.FT10BW,val=list(self.JMOIData['Versions'].keys()),bg=self.Ccodes["text_bg"],fg=self.Ccodes["black"],x=2,y=20,selectedVal=self.JAllMOIData['Product'])
        self.ProdCB.bind("<<ComboboxSelected>>",self.RestoreRun)
        self.Modeswitch = Buttons(self.SM1_frame,x=6,y=45,height=32,width=80,bg=self.Ccodes["blue"],command=self.SwitchMode)
        self.Modeswitch['image']=self.TPRTGIMG if self.Mode=='TPR' else self.TPTTGIMG
        self.Runswitch = Buttons(self.SM1_frame, x=6,y=90,height=32,width=80, bg=self.Ccodes["blue"], command=self.SwitchRun)
        self.Runswitch['image'] = self.Offline if self.switch=='Offline' else self.Online
        # if self.switch == "online":
        # #Version selection
        # Labels(self.SM1_frame,text="Certification:",x=2,y=115,width=13,bg=self.Ccodes["blue"],fg=self.Ccodes["white"],font=self.FT10BW)
        # self.VerCB = Combo(self.SM1_frame,width=12,name="verCB",state="readonly",font=self.FT10BW,val=list(self.JMOIData['Versions'][self.Product][self.Mode].keys()),bg=self.Ccodes["text_bg"],fg=self.Ccodes["black"],x=2,y=140,selectedVal=self.JAllMOIData['Certificate'])
        # self.VerCB.bind("<<ComboboxSelected>>",self.RestoreRun)
        #PowerProfileSelection
        # Labels(self.SM1_frame,text="PowerProfile:",x=2,y=165,width=13,bg=self.Ccodes["blue"],fg=self.Ccodes["white"],font=self.FT10BW)
        # self.PPCB = Combo(self.SM1_frame,name="ppCB",width=12,state="readonly",font=self.FT10BW,val=self.JMOIData['Versions'][self.Product][self.Mode][self.VerCB.get()],bg=self.Ccodes["text_bg"],fg=self.Ccodes["black"],x=2,y=190,selectedVal=self.JAllMOIData['PowerProfile'])   
        # # print(self.PPCB.get())
        # self.PPCB.bind("<<ComboboxSelected>>",self.RestoreRun)
        # #Project Name
        # Labels(self.SM1_frame,text="Project:",x=2,y=215,width=13,bg=self.Ccodes["blue"],fg=self.Ccodes["white"],font=self.FT10BW)
        # self.ProjNameET = Entries(self.SM1_frame,width=14,x=2,y=240,font=self.FT10BW,bg=self.Ccodes["text_bg"],fg=self.Ccodes["black"],textvar=self.JAllMOIData['Run']['Project'],name="projET")
        # self.ProjNameET.bind('<KeyPress>', self.RestoreRun)
        #Main Menu
        img_run = tk.PhotoImage(file='./Resources/img/runbtn.png')
        Buttons(self.SM1_frame,image=img_run,bg=self.Ccodes["blue"],x=30,y=150,command=lambda:Run(self))
        img_ip = tk.PhotoImage(file='./Resources/img/posbtn.png')
        Buttons(self.SM1_frame,image=img_ip,bg=self.Ccodes["blue"],x=30,y=240,command=lambda:IP(self))
        img_rp = tk.PhotoImage(file='./Resources/img/rpbtn.png')
        Buttons(self.SM1_frame,image=img_rp,bg=self.Ccodes["blue"],x=30,y=340,command=lambda:Reports(self))
        img_st = tk.PhotoImage(file='./Resources/img/stbtn.png')
        Buttons(self.SM1_frame,image=img_st,bg=self.Ccodes["blue"],x=30,y=420,command=lambda:Settings(self))
        img_import = tk.PhotoImage(file='./Resources/img/import.png')
        Buttons(self.SM1_frame,image=img_import,bg=self.Ccodes["blue"],x=30,y=500, command=self.open_file_dialog)
        img_export = tk.PhotoImage(file='./Resources/img/export.png')
        Buttons(self.SM1_frame,image=img_export,bg=self.Ccodes["blue"],x=30,y=580, command=self.export)
        img_ref = tk.PhotoImage(file='./Resources/img/refresh.png')
        Buttons(self.SM1_frame,image=img_ref,bg=self.Ccodes["blue"],x=39,y=680, command=self.refresh_window)
        #Add logo
        # Labels(self.SM1_frame,text=self.JsettingsData['SWversion'],x=1,y=700,width=15,bg=self.Ccodes["blue"],fg=self.master.Ccodes["white"])
        grllogo = tk.PhotoImage(file='./Resources/img/grl.png')
        logo_frame = Menu(self.SM1_frame,height=50,width=80,bg=self.Ccodes["blue"],x=10,y=740)
        Labels(logo_frame,x=0,y=0,img=grllogo,bg=self.Ccodes["blue"])
        tk.Label(logo_frame,image=grllogo,background=self.Ccodes["blue"]).place(x=0,y=0)
        #Enable for Direct offline validation with no UI
        # off = Run(self)
        # off.OfflineValidation()
        #Online
        #Open run section with default settings
        self.AllMOIModule = ALLMOIModule()
        Run(self)
        self.mainloop()
    # def on_closing(self):
    #     if self.SPConnection:
            # self.smartplug_obj = WiproPlug()
    #         subprocess.Popen('start ms-settings:network-mobilehotspot', shell=True)
    #         time.sleep(2)
    #         self.settings_win = Desktop(backend='uia').window(title='Settings')
    #         self.settings_win.set_focus()
    #         self.toggle = self.settings_win.child_window(auto_id="SystemSettings_Connections_InternetSharingEnabled_ToggleSwitch",control_type="Button")
    #         self.hotspot_state = self.toggle.get_toggle_state()
    #         if self.hotspot_state == 1:
    #             self.smartplug_obj.toggling(0)
    #         subprocess.call('taskkill /f /im SystemSettings.exe', shell=True) #Closes settings window
    #     self.destroy()
    def open_file_dialog(self):
        # Open file dialog and get selected file path
        json_file_path  = filedialog.askopenfilename()
        if json_file_path :
            # with open(json_file_path, "r") as file:
            #     data = json.load(file)
            with open(json_file_path, "rb") as file:   # binary mode required
                data = orjson.loads(file.read())
                if all(res in data for res in ["Header","QIconfig","TestConfig"]):
                    self.JAllMOIData['Mode'] = data["Header"]['Mode']
                    self.JAllMOIData['Certification']=data["Header"]['Certification']
                    self.JAllMOIData['powerProfile']=data["Header"]['powerProfile']
                    self.JAllMOI.update_file(self.JAllMOIData)
                    self.JQIData[data["Header"]["Mode"]] = data["QIconfig"]
                    self.JQI.update_file(self.JQIData)
                    self.JTestConfData[data["Header"]["Mode"]] = data["TestConfig"]
                    self.JTestConf.update_file(self.JTestConfData)
                    self.refresh_window()
                else:messagebox.showinfo("File Upload","Invalid JSON file selected")
    # def refresh_window(self):
    #     python = sys.executable
    #     # os.execl(python, python, * sys.argv)
    #     subprocess.Popen([python] + sys.argv)  # start new process
    #     sys.exit()  # kill current one
    
    def refresh_window(self):
        exe_path = sys.executable
        if getattr(sys, 'frozen', False):  # Running as PyInstaller exe
            subprocess.Popen([exe_path])
        else:  # Running from normal Python
            subprocess.Popen([sys.executable] + sys.argv) 
        sys.exit()
    def RestoreRun(self,ts):
        #Refresh PowerProfile section
        self.SQLConn.ExecutebyQuery("DELETE FROM TestFilters")
        self.SQLConn.ExecutebyQuery("DELETE FROM AllTestcases")
        if ts != "NA":
            # if ts.widget.winfo_name() == "verCB": 
            #     self.PPCB['values']=self.JMOIData['Versions'][self.Product][self.Mode][self.VerCB.get()]
                # self.JAllMOIData['Certificate'] = self.VerCB.get()
            # elif ts.widget.winfo_name() == "ppCB":
            #     self.AllMOIModule.PP = self.JAllMOIData['PowerProfile'] =  self.PPCB.get()
            # elif ts.widget.winfo_name() == "projET":
            #     self.JAllMOIData['Run']['Project'] = self.ProjNameET.get()
            # if  ts.widget.winfo_name() == "prodcb":
            #     self.VerCB['values']=list(self.JMOIData['Versions'][self.ProdCB.get()][self.Mode].keys())
            #     self.VerCB.set(list(self.JMOIData['Versions'][self.ProdCB.get()][self.Mode].keys())[0]) 
                # self.PPCB['values']=self.JMOIData['Versions'][self.ProdCB.get()][self.Mode][self.VerCB.get()]
                # self.PPCB.set(self.JMOIData['Versions'][self.ProdCB.get()][self.Mode][self.VerCB.get()][0])
            self.Product = self.JAllMOIData['Product'] = self.ProdCB.get() 
            # self.JAllMOIData['Certificate'] = self.VerCB.get() 
            # self.JAllMOIData['PowerProfile'] = next((item["value"] for item in self.JEsdfData[self.Product][self.Mode]['Esdf_Elements'] if item["field"] == "PowerProfile"))#self.PPCB.get()
            self.JAllMOI.update_file(self.JAllMOIData)
            if ts.widget.winfo_name() == "prodcb": Run(self)
        else:
            Run(self)
    # Select Offline or Online
    def MoveDebugLogstoLogs(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data = JsonOperations("json/DebugLogs.json").read_file()
            with open(f'Logs/DebugLogs_{timestamp}.txt','w') as file:
                for log in data:
                    file.write(f"{log[0]} : {log[1]} : {log[2]}\n")
            #shutil.copyfile('json/DebugLogs.json',f'Logs/DebugLogs_{timestamp}.txt')
        except Exception as e:print(e)
    def SwitchRun(self):
        print("Switching from",self.switch)
        # self.SQLConn.ExecutebyQuery("DELETE FROM TestFilters")
        # self.SQLConn.ExecutebyQuery("DELETE FROM AllTestcases")
        if self.switch == 'Offline':
            self.Runswitch['image'] = self.Online
            # self.switch = self.JsettingsData['Switch'] = 'online'
            self.switch = self.JAllMOIData['Switch'] = 'online'
        else:
            self.Runswitch['image'] = self.Offline
            self.switch = self.JAllMOIData['Switch'] =  'Offline'
        self.JAllMOI.update_file(self.JAllMOIData)
        # self.Jsettings.update_file(self.JsettingsData)  
        # self.JsettingsData = self.Jsettings.read_file()
        self.RestoreRun("NA")
    def SwitchMode(self):
        self.SQLConn.ExecutebyQuery("DELETE FROM TestFilters")
        self.SQLConn.ExecutebyQuery("DELETE FROM AllTestcases")
        if self.Mode=='TPT':
            self.Modeswitch['image']=self.TPRTGIMG  
            self.Mode = self.JAllMOIData['Mode'] = 'TPR'
        else:
            self.Modeswitch['image']=self.TPTTGIMG
            self.Mode=self.JAllMOIData['Mode'] = 'TPT'
        #self.JAllMOIData['Switch'] = 'Offline'
        self.Jsettings.update_file(self.JsettingsData)
        self.JAllMOI.update_file(self.JAllMOIData)
        #self.VerCB['values'] = list(self.JMOIData['Versions'][self.Product][self.Mode].keys())
        #self.PPCB['values'] = self.JMOIData['Versions'][self.Product][self.Mode][self.VerCB.get()]
        #self.VerCB.set(list(self.JMOIData['Versions'][self.Product][self.Mode].keys())[0])
        #self.PPCB.set(self.JMOIData['Versions'][self.Product][self.Mode][self.VerCB.get()][0])
        self.AllMOIModule.Mode = self.Mode
        # print(APIOperations(url=self.JapiData[self.Product][self.Mode]['GetSoftwareVersion'], retype='json').GetRequest())
        self.RestoreRun("NA")
    def ClearFrame(self,frm):
        if len(frm.winfo_children()) > 0:
            for wdgt in frm.winfo_children():
                wdgt.destroy()
    def export(self):
        pass
        # data = {"Header": {"Mode":self.Mode,"Certification":self.VerCB.get(),"powerProfile":self.PPCB.get()},"QIconfig":self.JQIData[self.Mode],"TestConfig":self.JTestConfData[self.Mode]}
        # # Generate filename with timestamp
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # new_json_filename = f'Export_{self.Mode}_{self.VerCB.get()}{self.PPCB.get()}_{timestamp}.json'
        # # Create a new JSON file with the data
        # with open(new_json_filename, 'w') as file:
        #     json.dump(data, file, indent=4)
        # print("New JSON file created for TPT mode:", new_json_filename)
class Run(MPPGUI):
    def __init__(self,master):
        self = self
        self.master = master    
        self.master.ClearFrame(self.master.SM2_frame)
        self.CreateRUNUI()  
        if self.master.switch =="Offline":
            self.update_logs("UI",f"Automation tool set for {self.master.Product} {self.master.Mode} in {self.master.switch} mode.")
        else: 
            self.update_logs("UI",f"Automation tool set for {self.master.Product} {self.master.Mode} in {self.master.switch} mode.")
        # self.P_OnlineValidation =  threading.Thread(target=self.RunTest)
        # self.P_OfflineValidaton = threading.Thread(target=self.TesterConnect)
        # self.P_Updatelogs = threading.Thread(target=self.LogsUI)
        self.master.postool.Disconnection()
    
    def CreateRUNUI(self):
        if self.master.switch=='online':
            #print(self.JsettingsData['Switch'])
            #create frames for runs
            self.RN_FR1 = Menu(self.master.SM2_frame,height=150,width=300,bg=self.master.Ccodes["frame_bg"],x=5,y=5)
            #Preparations
            # self.RN_FR2 = Menu(self.master.SM2_frame,height=450,width=305,bg=self.master.Ccodes["frame_bg"],x=310,y=5)
            #Filters
            self.RN_FR3 = Menu(self.master.SM2_frame,height=450,width=300,bg=self.master.Ccodes["frame_bg"],x=310,y=5)#310,310  x=5,y=160
            
            self.RN_FR4 = Menu(self.master.SM2_frame,height=450,width=325,bg=self.master.Ccodes["frame_bg"],x=620,y=5)
            #Run Tests
            self.RN_FR5 = Menu(self.master.SM2_frame,height=140,width=635,bg=self.master.Ccodes["frame_bg"],x=310,y=460)
            #self.RN_FR6 = Menu(self.master.SM2_frame,height=180,width=635,bg='#343638',x=310,y=605)
            #Logs
            self.RN_FR7 = Menu(self.master.SM2_frame,height=180,width=635,bg=self.master.Ccodes["frame_bg"],x=310,y=605)
            #Optimum 
            #self.RN_FR8 = Menu(self.master.SM2_frame,height=195,width=305,bg=self.master.Ccodes["frame_bg"],x=310,y=260)
            #License verification
            if self.master.Product == 'MPP' and self.master.Mode == 'TPR':
                self.RN_FR2 = Menu(self.master.SM2_frame,height=475,width=300,bg=self.master.Ccodes["frame_bg"],x=5,y=160)#5,160  x=310,y=5
                self.RN_FR8 = Menu(self.master.SM2_frame,height=145,width=300,bg=self.master.Ccodes["frame_bg"],x=5,y=640)#5,465   x=310,y=310
            else:
                self.RN_FR2 = Menu(self.master.SM2_frame,height=625,width=300,bg=self.master.Ccodes["frame_bg"],x=5,y=160)#5,160   x=310,y=5

            #Add Connect Tester UI
            self.PutTestConnectionUI()
            #Add Test QI inputs UI
            # self.PutQiInputUI()
            self.PutQiESDFUI()
            #Add test selection
            self.PutTestSel()
            #Add List Tests UI
            self.PutListTests()
            #Add Run Tests UI
            self.PutRunTests()
            #Add Offline Validation UI
            #self.PutOfflineValUI()
            #Add Logs UI
            #self.PutOptimumUI()
            self.LicenseUI()
            self.LogsUI() 
            # self.TesterConnect() 
        else:
            # self.RN_FR2 = Menu(self.master.SM2_frame,height=950,width=300,bg=self.master.Ccodes["frame_bg"],x=5,y=5)
            self.RN_FR4 = Menu(self.master.SM2_frame,height=450,width=635,bg=self.master.Ccodes["frame_bg"],x=5,y=5)
            self.RN_FR4_2 = Menu(self.master.SM2_frame,height=450,width=300,bg=self.master.Ccodes["frame_bg"],x=645,y=5)

            self.RN_FR6 = Menu(self.master.SM2_frame,height=180,width=940,bg=self.master.Ccodes["frame_bg"],x=5,y=460)
            self.RN_FR7 = Menu(self.master.SM2_frame,height=180,width=940,bg=self.master.Ccodes["frame_bg"],x=5,y=645)
            # self.PutQiInputUI()
            self.PutListTests()
            self.PutOfflineValUI()
            self.LogsUI() 
    #def PutOptimumUI(self):
        # Labels(self.RN_FR8,text="Get Optimum Position",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=47,font=self.master.FT10BW)
        # Labels(self.RN_FR8,text="DUTName :",x=0,y=22,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        # self.OPTPOSDUTname = Entries(self.RN_FR8,width=20,x=100,y=22,font=self.master.FT12BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],textvar=self.master.JsettingsData['OptimumData']['DUTname'])
        # Labels(self.RN_FR8,text="Coil Name :",x=0,y=47,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        # self.OPTPOSCoil = Entries(self.RN_FR8,width=20,x=100,y=47,font=self.master.FT12BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],textvar=self.master.JsettingsData['OptimumData']['Coil'])
        # Buttons(self.RN_FR8,text='Start Optimum',x=100,y=72,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=12,font=self.master.FT10BW)
        # Buttons(self.RN_FR8,text='Force Stop',x=193,y=72,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=9,font=self.master.FT10BW)
        # self.OPTPOSDUTname.bind("<KeyRelease>",self.UpdateOptimum)
        # self.OPTPOSCoil.bind("<KeyRelease>",self.UpdateOptimum)
    def UpdateOptimum(self):
        try:
            self.master.JsettingsData['OptimumData']['DUTname'] = self.OPTPOSDUTname.get()
            self.master.JsettingsData['OptimumData']['Coil'] = self.OPTPOSCoil.get()
            self.master.Jsettings.update_file(self.master.JsettingsData)
        except Exception as e:
            print(e)
    def PutTestConnectionUI(self):
        # self.master
        self.master.ClearFrame(self.RN_FR1)
        Labels(self.RN_FR1,text="Connect Tester",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        self.TesterIP = Entries(self.RN_FR1,width=20,x=5,y=30,font=self.master.FT12BW,textvar=self.master.JtesterData[self.master.Product][self.master.Mode]['TesterIP'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Buttons(self.RN_FR1,text='Connect',x=170,y=30,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.TesterConnect)
        Labels(self.RN_FR1,text=f"Status    :{self.master.JtesterData[self.master.Product][self.master.Mode]['status']}",x=5,y=65,fg=self.master.Ccodes["black"],bg=self.master.Ccodes["white"],font=self.master.FT10BW)
        Labels(self.RN_FR1,text=f"BoardNo   :{self.master.JtesterData[self.master.Product][self.master.Mode]['BoardNo']}",x=5,y=85,fg=self.master.Ccodes["black"],bg=self.master.Ccodes["white"],font=self.master.FT10BW)
        Labels(self.RN_FR1,text=f"SWVersion :{self.master.JtesterData[self.master.Product][self.master.Mode]['SWVersion']}",x=5,y=105,fg=self.master.Ccodes["black"],bg=self.master.Ccodes["white"],font=self.master.FT10BW)
        Labels(self.RN_FR1,text=f"FWversion :{self.master.JtesterData[self.master.Product][self.master.Mode]['FWversion']}",x=5,y=125,fg=self.master.Ccodes["black"],bg=self.master.Ccodes["white"],font=self.master.FT10BW)   
    #old format 
    def PutQiInputUI(self):
        self.master.ClearFrame(self.RN_FR2)
        Labels(self.RN_FR2,text="Qi Configurations",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        inputs = self.master.JMOIData['TestIP'][self.master.Product][self.master.Mode]
        rw = 27
        for key,value in inputs.items():
            Labels(self.RN_FR2,text=key,font=self.master.FT10BW,x=2,y=rw,width=20,fg=self.master.Ccodes["black"],bg=self.master.Ccodes["white"],anchor=tk.E)
            if value['Type'] =='TextBox':
                Entries(self.RN_FR2,font=self.master.FT10BW,name=value['key'],x=150,y=rw,width=20,textvar=self.master.JQIData[self.master.Product][self.master.Mode][value['key']],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
                #print(self.master.JQIData[self.master.Product][self.master.Mode][value['key']])
            if value['Type'] =='List':
                ListBx(self.RN_FR2,width=20,height=3,font=self.master.FT10BW,name=value['key'],x=150,y=rw,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],values=value['values'], selectedVal =self.master.JQIData[self.master.Product][self.master.Mode][value['key']] )
                rw=rw+40
            elif value['Type'] =='Combo':
                Combo(self.RN_FR2,width=18,state="readonly",font=self.master.FT10BW,val=value['values'],name=value['key'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],x=150,y=rw,selectedVal =self.master.JQIData[self.master.Product][self.master.Mode][value['key']] )
            elif value['Type'] =='Check':
                CheckBtn(self.RN_FR2,font=self.master.FT10BW,name=value['key'],x=150,y=rw,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.JQIData[self.master.Product][self.master.Mode][value['key']])
            rw+=21
        Buttons(self.RN_FR2,text='Load Opti. Data',x=50,y=rw+15,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.LoadOptData)
        Buttons(self.RN_FR2,text='Refresh1',x=150,y=rw+15,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.PutQiInputUI)
        Buttons(self.RN_FR2,text='Update',x=220,y=rw+15,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.UpdateQIJSON)
    #new format for Esdf update
    def PutQiESDFUI(self):
        self.master.ClearFrame(self.RN_FR2)
        Labels(self.RN_FR2,text="Test Execution Preparations",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=45,font=self.master.FT10BW)
        Labels(self.RN_FR2,text="Project Name :",x=5,y=22,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        self.ProjectName = Entries(self.RN_FR2,textvar=self.master.JAllMOIData['Run']['Project'],font=self.master.FT10BW,x=95,y=25,width=15,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Buttons(self.RN_FR2,text='Upload Project',x=210,y=23,width=11,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.UploadProject)
        
        Labels(self.RN_FR2,text="PRMC Code :" if self.master.Mode == "TPR" else "PTMC Code :",x=5,y=50,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        # self.pooldataentry = Entries(self.RN_FR2,textvar=self.master.poolvar.get(),font=self.master.FT10BW,x=95,y=52,width=15,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        # self.pooldatabtn = Buttons(self.RN_FR2,text='Load Pool data',x=210,y=50,width=11,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.PoolData)
        self.select_prmc = Combo(self.RN_FR2,width=13,state="readonly",font=self.master.FT10BW,val=["PRMC" if self.master.Mode == "TPR" else "PTMC","Use Pool Data","Load Pool Data"],selectedVal="PRMC" if self.master.Mode == "TPR" else "PTMC",bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=95,y=52)
        self.pooldataentry = Entries(self.RN_FR2,textvar=self.master.poolvar.get(),font=self.master.FT10BW,x=210,y=52,width=12,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        self.select_prmc.bind("<<ComboboxSelected>>", self.prmc_update)


        self.Exculde_ptmc_prmc_cbtn = CheckBtn(self.RN_FR2,text="Exclude DUT PTMC" if self.master.Mode == "TPR" else "Exclude DUT PRMC",x=5,y=80,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=False)
        self.Random_prmc_ptmc_cbtn = CheckBtn(self.RN_FR2,text="Random PRMC" if self.master.Mode == "TPR" else "Random PTMC",x=150,y=80,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=False)


        self.uploadesdfbtn = Buttons(self.RN_FR2,text='Upload ESDF',x=10,y=120,width=27,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.LoadESDFFile)
        self.testerconfigbtn = Buttons(self.RN_FR2,text='Tester configuration',x=10,y=150,width=27,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.LoadTestConfig)
        self.reportconfigbtn = Buttons(self.RN_FR2,text='Report configuration',x=10,y=180,width=27,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.LoadReportConfig)
        self.AutoValidButton = CheckBtn(self.RN_FR2,text="Auto Validation",x=5,y=290,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=False)
        
        self.createprojbtn = Buttons(self.RN_FR2,text='Create Project',x=150,y=230,width=12,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.Updateall)
        Buttons(self.RN_FR2,text='Refresh',x=30,y=230,width=10,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.RefreshTestExe)
        
        if self.master.Product == 'MPP' and self.master.Mode == 'TPR':
            self.EnableSmartSwich = CheckBtn(self.RN_FR2,font=self.master.FT10BW,text="Enable Smart Plug:",x=5,y=330,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],command=self.UpdateSmartSwitch,selectedVal=self.master.JAllMOIData['Run']['EnableSmartSwitch'])
            self.SelSmarSwitch = Combo(self.RN_FR2,width=10,state="readonly",font=self.master.FT10BW,val=['SP-e6:21','SP-06:da'],selectedVal=self.master.JAllMOIData['SP_MAC'],bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=135,y=335)
            Buttons(self.RN_FR2,text='Connect',x=228,y=333,width=9,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.SSCreateHS)
            self.PowerOffOn = CheckBtn(self.RN_FR2,font=self.master.FT10BW,text="Power OFF & ON DUT before every testcase",x=5,y=360,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],command=self.UpdateSmartSwitch,selectedVal=self.master.JAllMOIData['Run']['PowerOFF&ON'])

        # Buttons(self.RN_FR2,text='Tests Comparison',x=150,y=290,width=15,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=None)

    def prmc_update(self,ts):
        print("testing:",self.select_prmc.get())
        self.pooldataentry.destroy()
        
        if self.select_prmc.get() == ("PRMC" if self.master.Mode == "TPR" else "PTMC"):
            result = "0x010E"
        elif self.select_prmc.get() == "Use Pool Data":
            result = "0x01BD,0x01BF,0x007C,0x0016,0x00AF,0x0051,0x0097,0x013F,0x0082,0x0131,0x7846,0x562A,0xBE50,0x44F7,0xF7F1,0x7FDB,0xD3FB,0x074E,0x9791,0xFE0E,0xE65C,0x011B,0x0116,0x012F,0x018F,0x006E,0x0108,0x0022,0x0072,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x005A,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042,0x0042"
        elif self.select_prmc.get() == "Load Pool Data":
            if self.PoolData() is not None:
                result = self.PoolData() 
            else:
                self.select_prmc.set("PRMC" if self.master.Mode == "TPR" else "PTMC")
                result = "0x010E"

        self.master.poolvar.set(result)
        self.pooldataentry = Entries(self.RN_FR2,textvar=self.master.poolvar.get(),font=self.master.FT10BW,x=210,y=52,width=12,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])


    def DisplayNotal(self):
        self.cpopup = tk.Toplevel()
        self.cpopup.geometry("400x300")
        self.cpopup.title("NOTAL Selection")
        self.cpopup.resizable(False,False)
        ESDF = JsonOperations('json/ESDF.json')
        self.EsdfData_Notal = ESDF.read_file()

        self.Powerprofile="MPP25" 
        self.SupportedSpecification="2.3.0"
        for elements in self.EsdfData_Notal[self.master.Product][self.master.Mode]['Esdf_Elements']:
            if elements['Field']=='PowerProfile':
                self.Powerprofile=elements['Value']
            if elements['Field']=='SupportedSpecification':
                self.SupportedSpecification=elements['Value']
                if self.master.Product=="C3":self.SupportedSpecification=str('V_'+self.SupportedSpecification)
        y=20
        for key,Notal in self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['notal'].items():
            if self.SupportedSpecification in Notal['appModeDescription']:
                if self.Powerprofile in Notal['dutProfile']:
                    CheckBtn(self.cpopup,text=Notal['displayString'],name= key[0].lower() + key[1:],x=0,y=y,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=Notal['isActive'])
                    y+=20

        Buttons(self.cpopup,text='Perform Test Case Comparison',x=30,y=y+20,width=28,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=None) #UpdateNOTALSelection
        self.TestComparison()

    def TestComparison(self):
       
        Tcs=[]
        # List Tcs Which are Applicable to ESDF
        for TestID in self.master.EsdfTestData[self.master.Product][self.master.Mode][self.SupportedSpecification]['Tests'].keys():
            for Profile,ESDF  in self.master.EsdfTestData[self.master.Product][self.master.Mode][self.SupportedSpecification]['Tests'][TestID]['EsdfFields'].items():
                if self.Powerprofile==Profile:
                    if not ESDF[0]:Tcs.append(TestID)
                    else:
                        res=self.ESDFValidate(TestID,ESDF)
                        if len(res)>0:Tcs.extend(res)
        # List Tcs which are Applicable/Not According to NOTAL
        Notal=self.master.EsdfTestData[self.master.Product][self.master.Mode][self.SupportedSpecification]['Notals'][self.Powerprofile]
        if  Notal[0]:
            for NotalName,Tests in Notal[1][0].items():
                if self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['notal'][NotalName]['isActive']:
                    for Test in Tests:
                        if not Test[0]:
                            if Test[1] in Tcs:
                                if Test[2][0]:#Remove according to NOTAL
                                    res=self.ESDFValidate(TestID,Test[2])
                                    if len(res)>0:Tcs.remove(res[0])
                                else:Tcs.remove(Test[1]) 
                        else:
                            if Test[1] not in Tcs:
                                if Test[2][0]:# Add according to NOTAL    
                                    res=self.ESDFValidate(TestID,Test[2])
                                    if len(res)>0:Tcs.append(res[0])
                                else:Tcs.append(Test[1])                        
        # Compare Automation vs Software Test LisTing Through DB
        SupportedSpecification=self.SupportedSpecification if self.master.Product=="C3" else str('MPP_V'+SupportedSpecification)
        SupportedSpecification=SupportedSpecification.replace('.','_')
        self.master.SQLConn.ExecutebyQuery(f"DELETE FROM EsdfTests ")
        SW_TC=self.master.SQLConn.FetchDataFromQRY(  f"SELECT Testcase FROM AllTestcases " )
        SW_Tests= list(SW_TC['Testcase'])if SW_TC is not None else []
        if len(SW_Tests)>0:
            for TC in Tcs:
                self.master.SQLConn.ExecutebyQuery(f"INSERT INTO EsdfTests (mTestID) VALUES ('{TC}')")
                TestID=self.master.SQLConn.FetchDataFromQRY(f"SELECT TEST_DESCRIPTION FROM TestCaseCompleteDetailsView WHERE TEST_NAME='{TC}' AND CTS_VERSION='{SupportedSpecification}' ") 
                if TestID is not None:
                    if list(TestID['TEST_DESCRIPTION'])[0] in SW_Tests:
                        self.master.SQLConn.ExecutebyQuery(f""" UPDATE EsdfTests SET SWTestName = '{list(TestID['TEST_DESCRIPTION'])[0]}', AutomationTestName = '{list(TestID['TEST_DESCRIPTION'])[0]}', Result = 1 WHERE mTestID = '{TC}' """)
                    else:
                        self.master.SQLConn.ExecutebyQuery(f""" UPDATE EsdfTests SET SWTestName = 'NA',AutomationTestName = '{list(TestID['TEST_DESCRIPTION'])[0]}', Result = 0 WHERE mTestID = '{TC}' """ )
           
            # Compare SoftwareTcs vs Automtion Test Listing through DB
            for TC in SW_Tests:
                TestID=self.master.SQLConn.FetchDataFromQRY(f"SELECT TEST_NAME FROM TestCaseCompleteDetailsView WHERE TEST_DESCRIPTION='{TC}' AND CTS_VERSION='{SupportedSpecification}' ") 
                if TestID is not None:
                    if list(TestID['TEST_NAME'])[0] not in Tcs:
                        self.master.SQLConn.ExecutebyQuery(f""" INSERT INTO EsdfTests (mTestID, AutomationTestName, Result, SWTestName) VALUES ('{list(TestID['TEST_NAME'])[0]}', 'NA', 0, '{TC}') """ )
       
        #Export to Excelfrom DB


    def ESDFValidate(self,TestID,ESDF):
        Tcs=[]
        Applicability=True
        for Fields in ESDF[1]:
            for FieldName ,values in Fields.items(): 
                for elements in self.EsdfData_Notal[self.master.Product][self.master.Mode]['Esdf_Elements']:
                    if elements['Field']==FieldName:
                        if values[2]=="Boolean": 
                            if elements['Value']!=values[0]:Applicability=False
                        else:
                            if not self.Comp( values,elements['Value']):Applicability=False
                        break
        if Applicability: Tcs.append(TestID)
        return Tcs


    def Comp(self,values,RecivedVal):
        expected_values=values[0]
        comp=values[1]
        match comp:
            case "NEQ": return expected_values != RecivedVal
            case "GT":  return RecivedVal > expected_values
            case "GTE": return RecivedVal >= expected_values
            case "LT":  return RecivedVal < expected_values
            case "LTE": return RecivedVal <=expected_values
            case "IN": return expected_values in RecivedVal
            case "NOT-IN": return expected_values not in RecivedVal
            case "EQL": return expected_values == RecivedVal
            case "ANY": return True
                      
     
    def UpdateNOTALSelection(self):
        remarks = []
        errors = False
        if len(self.cpopup.winfo_children()) > 0:
            for wdgt in self.cpopup.winfo_children():
                if wdgt.winfo_class() in ['Checkbutton']:
                    try:
                        Notal=wdgt.winfo_name()[0].upper()+wdgt.winfo_name()[1:]
                        if wdgt.getvar(wdgt.winfo_name())=="0":
                            self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['notal'][Notal]["isActive"]=False
                        else:self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['notal'][Notal]["isActive"]=True
                    except Exception as e:
                        errors=True
                        remarks.append(f"{wdgt.winfo_name()} "+str(e))
        rm = '|'.join(remarks) if len(remarks)> 0 else 'All the fields are updated'
        if errors ==False:
            self.master.TesterConfig.update_file(self.master.TesterConfigData)
            self.Updateall()

        else:
            messagebox.showinfo("Not Updated:",rm)

    #Update Testview list by selected phase and offset combination.  

    def RefreshTestExe(self):
        self.ProjectName.config(state="normal")
        self.ProjectName.delete(0, tk.END)
        self.ProjectName.insert(0, "")
        self.pooldataentry.config(state="normal")
        self.pooldatabtn.config(state="normal")
        self.uploadesdfbtn.config(state="normal")
        self.testerconfigbtn.config(state="normal")
        self.createprojbtn.config(state="normal")

    def UploadProject(self):
        # self.master.SQLConn.ExecutebyQuery(f"UPDATE TestCaseCompleteDetailsView SET TestResults = 'NA'")
        folder_path = filedialog.askdirectory(initialdir=r"C:\GRL\GRL-C3-MP-TPR\Report")
        bkjson_path = ''
        BKJSONData=None
        testresults = []
        if folder_path:
            for file in os.listdir(folder_path):
                if file.endswith(".gproj"):
                    bkjson_path = os.path.join(folder_path,file)
                    # print(bkjson_path)
                    break
            APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutClearCapture']).PutRequest()
            loadproj = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutloadGProj'],json={"Uploadtype":"gprojReport","gProjFilePath":bkjson_path}).PutRequest()
            if loadproj == 200:
                self.master.projloaded = True
                projconfigdata = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetProjectConfiguration'], retype='json').GetRequest()
                APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['UpdateProjectConfiguration'],json=projconfigdata).PutRequest()
                APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutApplicationActiveStatus']+"/false").PutRequest()

                # with open(bkjson_path, "r",encoding="utf-8") as rf:
                #     BKJSONData = json.load(rf)
                with open(bkjson_path, "rb") as rf:   # binary mode (no encoding needed)
                    BKJSONData = orjson.loads(rf.read())
                for TCdata in BKJSONData['testBkpTestResultsandPath']:
                    # print(TCdata['testcaseDetails']['m_DisplayName'],TCdata['testinformation']['TestResult'])
                    testresults.append([TCdata['testcaseDetails']['m_DisplayName'],TCdata['testinformation']['TestResult']])
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases SET TestResult = '{TCdata['testinformation']['TestResult']}' WHERE Testcase = '{TCdata['testcaseDetails']['m_DisplayName']}'")
                
                # print("pooldata:",BKJSONData['testBkpProjectConfiguration']['TesterConfigurationModel']['prmcCode' if self.master.Mode == "TPR" else 'ptmcCode'])

                self.ProjectName = Entries(self.RN_FR2,textvar=BKJSONData['testBkpProjectConfiguration']['ProjectConfigurationModel']['projectName'],font=self.master.FT10BW,x=95,y=25,width=15,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
                self.UpdateMOI()
                self.ProjectName.config(state="disabled")
                self.pooldataentry.config(state="disabled")
                self.pooldatabtn.config(state="disabled")
                self.uploadesdfbtn.config(state="disabled")
                self.testerconfigbtn.config(state="disabled")
                self.createprojbtn.config(state="disabled")
            else: messagebox.showerror("Load Project", "Project not loaded, please try again")
            self.master.alloptimumcoils = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetCoilFilter'], retype='json').GetRequest()
            # print(self.master.alloptimumcoils)
        else:messagebox.showerror("Load Project folder", "Please load the proper project folder")
    
    def Rerun(self):
        base_path = r"C:\GRL\GRL-C3-MP-TPR\Report"

        # Get only subfolders starting with "apple"
        folders = [
            os.path.join(base_path, d)
            for d in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, d)) and d.lower().startswith(self.ProjectName.get())
        ]

        if folders:
            folder_path = max(folders, key=os.path.getmtime)
            print("Latest apple folder:", folder_path)
        else:
            print("No folders starting with 'apple' found.")

        bkjson_path = ''
        BKJSONData=None
        testresults = []
        if folder_path:
            for file in os.listdir(folder_path):
                if file.endswith(".gproj"):
                    bkjson_path = os.path.join(folder_path,file)
                    print(bkjson_path)
                    break
        # with open(bkjson_path, "r",encoding="utf-8") as rf:
        #     BKJSONData = json.load(rf)
        with open(bkjson_path, "rb") as rf:   # binary mode
            BKJSONData = orjson.loads(rf.read())
        for TCdata in BKJSONData['testBkpTestResultsandPath']:
            # print(TCdata['testcaseDetails']['m_DisplayName'],TCdata['testinformation']['TestResult'])
            testresults.append([TCdata['testcaseDetails']['m_DisplayName'],TCdata['testinformation']['TestResult']])
            self.master.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases SET TestResult = '{TCdata['testinformation']['TestResult']}' WHERE Testcase = '{TCdata['testcaseDetails']['m_DisplayName']}'")

    def Updateall(self):
        if self.ProjectName.get():

            #testing
            # self.UpdateTesterConfig()

            VerifyESDF = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutVerifyEsdfData'])
            MainESDF = JsonOperations('json/ESDF.json')
            MainESDFData = MainESDF.read_file()
            #Verify the ESDF data
            # print("esdf:",MainESDFData[self.master.Product][self.master.Mode])
            VerifyESDF.json = MainESDFData[self.master.Product][self.master.Mode]
            APIres = VerifyESDF.PutRequest()
            if APIres == 200:
                self.update_logs("UI","ESDF Data Verified Successfully")
                #Up
            else:self.update_logs("UI","Issue in ESDF Data Verification")   

            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['IsNewProjCreation']+"true").GetRequest())
            # print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutApplicationActiveStatus']+"/false").PutRequest())
            # print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutApplicationActiveStatus']+"/true").PutRequest())
            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetChannelList']).GetRequest())
            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutClearCapture']).PutRequest())
            self.CreateProjectByPopUp()
            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['IsNewProjCreation']+"false").GetRequest())
            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetTestCaseList']).GetRequest())
            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetOptimumCoilValues']).GetRequest())
            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetCoilFilter']).GetRequest())
            print(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetCoilFilter']).GetRequest())

            # if bool(int(self.EnableOptimum.getvar(self.EnableOptimum.winfo_name()))):
            #     PutcoilAPI = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutOptimumCoilValues'])
            #     PutcoilAPI.json = self.OptimumCoilValues
            #     res= PutcoilAPI.PutRequest()
            #     print(res)
    
            self.master.alloptimumcoils = list(APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetCoilFilter'], retype='json').GetRequest())
            print("alloptimumcoils:",self.master.alloptimumcoils)

            self.UpdateMOI()
        else: messagebox.showerror("Project Creation", "Project Name should not be empty")
               
        # print(APIOperations(url="http://localhost:2002/api/TestConfiguration/GetProjectConfiguration?IsNewProjCreation=true").GetRequest())
        # print(APIOperations(url="http://localhost:2002/api/App/PutApplicationActiveStatus/false").PutRequest())
        # print(APIOperations(url="http://localhost:2002/api/App/PutApplicationActiveStatus/true").PutRequest())
        # print(APIOperations(url="http://localhost:2002/api/Plot/GetAllChannelData?startTime=0&stopTime=0&numberOfSamples=2000").GetRequest())
        # print(APIOperations(url="http://localhost:2002/api/Plot/GetChannelList").GetRequest())
        # print(APIOperations(url="http://localhost:2002/api/Plot/PutClearCapture").PutRequest())
        # self.CreateProjectByPopUp()
        # print(APIOperations(url="http://localhost:2002/api/TestConfiguration/GetProjectConfiguration?IsNewProjCreation=false").GetRequest())
        # print(APIOperations(url="http://localhost:2002/api/TestConfiguration/GetTestCaseList").GetRequest())
        # print(APIOperations(url="http://localhost:2002/api/TestConfiguration/GetOptimumCoilValues").GetRequest())
        # print(APIOperations(url="http://localhost:2002/api/TestConfiguration/GetCoilFilter").GetRequest())
        # print(APIOperations(url="http://localhost:2002/api/TestConfiguration/GetPositionFilter").GetRequest())

    def PoolData(self):
        filename = askopenfilename()
        pooldata = []
        if filename.endswith('.csv'):
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    pooldata.append(row[0])
            result = ",".join(pooldata)
            print(result)
            # self.master.poolvar.set(result)
            return result
            # Entries(self.RN_FR2,textvar=self.master.poolvar.get(),font=self.master.FT10BW,x=95,y=52,width=15,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        else:
            messagebox.showerror("Pool data", "Enter proper pool data csv file")

    def SSCreateHS(self):
        # resp = messagebox.askokcancel("SmartPlug Setup","Please create and connect to following mobile hotspot in your laptop:\n Name:GRLSmartPlug\n Password:G%SPHotSpot%L\n Band:2.4Ghz")
        # print(resp)
        # if resp:
        #     self.master.smartplug_obj.get_connected_devices(self.SelSmarSwitch.get())

        self.WIFI_details = {"SP-06:da":{'user_name':'GRLSmartPlug','password':'G%SPHotSpot%L',}, "SP-e6:21":{'user_name':'GRL_SP:e6:21','password':"G%GRL_sp%L"}}
        self.sppopup = tk.Toplevel()
        self.sppopup.geometry("300x120")
        self.sppopup.title("SmartPlug Setup")
        self.sppopup.resizable(False,False)
        self.wifilbl = Texts(self.sppopup,text=f"Please create this mobile hotspot in your Laptop \nand plug-in smartplug then click 'OK'",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        # self.wifilbl = Texts(self.sppopup,text=f"Wi-fi Name       : {self.WIFI_details[self.SelSmarSwitch.get()]['user_name']}",x=0,y=40,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        # self.wifipwdlbl = Texts(self.sppopup,text=f"Wi-fi Password : {self.WIFI_details[self.SelSmarSwitch.get()]['password']}",x=0,y=60,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        # self.wifilbl = Texts(self.sppopup,text=f"Band                   : 2.4 GHz",x=0,y=80,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        self.wifi1lbl = Texts(self.sppopup,text=f"{'Wi-fi Name':<19}: {self.WIFI_details[self.SelSmarSwitch.get()]['user_name']}",x=0, y=40,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        self.wifipwdlbl = Texts(self.sppopup,text=f"{'Wi-fi Password':<17}: {self.WIFI_details[self.SelSmarSwitch.get()]['password']}",x=0, y=60,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        self.bandlbl = Texts(self.sppopup,text=f"{'Band':<25}: 2.4 GHz",x=0, y=80,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        print(self.SelSmarSwitch.get())
        Buttons(self.sppopup,text='OK',x=200,y=90,width=8,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.Connect_to_SP)
        

    def Connect_to_SP(self):
        self.master.smartplug_obj.get_connected_devices(self.SelSmarSwitch.get())
        self.sppopup.withdraw()
        

    def LicenseUI(self):
        if self.master.Product == 'MPP' and self.master.Mode == 'TPR':
            self.master.ClearFrame(self.RN_FR8)
            Labels(self.RN_FR8,text="License Verification",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=45,font=self.master.FT10BW)
            self.PermLicense = CheckBtn(self.RN_FR8,text="Permanent License",x=10,y=30,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=True)
            self.Perm_DemoLicense = CheckBtn(self.RN_FR8,text="Perm & Demo License",x=10,y=60,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=True)
            self.DemoLicense = CheckBtn(self.RN_FR8,text="Demo License",x=10,y=90,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=True)
            self.LicStartButton = Buttons(self.RN_FR8,text='Verify Licenses',x=10,y=120,width=15,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=lambda:threading.Thread(target=self.LicenseAutomate,daemon=True).start())
            Buttons(self.RN_FR8,text='Force Stop',width=13,x=150,y=120,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW, command=self.ForceStopProcess)
            #Buttons(self.RN_FR8,text='Update to Initia License',x=70,y=170,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=licobj.initialLicense)
    
    def LicenseAutomate(self):
        if self.is_npcap_installed():
            if self.master.TesterConnection and self.TesterIP.get() == "192.168.255.1":
                if bool(int(self.PermLicense.getvar(self.PermLicense.winfo_name()))) or bool(int(self.Perm_DemoLicense.getvar(self.Perm_DemoLicense.winfo_name()))) or bool(int(self.DemoLicense.getvar(self.DemoLicense.winfo_name()))):
                    messagebox.showinfo("License Verification", f"{2*(int(self.PermLicense.getvar(self.PermLicense.winfo_name()))+int(self.Perm_DemoLicense.getvar(self.Perm_DemoLicense.winfo_name()))+int(self.DemoLicense.getvar(self.DemoLicense.winfo_name())))} hours to finish execution")
                    self.update_logs("UI","License Verification started")
                    self.Disable_Frames(self.RN_FR2)
                    self.Disable_Frames(self.RN_FR3)
                    self.Disable_Frames(self.RN_FR4)
                    self.Disable_Frames(self.RN_FR5)
                    self.LicStartButton.configure(state="disabled")
                    self.LicValid_flag = True
                    self.master.JsettingsData['_stop_flag'] = False
                    self.master.Jsettings.update_file(self.master.JsettingsData)
                    ethernet_link = GrlEthernetLink_C2(bool(int(self.PermLicense.getvar(self.PermLicense.winfo_name()))),bool(int(self.Perm_DemoLicense.getvar(self.Perm_DemoLicense.winfo_name()))),bool(int(self.DemoLicense.getvar(self.DemoLicense.winfo_name()))),self.master.Mode)
                    threading.Thread(target=self.StatusRefresh,daemon=True).start()
                    ethernet_link.PreExecute()
                    self.update_logs("UI","License Verification Finished")
                    self.LicValid_flag = False
                    self.Enable_frame(self.RN_FR2)
                    self.Enable_frame(self.RN_FR3)
                    self.Enable_frame(self.RN_FR4)
                    self.Enable_frame(self.RN_FR5)
                    self.LicStartButton.configure(state="normal")
                else: messagebox.showwarning("License update", "Select atleast one license for verification")
            else: messagebox.showwarning("License update", "Make sure tester is connected to static IP")
        else: messagebox.showwarning("License update", "Please install 'npcap-1.82' which is available in the Resources folder, to perform License verification")

    def Disable_Frames(self,frame):
        for child in frame.winfo_children():
            if child.winfo_class() != 'Frame':
                child.configure(state='disabled')
    def Enable_frame(self,frame):
        for child in frame.winfo_children():
            if child.winfo_class() != 'Frame':
                child.configure(state='normal')
    def StatusRefresh(self):
        while self.LicValid_flag:
            time.sleep(1)
            self.LogsUI()
            if not self.LicValid_flag: break
    
    def is_npcap_installed(self):
        try:
            output = subprocess.check_output('sc query npcap', shell=True, stderr=subprocess.STDOUT)
            if b"RUNNING" in output or b"STOPPED" in output:
                return True
        except subprocess.CalledProcessError:
            pass
        return False

    def LoadTestConfig(self):
        self.cpopup = tk.Toplevel()
        self.cpopup.geometry("250x200")
        self.cpopup.title("Tester Configuration")
        self.cpopup.resizable(False,False)
        if self.master.Product == "MPP":
            self.KiP1 = Labels(self.cpopup,text="Ki_actual_P1(0,0):",x=0,y=0,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
            self.KiP1En = Entries(self.cpopup,name="ki1",textvar=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['kiActual_P1'],x=110,y=0,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
            self.KiP2 = Labels(self.cpopup,text="Ki_actual_P2(2,2):",x=0,y=30,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
            self.KiP2En = Entries(self.cpopup,name="ki2",textvar=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['kiActual_P2'],x=110,y=30,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
            self.EnableOptimum = CheckBtn(self.cpopup,text="Enable Optimum Position",x=0,y=50,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isOptimumCoilEnable'])
            if self.master.Mode == "TPR":
                self.EnableAmbient = CheckBtn(self.cpopup,text="Enable Ambient Temperature Check",x=0,y=70,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['ambientTempCheck'])
                self.EnableCoilRemovePlace = CheckBtn(self.cpopup,text="Enable Coil Remove/Place popups",x=0,y=90,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isCoilPlacePopupEnabled'])
            elif self.master.Mode == "TPT":
                self.EnableDUT = CheckBtn(self.cpopup,text="Enable popup to control DUT power",x=0,y=70,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isDUTPopupEnabled'])
                self.EnableEDS = CheckBtn(self.cpopup,text="Enable TPT popup for PRx EDS packet",x=0,y=90,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isEDSPopUpReq'])
            self.KiP1En.bind('<KeyRelease>',self.ValidateKi)
            self.KiP2En.bind('<KeyRelease>',self.ValidateKi)
        elif self.master.Product == "C3":
            if self.master.Mode == "TPR":
                Labels(self.cpopup,text="Basic device identifier:",x=0,y=0,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
                self.bdi = Entries(self.cpopup,textvar=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['bdiValue'],x=130,y=0,width=15,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
                self.EnableOptimum = CheckBtn(self.cpopup,text="Enable Optimum Position",x=0,y=30,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isOptimumCoilEnable'])
                self.MultiPings = CheckBtn(self.cpopup,text="PTx Supports Multi pings",x=0,y=50,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isPtxSupportsMultiPings'])
                self.EnableCoilRemovePlace = CheckBtn(self.cpopup,text="Enable Coil Remove/Place popups",x=0,y=70,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isCoilPlacePopupEnabled'])
            elif self.master.Mode == "TPT":
                Labels(self.cpopup,text="ft (kHz):",x=0,y=0,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
                self.ft = Entries(self.cpopup,textvar=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['referenceResonance'],x=60,y=0,width=15,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
                Labels(self.cpopup,text="Qt:",x=0,y=20,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
                self.qt = Entries(self.cpopup,textvar=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['referenceQuality'],x=60,y=20,width=15,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
                self.EnableOptimum = CheckBtn(self.cpopup,text="Enable Optimum Position",x=0,y=50,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isOptimumCoilEnable'])
                self.EnableDUTpopup = CheckBtn(self.cpopup,text="Enable Popup to control DUT power",x=0,y=75,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isDUTPopupEnabled'])
                self.EnableEDSpopup = CheckBtn(self.cpopup,text="Enable TPT popup for PRx EDS",x=0,y=100,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isEDSPopUpReq'])

        Buttons(self.cpopup,text='OK',x=50,y=130,width=10,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.UpdateTesterConfig)
    
    def LoadReportConfig(self):
        self.Rpopup = tk.Toplevel()
        self.Rpopup.geometry("270x230")
        self.Rpopup.title("Report Configuration")
        self.Rpopup.resizable(False,False)
        y=0
        for Field in  self.master.TesterConfigData[self.master.Product][self.master.Mode]['ReportConfigurationModel']:
            Labels(self.Rpopup,text=Field,x=5,y=y,fg=self.master.Ccodes["black"],font=self.master.FT10BW)
            Entries(self.Rpopup,name=Field,textvar=self.master.TesterConfigData[self.master.Product][self.master.Mode]['ReportConfigurationModel'][Field],x=120,y=y,font=self.master.FT10BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
            y+=25
        Buttons(self.Rpopup,text='OK',x=50,y=190,width=10,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.UpdateReportConfig)
    
    def UpdateReportConfig(self):

        if len(self.Rpopup.winfo_children()) > 0:
            for wdgt in self.Rpopup.winfo_children():
                if wdgt.winfo_class() in ['Entry']:
                        self.master.TesterConfigData[self.master.Product][self.master.Mode]['ReportConfigurationModel'][wdgt.winfo_name()]=wdgt.get()
            self.master.TesterConfig.update_file(self.master.TesterConfigData)
            self.Rpopup.withdraw()
            self.update_logs("UI","Report Config Data updated Successfully")

    def ValidateKi(self,ns):
        try:
            ch = ns.widget.winfo_name()
            val = float(self.KiP1En.get()) if "ki1" in ch else float(self.KiP2En.get())
            if 0 <= val <= 1.0:
                if "ki1" in ch:
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['kiActual_P1'] = val
                else:
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['kiActual_P2'] = val
                self.master.TesterConfig.update_file(self.master.TesterConfigData)
            else:
                messagebox.showwarning("Ki value", "Please enter Ki in the limit(0,1.0)")  
        except Exception as e:
            print(e)
    def UpdateTesterConfig(self):
        #keys = {}
        try:
            print("EnableOptimum:",bool(int(self.EnableOptimum.getvar(self.EnableOptimum.winfo_name()))))
            self.LoadOptiButton.config(state="disabled" if not bool(int(self.EnableOptimum.getvar(self.EnableOptimum.winfo_name()))) else "normal")
            if self.master.Product == "MPP":
                Kp1 = float(self.KiP1En.get())
                Kp2 = float(self.KiP2En.get())
                if Kp1>=0 and Kp1<=1:
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['kiActual_P1'] = Kp1
                else:self.update_logs("UI","Ki_Actual_P1 is not in limit, provivide value from 0-1")
                if Kp2>=0 and Kp2<=1:
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['kiActual_P2'] = Kp2
                else:self.update_logs("UI","Ki_Actual_P2 is not in limit, provivide value from 0-1")
                self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isOptimumCoilEnable'] = bool(int(self.EnableOptimum.getvar(self.EnableOptimum.winfo_name())))
                if self.master.Mode == "TPR":
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['ambientTempCheck'] = bool(int(self.EnableAmbient.getvar(self.EnableAmbient.winfo_name())))
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isCoilPlacePopupEnabled'] = bool(int(self.EnableCoilRemovePlace.getvar(self.EnableCoilRemovePlace.winfo_name())))
                elif self.master.Mode == "TPT":
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isDUTPopupEnabled'] = bool(int(self.EnableDUT.getvar(self.EnableDUT.winfo_name())))
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isEDSPopUpReq'] = bool(int(self.EnableEDS.getvar(self.EnableEDS.winfo_name())))
            elif self.master.Product == "C3":
                self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isOptimumCoilEnable'] = bool(int(self.EnableOptimum.getvar(self.EnableOptimum.winfo_name())))
                if self.master.Mode == "TPR":
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['bdiValue'] = self.bdi.get()
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isPtxSupportsMultiPings'] = bool(int(self.MultiPings.getvar(self.MultiPings.winfo_name())))
                    self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isCoilPlacePopupEnabled'] = bool(int(self.EnableCoilRemovePlace.getvar(self.EnableCoilRemovePlace.winfo_name())))
            self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['prmcCode' if self.master.Mode == "TPR" else "ptmcCode"] = self.master.poolvar.get()
            self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['prmc_Ptmc_Source'] = self.select_prmc.get()
            self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isExcludeDutPrmc'] = bool(int(self.Exculde_ptmc_prmc_cbtn.getvar(self.Exculde_ptmc_prmc_cbtn.winfo_name())))
            self.master.TesterConfigData[self.master.Product][self.master.Mode]['TesterConfigurationModel']['isRandomPrmc'] = bool(int(self.Random_prmc_ptmc_cbtn.getvar(self.Random_prmc_ptmc_cbtn.winfo_name())))
            self.master.TesterConfig.update_file(self.master.TesterConfigData)
            self.cpopup.withdraw()
            self.update_logs("UI","Tester Config Data updated Successfully")
        except Exception as e:
            self.update_logs("UI",f"Exception:{e}")
        # self.CreateProjectByPopUp()
    def LoadESDFFile(self):
        try:
            VerifyESDF = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutVerifyEsdfData'])
            filename = askopenfilename()
            if '.json' in filename:
                #convert the file data
                ESDFobj = JsonOperations(filename)
                ESDFData = ESDFobj.read_file()
                MainESDF = JsonOperations('json/ESDF.json')
                
                MainESDFData = MainESDF.read_file()
           
                rawdata = self.Esdf_converter(ESDFData)
                MainESDFData[self.master.Product][self.master.Mode]['Esdf_Elements'] = rawdata['Esdf_Elements']
                MainESDF.update_file(MainESDFData)
                
                self.update_logs("UI","ESDF Data updated Successfully")
                
                #Verify the ESDF data
                VerifyESDF.json = MainESDFData[self.master.Product][self.master.Mode]
                APIres = VerifyESDF.PutRequest()
                if APIres == 200:
                    self.update_logs("UI","ESDF Data Verified Successfully")
                else:self.update_logs("UI","ESDF ISSUE, new fileds are included in this software.")
            else:messagebox.showinfo("Wrong ESDF File:","Please choose .json file.")

        except Exception as e:
            self.update_logs("UI",f"Exception:{e}")

    def Esdf_converter(self,input_data):
        # Define units for specific fields
        field_units = {"GuaranteedLoadPower": "W","PotentialLoadPower":"W","PotentialLoadPowerEP":"W"}
        output = {"Esdf_Elements": []}
        for key, value in input_data.items():
            element = {
                "Field": key,
                "Value": value,
                "unit": field_units.get(key, "")
            }
            output["Esdf_Elements"].append(element)
        return output
        
        
    def CreateProjectByPopUp(self):
        try:
            # print("ProjectName:",self.ProjectName.get())
            # self.ProjectName = tk.simpledialog.askstring("Input", "Enter ProjectName:")
            if self.ProjectName.get() is not None:
                MainESDF = JsonOperations('json/ESDF.json')
                MainESDFData = MainESDF.read_file()
                TesterConf = JsonOperations('json/TesterConfig.json')
                TesterConfData = TesterConf.read_file()
                #call the Project creation API
                ProjectCreate = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutProjectFolder'])
                ProjectCreate.json = {"EsdfConfigurationModel":{"Esdf_Elements":MainESDFData[self.master.Product][self.master.Mode]["Esdf_Elements"]},
                                    "ProjectConfigurationModel":{"projectName":self.ProjectName.get(),"projectModePreCompliance":False,"projectAppMode":"MPP_TPR" if self.master.Mode == "TPR" else "MPP_TPT"},
                                    "ReportConfigurationModel":TesterConfData[self.master.Product][self.master.Mode]['ReportConfigurationModel'],
                                    "TesterConfigurationModel":TesterConfData[self.master.Product][self.master.Mode]['TesterConfigurationModel']}
                                    
                APIres = ProjectCreate.PutRequest()
                # print("ProjectCreate:",APIres,ProjectCreate.json)
                if APIres == 200:
                    self.update_logs("UI",f"Project {self.ProjectName.get()} created succesfully.")
                else:self.update_logs("UI","Project Creation Failed.")
            else:self.update_logs("UI","Project Creation Cancelled.")
        except Exception as e:
            self.update_logs("UI",f"Exception:{e}")
    def LoadOptData(self):
        PutcoilAPI = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutOptimumCoilValues'])
        #Load Data
        filename = askopenfilename()
        if filename.endswith('.xml') or filename.endswith('.json'):
            if filename.endswith('.xml'):
                with open(filename, 'r', encoding='utf-8') as f:
                    xml_data = f.read()
                root = ET.fromstring(xml_data)
                coil_value_list = []
                for coil in root.findall('Coil_Values'):
                    key = coil.find('key').text
                    value = coil.find('value').text  #float(coil.find('value').text)
                    coil_value_list.append({"key":key,"value":value})
                self.OptimumCoilValues = {"coilValue":coil_value_list,"sSCheck":True}

            elif filename.endswith('.json'):
                # with open(filename, 'r', encoding='utf-8') as f:
                #     json_data = json.load(f)
                with open(filename, "rb") as f:   
                    json_data = orjson.loads(f.read())
                coil_value_list = []
                allcoils = json_data["Optimum"]["Coil_Values"]
                self.OptimumCoilValues = {"coilOptData":json_data["Optimum"]["Coil_Values"]}

            PutcoilAPI.json = self.OptimumCoilValues
            res= PutcoilAPI.PutRequest()
            # print(res)
            if res == 200:
                self.master.JQIData[self.master.Product][self.master.Mode]['ssCheckForTestcases']=True
                self.master.JQI.update_file(self.master.JQIData)
                self.update_logs("UI",f"Optimum Coil Values loaded: {", ".join(f"{c['coilType']} : {c['value']}" for c in json_data["Optimum"]["Coil_Values"])}")
                messagebox.showinfo("Optimum values",f"Optimum Coil Values loaded:\n" +"\n".join(f"{c['coilType']} : {c['value']}" for c in json_data["Optimum"]["Coil_Values"]))
            else: messagebox.showerror("Optimum file", "Please load only .xml or .json optimum files")
        else: messagebox.showerror("Optimum file", "Please load only .xml or .json optimum files")

                            
    def PutTestSel(self):
        self.master.ClearFrame(self.RN_FR3)
        Labels(self.RN_FR3,text="Prepare Tests For Run",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=43,font=self.master.FT10BW)
        yax = 30
        #Get Coils
        Coils = offset = Phase = []
        Coils_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='Coil' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
        if Coils_DF is not None:
            Coils = list(Coils_DF['Name'])
            # if not(len(Coils)==1 and 'NA' in Coils):
                # Labels(self.RN_FR3,text='Coils:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
                # self.selectedcoils = DropdownWithCheckboxes(self.RN_FR3,options=Coils,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
                # yax += 25
        else:
            Coils= []
            # self.update_logs("UI","Unable to fetch Coils from DB.!") 
        Labels(self.RN_FR3,text='Coils:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        self.selectedcoils = DropdownWithCheckboxes(self.RN_FR3,options=Coils,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
        yax += 25
        print("Coils:",Coils)
        if self.master.Product != 'C3':
            #Get Position
            POS_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='offset' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
            if POS_DF is not None:
                offset = list(POS_DF['Name'])
                # if not(len(offset)==1 and 'NA' in offset):
                #     Labels(self.RN_FR3,text='Positions:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
                #     self.selectedpositions = DropdownWithCheckboxes(self.RN_FR3,options=offset,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
                #     yax += 25
            else:
                offset = []
                # self.update_logs("UI","Unable to fetch positions from DB.!")
            Labels(self.RN_FR3,text='Positions:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
            self.selectedpositions = DropdownWithCheckboxes(self.RN_FR3,options=offset,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
            yax += 25
       #Get Phases
        Phase_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='Phase' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
        if Phase_DF is not None:
            Phase = list(Phase_DF['Name'])
            # if not(len(Phase)==1 and 'NA' in Phase):
            #     Labels(self.RN_FR3,text='Phases:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
            #     self.selectedphases = DropdownWithCheckboxes(self.RN_FR3,options=Phase,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
            #     yax += 25
        else:
            Phase = []
            # self.update_logs("UI","Unable to fetch Phase from DB.!")
        Labels(self.RN_FR3,text='Phases:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        self.selectedphases = DropdownWithCheckboxes(self.RN_FR3,options=Phase,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
        yax += 25

        # #Get Categories
        # CAT_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='Cat' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
        # if CAT_DF is not None:
        #     cat = list(CAT_DF['Name'])
        #     # if not(len(cat)==1 and 'NA' in cat):
        #     #     Labels(self.RN_FR3,text='Categories:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        #     #     self.selectedcertifications = DropdownWithCheckboxes(self.RN_FR3,options=cat,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
        #     #     yax += 25
        # else:
        #     cat = []
        #     # self.update_logs("UI","Unable to fetch Categories from DB.!")
        # Labels(self.RN_FR3,text='Categories:',font=self.master.FT12BW,x=1,y=yax,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.selectedcertifications = DropdownWithCheckboxes(self.RN_FR3,options=cat,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=yax+5)
        # yax += 25

        



        # #Get Position
        # POS_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='offset' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
        # if POS_DF is not None:
        #     offset = list(POS_DF['Name'])
        # else:
        #     offset = []
        #     self.update_logs("UI","Unable to fetch positions from DB.!")
        # #Get Categories
        # CAT_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='Cat' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
        # if CAT_DF is not None:
        #     cat = list(CAT_DF['Name'])
        # else:
        #     cat = []
        #     self.update_logs("UI","Unable to fetch Categories from DB.!")
        # #Get Coils
        # Coils_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='Coil' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
        # if Coils_DF is not None:
        #     Coils = list(Coils_DF['Name'])
        # else:
        #     Coils= []
        #     self.update_logs("UI","Unable to fetch Coils from DB.!")
        # #Get Phases
        # Phase_DF =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name from TestFilters where FilterType='Phase' and Product='{self.master.Product}' and Mode='{self.master.Mode}'")
        # if Phase_DF is not None:
        #     Phase = list(Phase_DF['Name'])
        # else:
        #     Phase = []
        #     self.update_logs("UI","Unable to fetch Phase from DB.!")

        # Labels(self.RN_FR3,text='Coils:',font=self.master.FT12BW,x=1,y=30,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.selectedcoils = DropdownWithCheckboxes(self.RN_FR3,options=Coils,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=35)

        # Labels(self.RN_FR3,text='Positions:',font=self.master.FT12BW,x=1,y=70,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.selectedpositions = DropdownWithCheckboxes(self.RN_FR3,options=offset,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=75)

        # Labels(self.RN_FR3,text='Phases:',font=self.master.FT12BW,x=1,y=110,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.selectedphases = DropdownWithCheckboxes(self.RN_FR3,options=Phase,width=180,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=100,y=115)
        


        # Labels(self.RN_FR3,text='Coils:',font=self.master.FT12BW,x=100,y=25,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.AllCoils = CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='e',text="All Coils",x=100,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=lambda:self.SelectAll('e'))
        # rw=75
        # tmpid = 0
        # for key in Coils:
        #     #print(key,value)
        #     CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='c-'+str(tmpid),text=key,x=100,y=rw,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=self.DefaultCheck)
        #     tmpid+=1
        #     rw+=19

        # Labels(self.RN_FR3,text='Positions:',font=self.master.FT12BW,x=1,y=25,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.AllPositions = CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='f',text="All Positions",x=1,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=lambda:self.SelectAll('f'))
        # rw=75
        # tmpid = 0
        # for key in offset:
        #     #print(key,value)
        #     CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='o-'+str(tmpid),text=key,x=1,y=rw,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=self.DefaultCheck)
        #     tmpid+=1
        #     rw+=19

        # Labels(self.RN_FR3,text='Category:',font=self.master.FT12BW,x=1,y=rw+20,width=8,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.AllCategories = CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='g',text="All Categories",x=1,y=rw+45,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=lambda:self.SelectAll('g'))
        # rw=rw+70
        # tmpid = 0
        # for key in cat:
        #     #print(key,value)
        #     CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='a-'+str(tmpid),text=key,x=1,y=rw,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=self.DefaultCheck)
        #     tmpid+=1
        #     rw+=19

        # rw= 180
        # Labels(self.RN_FR3,text='Phases:',font=self.master.FT12BW,x=100,y=130,width=15,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        # self.AllPhases = CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='h',text="All Phases",x=100,y=155,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=lambda:self.SelectAll('h'))
        # tmpid = 0
        # for key in Phase:
        #     CheckBtn(self.RN_FR3,font=self.master.FT10BW,name='p-'+str(tmpid),text=key,x=100,y=rw,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=self.DefaultCheck)
        #     tmpid+=1
        #     rw+=19
        Buttons(self.RN_FR3,text='Refresh',x=4,y=420,width=20,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.UpdateMOI)
        Buttons(self.RN_FR3,text='Apply Filter',x=155,y=420,width=20,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.GenerateTestsForRun)
        # #Update checkboxes
        # self.AutoCheckPosPhase()
        # self.DefaultCheck()
    #Check / Uncheck all checkbuttons under it.        
    def SelectAll(self,WidName):
        try:
            if len(self.RN_FR3.winfo_children()) > 0:
                for wdgt in self.RN_FR3.winfo_children():
                    if wdgt.winfo_class() in ['Checkbutton']:
                        if "e" in WidName:
                            if int(self.AllCoils.getvar(self.AllCoils.winfo_name())) and 'c' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),1)
                            elif 'c' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),0)
                        elif "f" in WidName:
                            if int(self.AllPositions.getvar(self.AllPositions.winfo_name())) and 'o' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),1)
                            elif 'o' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),0)
                        elif "g" in WidName:
                            if int(self.AllCategories.getvar(self.AllCategories.winfo_name())) and 'a' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),1)
                            elif 'a' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),0)
                        elif "h" in WidName:
                            if int(self.AllPhases.getvar(self.AllPhases.winfo_name())) and 'p' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),1)
                            elif 'p' in wdgt.winfo_name():
                                    wdgt.setvar(wdgt.cget("variable"),0)
        except Exception as e:
            print(e)    
    #Check/uncheck main checkbutton based on status of below checkbuttons.  
    def DefaultCheck(self):
        try:
            c_flag = None
            o_flag = None
            a_flag = None
            p_flag = None
            if len(self.RN_FR3.winfo_children()) > 0:
                for wdgt in self.RN_FR3.winfo_children():
                    if wdgt.winfo_class() in ['Checkbutton']:
                        if 'c' in wdgt.winfo_name():
                            if not int(wdgt.getvar(wdgt.winfo_name())):
                                c_flag = False
                                if int(self.AllCoils.getvar(self.AllCoils.winfo_name())):
                                    self.AllCoils.setvar(self.AllCoils.winfo_name(), 0)
                        if 'o' in wdgt.winfo_name():
                            if not int(wdgt.getvar(wdgt.winfo_name())):
                                o_flag = False
                                if int(self.AllPositions.getvar(self.AllPositions.winfo_name())):
                                    self.AllPositions.setvar(self.AllPositions.winfo_name(), 0)
                        if 'a' in wdgt.winfo_name():
                            if not int(wdgt.getvar(wdgt.winfo_name())):
                                a_flag = False
                                if int(self.AllCategories.getvar(self.AllCategories.winfo_name())):
                                    self.AllCategories.setvar(self.AllCategories.winfo_name(), 0)
                        if 'p' in wdgt.winfo_name():
                            if not int(wdgt.getvar(wdgt.winfo_name())):
                                p_flag = False
                                if int(self.AllPhases.getvar(self.AllPhases.winfo_name())):
                                    self.AllPhases.setvar(self.AllPhases.winfo_name(), 0)
                        if not c_flag and 'e' in wdgt.winfo_name():
                            wdgt.setvar(wdgt.cget("variable"),1)
                        if not o_flag and 'f' in wdgt.winfo_name():
                            wdgt.setvar(wdgt.cget("variable"),1)
                        if not a_flag and 'g' in wdgt.winfo_name():
                            wdgt.setvar(wdgt.cget("variable"),1)
                        if not p_flag and 'h' in wdgt.winfo_name():
                            wdgt.setvar(wdgt.cget("variable"),1) 
        except Exception as e:
            print(e) 
    def PutListTests(self):
        self.master.ClearFrame(self.RN_FR4)
        Labels(self.RN_FR4,text="View Test",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=50,font=self.master.FT10BW)
        if self.master.JAllMOIData['Switch']=='online':
            pos = phase = Coil = []
            # posobj =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name FROM TestFilters WHERE Status =1 and FilterType='offset'")
            posobj =  self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Position) from AllTestcases where Status =1")
            if posobj is not None: pos = list(posobj['Position'])
            print(pos)
            # phaseobj =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name FROM TestFilters WHERE Status =1 and FilterType='Phase'")
            phaseobj =  self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Phase) from AllTestcases where Status =1")
            if phaseobj is not None: phase = list(phaseobj['Phase'])
            # CoilObj =  self.master.SQLConn.FetchDataFromQRY(f"SELECT Name FROM TestFilters WHERE Status =1 and FilterType='Coil'")
            CoilObj =  self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Coil) from AllTestcases where Status =1")
            if CoilObj is not None: Coil = list(CoilObj['Coil'])
            # pos = [i.replace(',','') for i in list(self.master.JMOIData['Offset'][self.master.Mode][self.master.PPCB.get()].values())]
            # pos = list(self.master.JAllMOIData['Selected_Testcases'].keys())
            # phase = []
            # if len(pos)>0: phase = list(self.master.JAllMOIData['Selected_Testcases'][pos[0]].keys())
            # Phase = list(self.master.JAllMOIData['Chapters'].keys())
            
            
            
            
            # Labels(self.RN_FR4,text='Select Coil :',font=self.master.FT12BW,x=1,y=25,width=14,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
            # Labels(self.RN_FR4,text='Select Position :',font=self.master.FT12BW,x=1,y=50,width=14,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
            # Labels(self.RN_FR4,text='Select Phase    :',font=self.master.FT12BW,x=1,y=75,width=14,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
            # self.CoilSelCombo = Combo(self.RN_FR4,width=25,state="readonly",font=self.master.FT10BW,val=Coil,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=30)
            # self.PosSelCombo = Combo(self.RN_FR4,width=25,state="readonly",font=self.master.FT10BW,val=pos,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=60)
            # self.PhaseSelCombo = Combo(self.RN_FR4,width=25,state="readonly",font=self.master.FT10BW,val=phase,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=90)
            # self.TestListBox = ListBx(self.RN_FR4,width=45,height=18,font=self.master.FT10BW,x=3,y=120,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],values=[])
            # # if len(pos)>0:self.PosSelCombo.set(pos[0])
            # # self.PosSelCombo.bind("<<ComboboxSelected>>",self.LoadPhaseforPos)
            # self.PhaseSelCombo.bind("<<ComboboxSelected>>",self.LoadPosTest)
            # # self.PosSelCombo.bind("<<ComboboxSelected>>",self.LoadPosTest)

            yax = 25
            if not(len(Coil)==1 and 'NA' in Coil):
                Labels(self.RN_FR4,text='Select Coil :',font=self.master.FT12BW,x=1,y=yax,width=14,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
                self.CoilSelCombo = Combo(self.RN_FR4,width=25,state="readonly",font=self.master.FT10BW,val=Coil,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=yax+5)
                yax += 25
            if self.master.Product == "MPP":
                if not(len(pos)==1 and 'NA' in pos):
                    Labels(self.RN_FR4,text='Select Position :',font=self.master.FT12BW,x=1,y=yax,width=14,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
                    self.PosSelCombo = Combo(self.RN_FR4,width=25,state="readonly",font=self.master.FT10BW,val=pos,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=yax+5)
                    yax += 25
            if not(len(phase)==1 and 'NA' in phase):
                Labels(self.RN_FR4,text='Select Phase    :',font=self.master.FT12BW,x=1,y=yax,width=14,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
                self.PhaseSelCombo = Combo(self.RN_FR4,width=25,state="readonly",font=self.master.FT10BW,val=phase,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=yax+5)
                self.PhaseSelCombo.bind("<<ComboboxSelected>>",self.LoadPosTest)
            self.TestListBox = ListBx(self.RN_FR4,width=45,height=18,font=self.master.FT10BW,x=3,y=120,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],values=[])

            Buttons(self.RN_FR4,text='Keep Selected',width=21,x=5,y=420,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.KeepSelected)
            Buttons(self.RN_FR4,text='Remove Selected',width=21,x=165,y=420,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.RemoveSelected)      
        else:
            # Labels(self.RN_FR4,text='Select Coils :',font=self.master.FT12BW,x=1,y=25,width=13,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
            # self.PosSelCombo = Combo(self.RN_FR4,width=25,state="readonly",font=self.master.FT10BW,val=pos,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=30)
            if self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Project) FROM OfflineTestcases") is not None:
                proj = self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Project) FROM OfflineTestcases")['Project'].tolist()
            else:
                proj = []
            Labels(self.RN_FR4,text='Select Project :',font=self.master.FT12BW,x=1,y=25,width=13,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
            self.OffValProjCB = Combo(self.RN_FR4,width=26,font=self.master.FT10BW,val=proj,state="readonly",bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=120,y=30)
            self.TestListBox = ListBx(self.RN_FR4,width=89,height=24,font=self.master.FT10BW,x=3,y=60,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],values=[])
            self.OffValProjCB.bind("<<ComboboxSelected>>",self.LoadOffTest)
            Buttons(self.RN_FR4,text='Keep Selected',width=21,x=320,y=29,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.KeepSelected)
            Buttons(self.RN_FR4,text='Remove Selected',width=21,x=480,y=29,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.RemoveSelected)      
            self.master.ClearFrame(self.RN_FR4_2)
            # Labels(self.RN_FR4,text="View Test",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=50,font=self.master.FT10BW)
            Labels(self.RN_FR4_2,text='Select Phases For Offline Validation',font=self.master.FT12BW,x=3,y=25,width=32,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],anchor=tk.E)
            self.PhaseListBox = ListBx(self.RN_FR4_2,width=40,height=21,font=self.master.FT10BW,x=5,y=60,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],values=[])
            Buttons(self.RN_FR4_2,text='Select Phase',width=18,x=5,y=420,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.KeepSelectedPhase)
            Buttons(self.RN_FR4_2,text='Remove Phase',width=18,x=160,y=420,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.RemoveSelectedPhase)  

    def LogsUI(self):
        try:
            UIlogs=[]
            self.master.JLogsData = self.master.JLogs.read_file()
            for log in self.master.JLogsData:
                if log[1] == "UI":
                    UIlogs.append(f"{str(log[0]).split(' ')[1].split('.')[0]} : {log[2]}")
            if self.master.PrevUIlogs != UIlogs:
                self.master.ClearFrame(self.RN_FR7)
                self.master.PrevUIlogs = UIlogs
                Labels(self.RN_FR7, text="Execution Status", x=0,y=0, bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"], width=90, font=self.master.FT10BW, anchor="center")
                self.logsLB = ListBx(self.RN_FR7, width=155, height=11, x=0, y=23, font=self.master.FT8BW, bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"], values=UIlogs[::-1])
        except Exception as e:
            print(e)
    def freeze_frame(frame):
        """Disable all widgets inside a frame."""
        for widget in frame.winfo_children():
            if isinstance(widget, (tk.Entry, tk.Button, tk.Text, tk.Checkbutton, tk.Radiobutton)):
                widget.config(state="disabled")
    def Unfreeze_frame(frame):
        """Disable all widgets inside a frame."""
        for widget in frame.winfo_children():
            if isinstance(widget, (tk.Entry, tk.Button, tk.Text, tk.Checkbutton, tk.Radiobutton)):
                widget.config(state="normal")
    def Connpopup(self):
         while not self.Conn_flag:
            time.sleep(1)
            popupdata = {"userTextBoxInput":"","responseButton":"Ok","shouldTextBoxBeAdded":False,"isValid":True,"popID":23,"displayPopUp":False,"isDisplayPopUpOpen":False,"title":"GRL-C3-MP-TPR Test Solution","message":"","button":"OK","image":"","icon":"Asterisk","isFrontEndPopUp":False,"callBackMethod":"","comboBoxEntries":"","selectedComboBoxValue":"","comboBoxEntriesFE":[],"selectedComboBoxValueFE":"","onlyDropdownAdded":False,"enableTimerOKButton":False,"enableCustomUserInputs":False,"customInputValues":{}}
            self.APIHandlePopup=APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutMessageBoxResponse'])
            self.APIHandlePopup.json=popupdata
            self.APIHandlePopup.PutRequest()
            if self.Conn_flag == True: break
            #print(self.APIHandlePopup)
    # def ping_ip(self):
    #     print("ping_ip:",self.TesterIP.get())
    #     packet = ScapyIP(dst=self.TesterIP.get())/ICMP()
    #     #start = time.time()
    #     reply = sr1(packet, timeout=1, verbose=0)
    #     if reply:
    #         self.update_logs("License verify", "Pinging - IP reached")
    #         return True
    #     else:
    #         self.update_logs("License verify", "Pinging - IP not reached")
    #         return False
    #backend functions
    def TesterConnect(self):
        #Start the Status threat
        self.Conn_flag = False
        self.master.JsettingsData['_Logs_flag'] = False
        self.master.Jsettings.update_file(self.master.JsettingsData)
        time.sleep(1)
        threading.Thread(target=self.safe_refresh_logs,daemon=True).start()
        #check for the SW status
        server_instance = Server()
        server_instance.AutoCheck()
        #time.sleep(1)
        self.master.JsettingsData['_Logs_flag'] = True
        self.master.Jsettings.update_file(self.master.JsettingsData)
        # time.sleep(1)
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        
        threading.Thread(target=self.Connpopup,daemon=True).start()
        self.update_logs("UI",f"Procceding to connect the Tester with IP {self.TesterIP.get()}")
        TesterCon = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['ConnectionSetup'],pathparam=self.TesterIP.get(),retype='json')
        testerinfo = TesterCon.GetRequest()
        #print(testerinfo)
        if testerinfo is not None:
            self.master.JtesterData[self.master.Product][self.master.Mode]['TesterIP'] = testerinfo['testerIpAddress']
            self.master.JtesterData[self.master.Product][self.master.Mode]['status'] = testerinfo['testerStatus']
            self.master.JtesterData[self.master.Product][self.master.Mode]['BoardNo'] = testerinfo['serialNumber']
            self.master.JtesterData[self.master.Product][self.master.Mode]['FWversion'] = testerinfo['firmwareVersion']
            self.master.JtesterData[self.master.Product][self.master.Mode]['licenseInfo'] = testerinfo['licenseInfo']
            #get Sw
            SWver = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetSoftwareVersion'],retype='text')
            SWverinfo = SWver.GetRequest()
            self.master.JtesterData[self.master.Product][self.master.Mode]['SWVersion'] = SWverinfo if SWverinfo is not None else 'NA'
            self.master.Jtester.update_file(values=self.master.JtesterData)
            # print(testerinfo)
            if testerinfo['testerStatus'] == 'Connected':
                self.Conn_flag = True
                self.master.TesterConnection = True
                self.update_logs("UI",f"Tester connected Successfully with IP {self.TesterIP.get()}")
                tk.messagebox.showinfo("Tester Connection:","Connected Successfully.")
                # self.update_logs(f"Connecting to the C3 {self.master.Mode} Tester with IP:{self.master.TesterIP.get()}..")
                # #put certification and power profile filters
                # if self.master.Mode=='TPR':
                #     self.CallAPI(self.master.JapiData[self.master.Product][self.master.Mode]['PutCertificationFilter']+f'/{self.master.VerCB.get()}')
                #     self.CallAPI(self.master.JapiData[self.master.Product][self.master.Mode]['PutPowerProfile']+f'/{self.master.PPCB.get()}')
                # else:
                #     self.CallAPI(self.master.JapiData[self.master.Product][self.master.Mode]['PutCertificationFilterToggle']+f'/{self.master.VerCB.get()}')
                #     self.CallAPI(self.master.JapiData[self.master.Product][self.master.Mode]['PutCertificationFilterToggle']+f'/{self.master.PPCB.get()}')
                #Enable API mode
                # apiobj = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['EnableAPIMode'])
                # apiobj.PutRequest()
                #Load the
                for product in self.master.JtesterData:
                        for mode in self.master.JtesterData[product]:
                            if not (product == self.master.Product and mode == self.master.Mode):
                                self.master.JtesterData[product][mode]['status'] = "Disconnected"
                                self.master.JtesterData[product][mode]['BoardNo'] = "NA"
                                self.master.JtesterData[product][mode]['FWversion'] = "NA"
                                self.master.JtesterData[product][mode]['SWVersion'] = "NA"
                self.master.Jtester.update_file(self.master.JtesterData)
                self.ProjectName.delete(0, tk.END)
                self.ProjectName.insert(0, "")
            else: 
                self.master.TesterConnection = False
                self.update_logs("UI",f"Tester not connected with IP {self.TesterIP.get()}, Please ensure the network connectivity.")
                tk.messagebox.showinfo("Tester Connection:","Not Connected.")
                # self.update_logs("Connection Failed")
        else:
            #call server open
            #os.system('py ./Server.py')
            # subprocess.Popen(["python", ".\\Scripts\\Server.py"])
            self.update_logs("UI",f"The MPP {self.master.Mode} software is not running,Please check the status manually.")
            # server_instance = Server(self.master.Mode,self.master.Product)
            # server_instance.open_C3_server_application()
            # time.sleep(15)
            # self.TesterConnect()
        # else: messagebox.showwarning("Ethernet connection", "Please check for ethernet connection")
        self.PutListTests()
        self.PutTestConnectionUI()
    def PutRunTests(self):
        self.master.ClearFrame(self.RN_FR5)
        Labels(self.RN_FR5,text="Run Test",x=0,y=0, bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=90,font=self.master.FT10BW)
        # offset = list(self.master.JAllMOIData['Selected_Testcases'].keys()) if len(list(self.master.JAllMOIData['Selected_Testcases'].keys()))>0 else []
        OffsetObj = self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Position) from AllTestcases where Status =1")
        offset = list(OffsetObj['Position']) if OffsetObj is not None else []
        Labels(self.RN_FR5,text='Select Position:',font=self.master.FT12BW,x=1,y=25,width=13, bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.W)
        self.RnPOSListBox = ListBx(self.RN_FR5,width=13,height=5,font=self.master.FT10BW,x=5,y=50,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],values=offset,selectedVal=self.master.JAllMOIData['Run']['Position'])
        self.RnPOSListBox.bind('<<ListboxSelect>>', self.UpdateRunPos)

        # Labels(self.RN_FR5,text='Select/Type Project:',font=self.master.FT12BW,x=115,y=25,width=17,bg=self.master.Ccodes["white"],fg="#000000",anchor=tk.W)
        # self.proSelCB = Combo(self.RN_FR5,width=22,font=self.master.FT10BW,val=[],bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=260,y=30,selectedVal=self.master.JAllMOIData['Run']['Project'])
        self.LoadOptiButton = Buttons(self.RN_FR5,text='Load Optimum Data',x=480,y=25,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],font=self.master.FT10BW,command=self.LoadOptData)
        
        Labels(self.RN_FR5,text='Repeat Count:',font=self.master.FT10BW,x=105,y=110,width=12,bg=self.master.Ccodes["white"],fg="#000000",anchor=tk.W)
        # self.Repeatcount=Entries(self.RN_FR5,font=self.master.FT10BW,x=390,y=30,width=5,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],textvar=self.master.JAllMOIData['Run']['RepeatCount'])
        self.Repeatcount=Combo(self.RN_FR5,state="readonly",font=self.master.FT10BW,x=190,y=110,width=5,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],val=[0,1,2,3,4,5,6,7,8,9,10],selectedVal=str(self.master.JAllMOIData['Run']['RepeatCount']))
        # Labels(self.RN_FR5,text='------------------------------------------------------------------------------------------------------------',font=self.master.FT10BW,x=115,y=45,width=44,bg=self.master.Ccodes["white"],fg="#000000",anchor=tk.W)
        self.TADCk = CheckBtn(self.RN_FR5,font=self.master.FT10BW,name="enableTAD",text="Enable Tester As DUT :",selectedVal=False,x=330,y=60,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=self.UpdateTAD)
        self.TADfilter = Combo(self.RN_FR5,width=16,state="readonly",font=self.master.FT10BW,val=["Automation Tests","Excerciser Tests"],selectedVal="Automation Tests",bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=480,y=65)
        # self.RerunCk = CheckBtn(self.RN_FR5,font=self.master.FT10BW,text="Rerun Fail and inconclusive",x=330,y=80,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=False)
        if self.master.Product == 'MPP':
            self.FindOptimumCk = CheckBtn(self.RN_FR5,font=self.master.FT10BW,text="Find Optimum :",x=105,y=25,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=False)
            self.optimumcoils = DropdownWithCheckboxes(self.RN_FR5,options=self.master.alloptimumcoils,width=100,selected_options=[],font=self.master.FT8BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=220,y=30)
            self.EnablePosCk = CheckBtn(self.RN_FR5,font=self.master.FT10BW,text="Enable Position Tool",x=330,y=25,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=self.master.JAllMOIData['Run']['PositionTool'],command=self.UpdatePosTool)
        else: self.UpdatePosTool()

        self.RunTestsCk = CheckBtn(self.RN_FR5,font=self.master.FT10BW,text="Run Tests",x=105,y=60,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],selectedVal=True)
        # Buttons(self.RN_FR5,text='Start Optimum',x=120,y=110,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=13,font=self.master.FT10BW,command=lambda:threading.Thread(target=self.StartOptimumRun,daemon=True).start())
        Buttons(self.RN_FR5,text='Execute',width=13,x=250,y=110,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:threading.Thread(target=self.RunTest,daemon=True).start())
        Buttons(self.RN_FR5,text='Skip Test',width=13,x=380,y=110,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.master.AllMOIModule.SkipTestcase)
        Buttons(self.RN_FR5,text='Force Stop',width=13,x=510,y=110,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW, command=self.ForceStopProcess)
        
        # Buttons(self.RN_FR5,text='Start Optimum',x=525,y=75,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=14,font=self.master.FT10BW)
        # self.TADCk = CheckBtn(self.RN_FR5,font=self.master.FT12BW,name="enableTAD",text="Enable Tester As DUT",x=1,y=100,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],command=lambda:self.PopupMsg("info","Ensure both TPT and TPR hardware connected using the tool."))
        # Labels(self.RN_FR5,text='Filters:',font=self.master.FT12BW,x=180,y=103,width=6,bg=self.master.Ccodes["white"],fg="#000000",anchor=tk.W)
        # self.TADfilter = Combo(self.RN_FR5,width=20,state="readonly",font=self.master.FT10BW,val=["Automation Tests","Excerciser Tests"],selectedVal="Automation Tests",bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=240,y=107)
        # Buttons(self.RN_FR5,text='Run Tests - API',width=14,x=410,y=105,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.RunTest)
        # Buttons(self.RN_FR5,text='Force Stop',width=14,x=525,y=105,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW, command=self.ForceStopProcess)
        # self.proSelCB.bind("<KeyRelease>",self.UpdateProject)
        self.Repeatcount.bind("<<ComboboxSelected>>",self.UpdateRepeatCount)
        # self.EnablePosCk.bind("<CheckbuttonSelect>",self.UpdatePosTool)
        # self.proSelCB.bind("<<ComboboxSelected>>",self.UpdateProject)
    def PutOfflineValUI(self):
        self.master.ClearFrame(self.RN_FR6)
        #Phase = self.master.JMOIData['Chapters'][self.master.Mode][self.master.PPCB.get()]
        # projval = self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode][1] if self.AllRun == 1 else self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode][0]
        Labels(self.RN_FR6,text="Offline Validation",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=156,font=self.master.FT10BW)
        Buttons(self.RN_FR6,text='Browse & Add Projects',width=30,x=1,y=25,font=self.master.FT10BW,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],command=self.ProjAddOffValidation)
        Buttons(self.RN_FR6,text='Remove Selected',width=30,x=220,y=25,font=self.master.FT10BW,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],command=self.RemoveSelectedOffline)
        Buttons(self.RN_FR6,text='Clear All',width=30,x=440,y=25,font=self.master.FT10BW,bg=self.master.Ccodes["blue"],fg=self.master.Ccodes["white"],command=self.ClearAllOffline)
        self.OfflineListBox = ListBx(self.RN_FR6,width=155,height=6,font=self.master.FT10BW,x=1,y=50,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],values=self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode])
        # self.AllRunCBT = CheckBtn(self.RN_FR6,font=self.master.FT12BW,text="Consider All Runs",x=1,y=154,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],selectedVal=True if self.master.AllRun==1 else False,command=self.ValidationModeSwitch)
        # self.ExValid = CheckBtn(self.RN_FR6,font=self.master.FT12BW,text="Consider Exerciser Runs",x=1,y=154,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"], selectedVal=True if self.master.ExRun==1 else False,command=self.ValidationModeSwitch)
        Buttons(self.RN_FR6,text='Prepare Validation',width=18,x=530,y=154,font=self.master.FT10BW,bg=self.master.Ccodes["blue"],command=self.PrepareOffValidation)
        Buttons(self.RN_FR6,text='Start Validation-API',width=18,x=665,y=154,font=self.master.FT10BW,bg=self.master.Ccodes["blue"],command=lambda:threading.Thread(target=self.OfflineValidation,daemon=True).start())          
        Buttons(self.RN_FR6,text='Force Stop',width=18,x=800,y=154,font=self.master.FT10BW,bg=self.master.Ccodes["blue"],command=self.ForceStopProcess)
        # Labels(self.RN_FR6,text='CTS Version:',font=self.master.FT12BW,x=1,y=156,width=12,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],anchor=tk.E)
        # self.CTSVerCB = Combo(self.RN_FR6,width=32,font=self.master.FT12BW,state="readonly",val=[f for f in os.listdir("json/CTSvalidation") if os.path.isfile(os.path.join("json/CTSvalidation", f))],bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=110,y=156,selectedVal=self.master.JsettingsData['Offline_validation']['CTSConfig'])
        # self.CTSVerCB.bind("<<ComboboxSelected>>",self.UpdateJSONValues)
        
    def ValidationModeSwitch(self):
        res = messagebox.askyesno("Changing Validation mode",f"Changing the validation mode will remove any projects that have already been added. Would you like to proceed?")
        if res == True:
            self.master.AllRun = self.master.JsettingsData['Runall'] =int(self.AllRunCBT.getvar(self.AllRunCBT.winfo_name()))
            self.master.ExRun = self.master.JsettingsData['RunEx'] = int(self.ExValid.getvar(self.ExValid.winfo_name()))
            self.master.Jsettings.update_file(self.master.JsettingsData)
            self.master.JsettingsData = self.master.Jsettings.read_file()
            #clear projects
            self.ClearAllOffline()
            if self.master.AllRun == 1 and self.master.ExRun == 1:
                messagebox.showwarning("Select only one mode",f"Select either All Runs OR Exerciser Runs")
                self.master.ExRun = False
                self.master.Jsettings.update_file(self.master.JsettingsData)
        self.PutOfflineValUI()
    #backend Operations
    def GenerateTestsForRun(self):
        # print(self.selectedcoils.get_selected(),self.selectedphases.get_selected(),self.selectedpositions.get_selected())
        #Update JSON file with filtered pos & Phase
        self.UpdatePosPhaseFilter()
        #Preapare new testlist with applied filters
        # self.master.AllMOIModule.PrepareTestCases()
        # self.master.JAllMOIData = self.master.JAllMOI.read_file()
        self.PutListTests()
        self.PutRunTests()

        # phaselist = []
        # offsetlist = []
        # if len(self.RN_FR3.winfo_children()) > 0:
        #     for wdgt in self.RN_FR3.winfo_children():
        #         if wdgt.winfo_class() in ['Checkbutton']:
        #             if 'c-' in wdgt.winfo_name():
        #                 if wdgt.getvar(wdgt.winfo_name())=='1':
        #                     phaselist.append(wdgt.cget("text"))
        #             elif 'o-' in wdgt.winfo_name():
        #                 if wdgt.getvar(wdgt.winfo_name())=='1':
        #                     offsetlist.append((wdgt.cget("text")))
        # print(phaselist)
        # print(offsetlist)
        # if len(phaselist)>0 and len(offsetlist)>0:
        #     #clear Existing data
        #     for pos in self.master.JTestConfData[self.master.Product][self.master.Mode]:
        #         if pos != 'Offline':
        #             self.master.JTestConfData[self.master.Product][self.master.Mode][pos].clear()
        #     for test in self.master.JMOIData[self.master.Mode]:
        #         # if str(self.master.Mode)+'_TD_' in test:
        #         # print(test)
        #         if self.master.JMOIData[self.master.Mode][test]['TC_Chapter'] in phaselist and self.master.JMOIData[self.master.Mode][test]['Pos_applicable'][0] in offsetlist and self.master.PPCB.get() in self.master.JMOIData[self.master.Mode][test]['PowerProfile']:
        #             self.master.JTestConfData[self.master.Product][self.master.Mode][self.master.JMOIData[self.master.Mode][test]['Pos_applicable'][0].replace(',','')].append(test)
        # self.master.JTestConf.update_file(self.master.JTestConfData)
    def UpdateJSONValues(self,ts):
        widget = ts.widget
        widget_type = widget.winfo_class()
        # Get value based on widget type
        if widget_type in ["Entry","TCombobox"]:
            value = widget.get()
        elif widget_type in ["Button","Label"]:
            value = widget["text"]
        if value:
            self.master.JsettingsData['Offline_validation']['CTSConfig'] = value
            self.master.Jsettings.update_file(self.master.JsettingsData)
    def UpdateQIJSON(self):
        remarks = []
        errors = False
        if len(self.RN_FR2.winfo_children()) > 0:
            for wdgt in self.RN_FR2.winfo_children():
                if wdgt.winfo_class() in ['Entry','Listbox','TCombobox','Checkbutton']:
                    try:
                        if wdgt.winfo_name() in ['maximumPower','guaranteedPower']:
                            val = int(wdgt.get())
                            if val > 0 and val<=15:
                                self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                            else:
                                remarks.append(f"{wdgt.winfo_name()} not in limit [0-15]")
                                errors=True
                        elif wdgt.winfo_name() in ['supportATNCloaking']:
                            val = wdgt.get()
                            self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = False if val =='No' else True
                        elif wdgt.winfo_name() in ['pRx_detectPing']:
                            val = wdgt.get()
                            self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                        elif wdgt.winfo_name() in ['mplaOffset']:
                            val = int(wdgt.get())
                            if val >= 0 and val<=5000:
                                self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                            else:
                                remarks.append(f"{wdgt.winfo_name()} not in limit [<500]")
                                errors=True
                        elif wdgt.winfo_name() in ['kest_P1_MPTPT','kest_P2_MPTPT']:
                            val = float(wdgt.get())
                            if val >= 0.40 and val <= 0.96 or val in [0,0.0]:
                                self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                            else:
                                remarks.append(f"{wdgt.winfo_name()} not in limit [0.40-0.96]")
                                errors=True
                        elif wdgt.winfo_name() in ['prxCloakRetry']:
                            if self.master.JQIData[self.master.Product][self.master.Mode]['pRx_detectPing']=='Yes':
                                val = int(wdgt.get())
                                if val >= 0 and val <= 100:
                                    self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                                else:
                                    remarks.append(f"{wdgt.winfo_name()} not in limit [0-100] or pRx_detectPing not set Yes")
                                    errors=True
                            else:
                                remarks.append(f"pRx_detectPing not set to yes,prxCloakRetry are ignored")
                        elif wdgt.winfo_name() in ['cloakingReason']:
                            if self.master.Mode == 'TPT':
                                if self.master.JQIData[self.master.Product][self.master.Mode]['isCloaking']=='Yes':
                                    valindex = wdgt.curselection()
                                    if len(valindex)>0:
                                        val = [wdgt.get(i) for i in valindex]
                                        self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                                        self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                                    else:
                                        self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                                else:
                                    self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                                    remarks.append(f"isCloaking not set to yes,cloakingReason are ignored ")
                                    remarks.append(f"  But the fields are updated")
                            else:
                                if self.master.JQIData[self.master.Product][self.master.Mode]['supportATNCloaking']==True:
                                    valindex = wdgt.curselection()
                                    if len(valindex)>0:
                                        val = [wdgt.get(i) for i in valindex]
                                        self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                                        self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                                    else:
                                        self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                                else:
                                    self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                                    remarks.append(f"supportATNCloaking not set to yes,cloakingReason are ignored")
                        elif wdgt.winfo_name() in ['prxPLAP_support_MPTPT','prxID_support_MPTPT','prxChargeStatus_support_MPTPT','prxEDS_support_MPTPT','ssCheckForTestcases']:
                            self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] =False if wdgt.getvar(wdgt.winfo_name())=='0' else True
                        elif wdgt.winfo_name() in ['cloaking','supportProprietary']:
                            valindex = wdgt.curselection()
                            if len(valindex)>0:
                                val = [wdgt.get(i) for i in valindex]
                                self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                                self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = val
                            else:
                                self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()].clear()
                        else:
                            self.master.JQIData[self.master.Product][self.master.Mode][wdgt.winfo_name()] = wdgt.get()
                    except Exception as e:
                        errors=True
                        remarks.append(f"{wdgt.winfo_name()} "+str(e))
        rm = '|'.join(remarks) if len(remarks)> 0 else 'All the fields are updated'
        if errors ==False:
            self.master.JQI.update_file(self.master.JQIData)
            self.PutQiInputUI()
            messagebox.showinfo("Updated:",rm)
        else:
            messagebox.showinfo("Not Updated:",rm)
    #Update Testview list by selected phase and offset combination.
    def LoadPosTest(self,ts):
        self.TestListBox.delete(0,tk.END)
        # if self.PosSelCombo.get() not in ['Offline']:
            # self.OffValProjCB['values']=[]
            # self.OffValProjCB.set('')
        if self.master.JAllMOIData['Switch'] != 'Offline':
            # res = self.master.SQLConn.FetchDataFromQRY(f"SELECT Testcase FROM AllTestcases WHERE Position='{self.PosSelCombo.get()}' and Coil='{self.CoilSelCombo.get()}' and Phase='{self.PhaseSelCombo.get()}' and Status=1")
            # query = f"SELECT Testcase FROM AllTestcases WHERE"
            # if 'PosSelCombo' in vars(self):#'PosSelCombo' in vars(self)
            #     query += f" Position='{self.PosSelCombo.get()}'"
            # if hasattr(self, 'CoilSelCombo'):
            #     query += f" and Coil='{self.CoilSelCombo.get()}'"
            # if hasattr(self, 'PhaseSelCombo'):
            #     query += f" and Phase='{self.PhaseSelCombo.get()}'"
            # query += f" and Status=1"
            # res = self.master.SQLConn.FetchDataFromQRY(query)
            query = f"SELECT Testcase FROM AllTestcases WHERE"
            if 'PosSelCombo' in vars(self):
                try:
                    query += f" Position='{self.PosSelCombo.get()}' and"
                except:
                    pass

            if 'CoilSelCombo' in vars(self):
                try:
                    query += f" Coil='{self.CoilSelCombo.get()}' and"
                except:
                    pass

            if 'PhaseSelCombo' in vars(self):
                try:
                    query += f" Phase='{self.PhaseSelCombo.get()}' and"
                except:
                    pass

            query += " Status=1"
            res = self.master.SQLConn.FetchDataFromQRY(query)
            if res is not None:
                self.TestListBox.UpdateValues(list(res['Testcase']))
            # self.RnPOSListBox.delete(0,tk.END)
            # self.RnPOSListBox.UpdateValues(list(self.master.JAllMOIData['Selected_Testcases'].keys()))
        # else:
        # else:
        #     if len(self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'])>0:
        #         self.OffValProjCB['values']=list(self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'].keys())
    def LoadOffTest(self,ts):
        self.TestListBox.delete(0,tk.END)
        self.PhaseListBox.delete(0,tk.END)
        print(self.OffValProjCB.get())
        res = self.master.SQLConn.FetchDataFromQRY(f"SELECT Testcase FROM OfflineTestcases WHERE Project = '{self.OffValProjCB.get()}' AND Status=1")
        if res is not None:
            test_case =list(res['TestCase'])# res["TestCase"].tolist()  # Convert DataFrame column to a list
            self.TestListBox.UpdateValues(test_case) 
           
            Pres = self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Phase) FROM OfflineTestcases WHERE Project = '{self.OffValProjCB.get()}' AND Status=1")
            if Pres is not None:
                phases=list(Pres['Phase'])
                self.PhaseListBox.UpdateValues(phases)

           
        #self.TestListBox.UpdateValues(list(self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][self.OffValProjCB.get()].keys()))
    def KeepSelected(self):
        index = self.TestListBox.curselection()
        if len(index)>0:
            testcases = [self.TestListBox.get(i) for i in index]
            availabletc = list(self.TestListBox.get(0,tk.END))
            ns_tests = list(set(availabletc) - set(testcases))
            if len(testcases)>0:
                if self.master.switch != 'Offline':
                    testlist=  f"('{ns_tests[0]}')" if len (ns_tests) == 1 else tuple(ns_tests)
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases SET Status=0 where Testcase in {testlist}")
                    self.LoadPosTest(self.TestListBox) 
                else:
                    testlist=  f"('{ns_tests[0]}')" if len (ns_tests) == 1 else tuple(ns_tests)
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE OfflineTestcases SET Status=0 where Testcase in {testlist} AND Project = '{self.OffValProjCB.get()}'")
                    self.LoadOffTest(self.TestListBox)             
                    #self.master.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases SET Status=0 where Testcase in {Alltestcases}")
            #         # for tc in ns_tests:
            #         #     self.master.JAllMOIData['Selected_Testcases'][self.PosSelCombo.get()][self.PhaseSelCombo.get()].remove(tc)
            #         # self.master.JTestConf.update_file(self.master.JTestConfData)
            #         # print(ns_tests)
            #         self.master.JAllMOIData['Selected_Testcases'][self.PosSelCombo.get()][self.PhaseSelCombo.get()]=testcases
            #         self.master.JAllMOI.update_file(self.master.JAllMOIData)
            #     else:
            #         proj = self.OffValProjCB.get()
            #         for tc in ns_tests:
            #             del self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][proj][tc]
            #         self.master.JTestConf.update_file(self.master.JTestConfData)
            #         # self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][proj] = testcases
            #         # self.master.JTestConf.update_file(self.master.JTestConfData)
            #         self.LoadPosTest(self.TestListBox)  
            #         self.LoadOffTest(self.OffValProjCB)  
    def KeepSelectedPhase(self):
        index = self.PhaseListBox.curselection()
        if len(index)>0:
            testcases = [self.PhaseListBox.get(i) for i in index]
            availabletc = list(self.PhaseListBox.get(0,tk.END))
            ns_tests = list(set(availabletc) - set(testcases))
            if len(testcases)>0:
                
                testlist=  f"('{ns_tests[0]}')" if len (ns_tests) == 1 else tuple(ns_tests)
                self.master.SQLConn.ExecutebyQuery(f"UPDATE OfflineTestcases SET Status=0 where Phase in {testlist} AND Project = '{self.OffValProjCB.get()}'")
                self.LoadOffTest(self.TestListBox)             
                #self.master.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases SET Status=0 where Testcase in {Alltestcases}")
                    
    def RemoveSelected(self):
        index = self.TestListBox.curselection()
        if len(index)>0:
            testcases = [self.TestListBox.get(i) for i in index]
            availabletc = list(self.TestListBox.get(0,tk.END))
            ns_tests = list(set(availabletc) - set(testcases))
            if len(testcases)>0:
                if self.master.switch != 'Offline':
                    testlist=  f"('{testcases[0]}')" if len (testcases) == 1 else tuple(testcases)
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases SET Status=0 where Testcase in {testlist}")
                    self.LoadPosTest(self.TestListBox) 
                else:
                    #self.master.AllMOIModule.Offlinetestcase()
                    testlist=  f"('{testcases[0]}')" if len (testcases) == 1 else tuple(testcases)
                    #print(testlist)
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE OfflineTestcases SET Status=0 where Testcase in {testlist} AND Project = '{self.OffValProjCB.get()}'")
                    self.LoadOffTest(self.TestListBox)  

                    # self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][proj] = ns_tests
                    # self.master.JTestConf.update_file(self.master.JTestConfData)
                    # self.LoadPosTest(self.TestListBox)
                    # self.LoadOffTest(self.OffValProjCB)
    def RemoveSelectedPhase(self):
        index = self.PhaseListBox.curselection()
        if len(index)>0:
            testcases = [self.PhaseListBox.get(i) for i in index]
            availabletc = list(self.PhaseListBox.get(0,tk.END))
            ns_tests = list(set(availabletc) - set(testcases))
            if len(testcases)>0:
                
                testlist=  f"('{testcases[0]}')" if len (testcases) == 1 else tuple(testcases)
                #print(testlist)
                self.master.SQLConn.ExecutebyQuery(f"UPDATE OfflineTestcases SET Status=0 where Phase in {testlist} AND Project = '{self.OffValProjCB.get()}'")
                self.LoadOffTest(self.TestListBox)  

                    
    def RemoveSelectedOffline(self):
        index =self.OfflineListBox.curselection()
        proj = [self.OfflineListBox.get(i) for i in index]
        if len(proj)>0:
            for i in proj:
                print("i:",i.split('/')[-1])
                self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode].remove(i)
                self.master.SQLConn.ExecutebyQuery(f"DELETE FROM OfflineTestcases WHERE Project = '{i.split('/')[-1]}'")
            self.master.Jsettings.update_file(self.master.JsettingsData)
            self.OfflineListBox.UpdateValues(self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode])   
        self.PutListTests()
    def GetProjectnameFromRepDir(self):
        prolist=[]
        propath = self.master.JtesterData[self.master.Product][self.master.Mode]['ReportPath']
        for file in os.listdir(propath):
            if 'V_2_0_1' in file:
                prolist.append(file.split('_')[0])
        return prolist
    # def UpdateProject(self,ts):
        # if ts != "NA":
        #     self.master.JAllMOIData['Run']['Project'] = self.proSelCB.get()
        #     self.master.JAllMOI.update_file(self.master.JAllMOIData)
        # APIPutPowerProfile = APIOperations(url=f"{self.master.JapiData[self.master.Product][self.master.Mode]['PutPowerProfile']}/{self.master.JAllMOIData['PowerProfile']}")
        # APIPutCertificationFilter = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutCertificationFilter'])
        # APIcreateProj = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutProjectFolder'],json={"projectName":self.master.JsettingsData['Online_validation'][self.master.Mode]['ProjectName'],"moiName":self.master.VerCB.get()})
        # APIPutPowerProfile.PutRequest()
        # APIPutCertificationFilter.PutRequest()
        # res = APIcreateProj.PutRequest()

        # self.master.JsettingsData['Online_validation'][self.master.Mode]['ProjectName'] = self.proSelCB.get()
        # self.master.Jsettings.update_file(self.master.JsettingsData)
        # Move the project creation while clicking the Run Tests api button.

        # APIPutPowerProfile = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutPowerProfile'])
        # APIPutCertificationFilter = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutCertificationFilter'])
        # APIcreateProj = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutProjectFolder'],json={"projectName":self.master.JsettingsData['Online_validation'][self.master.Mode]['ProjectName'],"moiName":self.master.VerCB.get()})
        # APIPutPowerProfile.PutRequest()
        # APIPutCertificationFilter.PutRequest()
        # res = APIcreateProj.PutRequest()
        # print("Project",res)
    def UpdateRepeatCount(self,ts):
        try:
            # self.master.JQIData[self.master.Product][self.master.Mode]['repCount'] = int(self.Repeatcount.get())
            # self.master.JQI.update_file(self.master.JQIData)
            self.master.JAllMOIData['Run']['RepeatCount'] = int(self.Repeatcount.get())
            print("checking repeat count:",int(self.Repeatcount.get()))
            self.master.JAllMOI.update_file(self.master.JAllMOIData)
        except Exception as e:
            print(e)
    #Update 
    def UpdatePosTool(self):
        if self.master.Product == "MPP":
            self.master.JAllMOIData['Run']['PositionTool'] = True if self.EnablePosCk.getvar(self.EnablePosCk.winfo_name()) == '1' else False
        else: self.master.JAllMOIData['Run']['PositionTool'] = False
        self.master.JAllMOI.update_file(self.master.JAllMOIData)
    def UpdateSmartSwitch(self):
        self.master.JAllMOIData = self.master.JAllMOI.read_file()
        self.master.SPConnection = self.master.JAllMOIData['SPConnection']
        
        if self.EnableSmartSwich.getvar(self.EnableSmartSwich.winfo_name()) == '1':
            self.master.JAllMOIData['Run']['EnableSmartSwitch'] = True  
        else: self.master.JAllMOIData['Run']['EnableSmartSwitch'] = False

        if self.PowerOffOn.getvar(self.PowerOffOn.winfo_name()) == '1':
            self.master.JAllMOIData['Run']['PowerOFF&ON'] = True
        else: self.master.JAllMOIData['Run']['PowerOFF&ON'] = False

        self.master.JAllMOI.update_file(self.master.JAllMOIData)

    def UpdateTAD(self):
        self.PopupMsg("info","Ensure both TPT and TPR hardware connected using the tool.")
        self.master.JAllMOIData['Run']['TAD'] = True if int(self.TADCk.getvar(self.TADCk.winfo_name())) == 1 else False
        self.master.JAllMOI.update_file(self.master.JAllMOIData)

    def ProjAddOffValidation(self,folder = ''):
        jsonlist=[]
        ExTracelist = []
        test = {}
        
        if self.master.switch == 'Offline':
            # print(self.master.switch)
            foldernames = filedialog.askdirectory(title="Select Folder")
        else: foldernames = folder
    
        # print(foldernames,self.master.switch)
        # foldernames = list(tkfilebrowser.askopendirnames(title="Select Project Folders"))
        if foldernames:
            # for path in foldernames:
                # if '_MPP_' in path:
            #Check fot the valid project folder
            ResFol = False
            Finaljson = False
            Finaljsonpath = None
            bkupjson = False
            ExTrace = False
            for root, dirs, files in os.walk(foldernames):
                for d in dirs:
                    if d.startswith("Run"):
                        ResFol=True
                        break
                for f in files:
                    if f.endswith("FinalReport.json"):
                        Finaljson=True
                        Finaljsonpath=os.path.join(root,f)
                    if f.endswith("TestBackup.gproj"):
                        bkupjson=True
                    if f.endswith("QiSignalCapture.grltrace"):
                        ExTrace=True
            # print( self.master.AllRun,ResFol==True,Finaljson==True,ExTrace)
            #1. Consider Excericser
            if self.master.ExRun == 1:
                self.master.sts = True
                if self.master.ExRun == 1: #consider exerciser runs
                    for root, dirs, files in os.walk(foldernames):
                        for f in files:
                            if f.startswith("QiSignalCapture.grltrace"):
                                ExTracelist.append(os.path.join(root, f))
            else:
                #check for Valid project folder
                if  ResFol==True and Finaljson==True and bkupjson==True:
                    ValidProj = False
                    #check for the project file loaded is for selected product & the mode
                    Fjson = JsonOperations(Finaljsonpath)
                    FjsonData = Fjson.read_file()
                    self.master.JAllMOIData = self.master.JAllMOI.read_file()
                    #MPP TPR case
                    # print(FjsonData['TestToolInfo']['ModelName'],self.master.JAllMOIData['Product'],self.master.JAllMOIData['Mode'])
                    if all(res in FjsonData['TestToolInfo']['ModelName'] for res in ["-MP-","TPR"]):
                        if self.master.JAllMOIData['Product'] == "MPP" and self.master.JAllMOIData['Mode'] == "TPR":ValidProj=True
                    elif all(res in FjsonData['TestToolInfo']['ModelName'] for res in ["-C3-","TPT"]):
                        if self.master.JAllMOIData['Product'] == "MPP" or "C3" and self.master.JAllMOIData['Mode'] == "TPT":ValidProj=True
                    elif all(res in FjsonData['TestToolInfo']['ModelName'] for res in ["-WP-","TPR"]):
                        if self.master.JAllMOIData['Product'] == "C3" and self.master.JAllMOIData['Mode'] == "TPR":ValidProj=True
                    if ValidProj == True:
                        #1. Consider All Runs
                        if self.master.AllRun == 1:
                            for root, dirs, files in os.walk(foldernames):
                                for d in dirs:
                                    if d.startswith("Run"):
                                        if os.path.join(root, d) not in self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode]:
                                            # print(os.path.join(root, d))
                                            jsonlist.append(os.path.join(root, d))
                        #2. Consider Consolidated
                        else:
                            for root, dirs, files in os.walk(foldernames):
                                for file in files:
                                    if file.__contains__("FinalReport.json"):
                                        if root not in self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode]:
                                            # jsonlist.append(os.path.join(root,file))
                                            jsonlist.append(root)
                        self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode].extend(jsonlist)
                        self.master.Jsettings.update_file(self.master.JsettingsData)
                        # print("links:",self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode])
                        if self.master.switch == 'Offline':self.OfflineListBox.UpdateValues(self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode])
                    else: 
                        self.update_logs("UI","Please select a valid project, The selected project does not match the one configured in the tool.")
                        messagebox.showinfo("Wrong Project","Please select a valid project, The selected project does not match the one configured in the tool.")
                else:messagebox.showinfo("Project Folder","Select valid project folder")
 
    def ClearAllOffline(self):
        # self.master.SQLConn.DeleteTableData("OfflineTestcases")
        self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode].clear()
        self.master.Jsettings.update_file(self.master.JsettingsData)
        self.OfflineListBox.delete(0,tk.END)
        self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'].clear()
        # self.master.JTestConfData[self.master.Product][self.master.Mode]['Test'].clear()
        self.master.JTestConf.update_file(self.master.JTestConfData)
        self.master.SQLConn.DeleteTableData("OfflineTestcases")
        self.PutListTests()
    def PrepareOffValidation(self):
        try:
            self.master.SQLConn.DeleteTableData("OfflineTestcases")
            # auto validation
            if self.master.switch != 'Offline':
                projects = self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode]
                # print(len(projects))
            # manually selecting projects to validate
            else:
                index = self.OfflineListBox.curselection()
                # print("index:",index)
                if len(index)>0:
                    projects = [self.OfflineListBox.get(i) for i in index]
                    # print("projects:",projects)
                
            TClist={}
            # projects = self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode]
            # print(len(projects))
            if len(projects)>0:
                if self.master.AllRun == 1:
                    #Consider all traces from all the runs
                    for pro in projects:
                        filepath = None
                        jsonpath = None
                        for root, dirs, files in os.walk(pro):
                            for file in files:
                                if file.endswith(".gproj") and file.__contains__("Run"):
                                    filepath = str(Path(os.path.join(root, file)))
                                    
                                if file.endswith(".json") and file.__contains__("Run"):
                                    jsonpath = os.path.join(root, file) 
                        # print("file",filepath,jsonpath)
                        if filepath is not None and jsonpath is not None:
                            # print("path",os.path.join(pro,filepath))
                            test = JsonOperations(os.path.join(pro,filepath))
                            testdata =test.read_file()
                            #print("testdata",testdata)
                            # print("ERR",filepath.split('\\'))
                            proname = str(filepath.split('\\')[len(filepath.split('\\'))-4])+'-'+str(filepath.split('\\')[len(filepath.split('\\'))-3])
                            #print("proname",proname)
                            if proname not in TClist:TClist[proname] ={}
                            #print("fine",testdata['testBkpTestResultsandPath'])
                            for tcl in testdata['testBkpTestResultsandPath']:
                                if 'testinformation' in tcl:
                                    if tcl['testinformation'] is not None:
                                        if tcl['testcaseDetails']['m_DisplayName'] is not None and tcl['testinformation']['TestResult'] not in [' ',None,'NotRun']:
                                            # if any(self.master.JMOIData[self.master.Mode][i].get('Testcase_Name') == tcl['testcaseDetails']['m_DisplayName'] for i in self.master.JMOIData[self.master.Mode] if str(self.master.Mode)+"_TD_" in i):
                                                testpath = tcl['actualTracePath'].split('\\')
                                                TClist[proname][tcl['testcaseDetails']['m_DisplayName']]=[tcl['testcaseDetails']['m_TestId'],pro+'\\'+testpath[len(testpath)-2]+'\\'+testpath[len(testpath)-1],jsonpath]
                else:
                    #Consider only SW taken final traces for the offline validation
                    print("proceeding for the consolidated")
                    for pro in projects:
                        # print("pro:",pro)
                        Backuppath = None
                        jsonpath = None
                        for root, dirs, files in os.walk(pro):
                            if "ReferenceData" in dirs:
                                dirs.remove("ReferenceData")
                            for file in files:
                                if file.endswith("Final_TestBackup.gproj"):
                                    Backuppath =os.path.join(Path(root), Path(file))
                                if file.endswith("FinalReport.json"):
                                    jsonpath = os.path.join(Path(root), Path(file))
                        #Fetch Testcases from Backup json file
                        BKJSON = JsonOperations(Backuppath)
                        BKJSONData =  BKJSON.read_file()
                        for TCdata in BKJSONData['testBkpTestResultsandPath']:
                            tracepathlist = TCdata['actualTracePath'].split('\\')
                            # tracepath = f"{pro}/{tracepathlist[len(tracepathlist)-3]}/{tracepathlist[len(tracepathlist)-2]}/{tracepathlist[len(tracepathlist)-1]}"
                            tracepath = os.path.join(Path(pro),tracepathlist[len(tracepathlist)-3],tracepathlist[len(tracepathlist)-2],tracepathlist[len(tracepathlist)-1])
                            proname = tracepathlist[len(tracepathlist)-4]
                            if proname not in TClist:TClist[proname] ={} 
                            TClist[proname][TCdata["testcaseDetails"]['m_DisplayName']]=[TCdata["testcaseDetails"]['m_TestId'],str(tracepath),str(jsonpath),str(Backuppath),TCdata["testcaseDetails"]['m_TestDetailsfromSpecVersion']['_chapter']]
                # # print(self.master.JTestConfData)   
                # self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'].clear()
                # self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline']=TClist
                # print("TClist:",TClist)
                # self.master.JTestConf.update_file(self.master.JTestConfData)
                self.create_offlinetestcases_table()  # Ensure table is created before inserting

                AllTestData = []
                #TestFilters = []
                # Retrieve test cases from JSON and format them
                for project_name, test_cases in TClist.items():
                    for test_case_name, test_case_details in test_cases.items():
                        AllTestData.append({
                            "Product": self.master.JAllMOIData['Product'],
                            "Mode": self.master.JAllMOIData['Mode'],
                            'Project': project_name,
                            "TestCase": test_case_name,
                            "TestID": test_case_details[0],
                            "TracePath": test_case_details[1],
                            "JsonPath": test_case_details[2],
                            "BackupPath": test_case_details[3] if len(test_case_details) > 3 else None,
                            "Phase":test_case_details[4],
                            "Status": 1                  
                        })
                
                # Insert into DB
                if len(AllTestData)>0:
                    self.master.SQLConn.DeleteTableData("OfflineTestcases")  # Optional: Clears old data
                    self.master.SQLConn.InsertDataFromDict("OfflineTestcases", AllTestData)
                    #for val in test_case_name:TestFilters.append({"FilterType":"Tescasename","Name":val,"Status":1})
                    # print(TestFilters)
                    #self.master.SQLConn.DeleteTableData("TestFilters")
                    #self.master.SQLConn.InsertDataFromDict("TestFilters",TestFilters)
            
                # self.OffValProjCB['values']=list(TClist.keys())
                # self.master.OfflineProjs = list(TClist.keys())
                #  self.TestListBox.UpdateValues(list(res['Testcase']))
                self.PutListTests()
                # self.master.AllMOIModule.Offlinetestcase()
                print(self.master.SQLConn.FetchDataFromQRY(f"SELECT COUNT(TestID) FROM OfflineTestcases WHERE Status = 1").iloc[0, 0])
            else:messagebox.showwarning("Project selection", "Please select the project to prepare for offline validation")
        except Exception as e:
            traceback.print_exc()
    def create_offlinetestcases_table(self):
        """Create the OfflineTestcases table if it doesn't exist"""
        query = """
        CREATE TABLE IF NOT EXISTS OfflineTestcases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Product TEXT NOT NULL,
            Mode TEXT NOT NULL,
            Project TEXT NOT NULL,
            TestCase VARCHAR(255) NOT NULL,
            TestID VARCHAR(255) NOT NULL,
            TracePath VARCHAR(255) NOT NULL,
            JsonPath VARCHAR(255) NOT NULL,
            BackupPath VARCHAR(255),
            Phase NOT NULL,
            Status INTEGER NOT NULL
        )
        """        
        self.master.SQLConn.ExecutebyQuery(query)  # Ensure this method executes SQL commands

    def Create_validation_logs(self,proj):
        # Logs folder
        timestamp1 = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(f"Offline_validation_Logs/{self.master.Product}/{self.master.Mode}", exist_ok=True)
        log_path = f"Offline_validation_Logs/{self.master.Product}/{self.master.Mode}/{proj}_{timestamp1}.log"
        open(log_path, "w").close()
        self.master.JsettingsData['Validation_logs_path'] = log_path
        self.master.Jsettings.update_file(self.master.JsettingsData)

    def OfflineValidation(self):
        try:
            self.master.SQLConn.ExecutebyQuery("DELETE FROM Header")
            self.master.SQLConn.ExecutebyQuery("DELETE FROM PayLoadDetails")
            self.master.SQLConn.ExecutebyQuery("DELETE FROM ChecksHeader")
            self.master.SQLConn.ExecutebyQuery("DELETE FROM ChecksDetails")
            self.master.SQLConn.ExecutebyQuery("VACUUM")
            self.master.TestData['TestResults']={}
            self.master.TestData['FileList_Data']={}
            self.master.TestResultsjson.update_file(self.master.TestData)
            self.master.JsettingsData = self.master.Jsettings.read_file()
            CTS = JsonOperations(f'json/CTSvalidation/{self.master.Product}{self.master.Mode}.json')
            self.JCTSData =CTS.read_file()
            if self.master.JsettingsData['_stop_flag']==True:
                #Start the Status threat
                self.master.JsettingsData['_stop_flag'] = False
                self.master.JsettingsData['_Logs_flag'] = False
                self.master.Jsettings.update_file(self.master.JsettingsData)
                time.sleep(1)
                threading.Thread(target=self.safe_refresh_logs,daemon=True).start()
                #check for the SW status
                server_instance = Server()
                server_instance.AutoCheck()
                time.sleep(1)
                self.master.JsettingsData['_Logs_flag'] = True
                self.master.Jsettings.update_file(self.master.JsettingsData)
                time.sleep(1)
                # print("St 1",self.master.sts,len(self.master.OfflineProjs))
                # self.update_logs("UI","Offline validation started.")
                self.TraceUPL = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutWaveformFile'])        
                self.TCstatus = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['TCstatus'],retype='json')
                #Exerciser traces validation
                if self.master.sts == True:
                    for tests in self.master.JTestConfData[self.master.Product][self.master.Mode]['Test']:
                        self.update_logs("UI",f"Validating:{tests}")
                        self.TraceUPL.files = {"WaveformFile":open(tests.replace('/','\\'),"rb")}
                        # print(tests.replace('/','\\'),"rb")
                        ProjRun = None
                        self.Validation(tests,ProjRun)
                    self.master.sts = False
                #Test cases validation   - automation
                else:
                    projects = self.master.SQLConn.FetchDataFromQRY(f"SELECT DISTINCT(Project) FROM OfflineTestcases")
                    ProList = projects['Project'].tolist() if projects is not None else []
                    # print(ProList)
                    if len(ProList)>0:
                        # print("ProList:",ProList)
                        projcnt = 0
                        for ProjRun in ProList:
                            projcnt+=1
                            TCcnt =0 
                            # start validation logs
                            self.Create_validation_logs(ProjRun)
                            self.update_logs("UI",f"Offline validation started for the Project - {ProjRun} - {projcnt}/{len(ProList)}")
                            #Create Json for Results TBD--
                            self.CreateResultJson(ProjRun)
                            self.master.JsettingsData = self.master.Jsettings.read_file()
                            if self.master.JsettingsData['_stop_flag'] == True :break
                            #print(self.master.SQLConn.FetchDataFromQRY(f"SELECT COUNT(TestID) FROM OfflineTestcases WHERE Status = 1").iloc[0, 0])
                            if self.master.SQLConn.FetchDataFromQRY(f"SELECT TestCase, TestID, TracePath, JsonPath, BackupPath FROM OfflineTestcases WHERE Status = 1 AND Project = '{ProjRun}'") is not None:
                                AllTests = self.master.SQLConn.FetchDataFromQRY(f"SELECT TestCase, TestID, TracePath, JsonPath, BackupPath FROM OfflineTestcases WHERE Status = 1 AND Project = '{ProjRun}'")[["TestCase","TestID","TracePath","JsonPath","BackupPath"]].values.tolist()
                            else: AllTests = []
                            
                            # print(AllTests)
                            test_time = []
                           
                            if len(AllTests)>0:
                                self.Disable_Frames(self.RN_FR4)
                                if self.master.JAllMOIData['Switch']=='Offline':self.Disable_Frames(self.RN_FR4_2)
                                for tests in AllTests:
                                    try:
                                        # print("tests:",tests)
                                        if os.path.exists(tests[2]):
                                            APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutClearCapture']).PutRequest()
                                            if self.master.Product=='MPP' and self.master.Mode=='TPT':
                                                BKjson = JsonOperations(tests[4])
                                                self.BKjsonData = BKjson.read_file()
                                                self.master.TestData = self.master.TestResultsjson.read_file()
                                                if tests[1] not in self.master.TestData['TestResults'].keys():
                                                    self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
                                                    TCcnt+=1
                                                    try:
                                                        TestKey=f'{self.Certification}_Link'
                                                        if self.JCTSData[self.master.Product][self.master.Mode][tests[1]].get(TestKey,False):
                                                            for Tc in self.JCTSData[self.master.Product][self.master.Mode][tests[1]][TestKey]["TestLink"]:
                                                                for TempTests in AllTests:
                                                                    if Tc in TempTests[1] and Tc not in self.master.TestData['TestResults'].keys():
                                                                        self.update_logs("UI",f"Validating:{TempTests[0]}-{TCcnt}/{len(AllTests)}")
                                                                        print(f"Validating:{TempTests[0]}-{TCcnt}/{len(AllTests)}")
                                                                        self.TraceUPL.files = {"WaveformFile":open(TempTests[2].replace('/','\\'),"rb")}
                                                                        status = self.TraceUPL.PutRequest()
                                                                        if status == 200 and self.CheckTraceLoadStatus():
                                                                            TCcnt+=1
                                                                            TestValidation(TestID=TempTests[1],TestCaseName=TempTests[0],ProjectJson=TempTests[3],BackupJson = TempTests[4],TracePath=TempTests[2])                                                                          
                                                                            break                                                               
                                                    except Exception as e: print(e)
                                                    # If the Test Contains TWO Trace files then add the TC in List and Load the TRace file and store it in Json and Update Json file
                                                    if tests[1] in ['CMAG001_01_Magnetic_Cover_Presence_Check']: 
                                                        if tests[1] not in self.master.TestData['FileList_Data'].keys():
                                                            self.TraceUPL.files = {"WaveformFile":open(tests[2].replace('/','\\'),"rb")}
                                                            status = self.TraceUPL.PutRequest()
                                                            if status == 200 and self.CheckTraceLoadStatus():
                                                                PktAPI = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetCCLinePackets'],retype='json')
                                                                if tests[1] not in self.master.TestData['FileList_Data']:
                                                                    self.master.TestData['FileList_Data'][tests[1]] = {}
                                                                self.master.TestData['FileList_Data'][tests[1]]['Json']= PktAPI.GetRequest()
                                                                self.master.TestResultsjson.update_file(self.master.TestData)
                                                                tests[2]=tests[2].replace('4_1.grltrace','4_1_MPP.grltrace')

                                                    self.update_logs("UI",f"Validating:{tests[0]}-{TCcnt}/{len(AllTests)}")
                                                    self.TraceUPL.files = {"WaveformFile":open(tests[2].replace('/','\\'),"rb")}
                                                    status = self.TraceUPL.PutRequest()
                                                    if status == 200 and self.CheckTraceLoadStatus():
                                                        TestValidation(TestID=tests[1],TestCaseName=tests[0],ProjectJson=tests[3],BackupJson = tests[4],TracePath=tests[2])        

                                            else:
                                                TCcnt+=1
                                                start1 = time.perf_counter()
                                                self.update_logs("UI",f"Validating:{tests[0]}-{TCcnt}/{len(AllTests)}")
                                                print(f"Validating:{tests[0]}-{TCcnt}/{len(AllTests)}")
                                                self.TraceUPL.files = {"WaveformFile":open(tests[2].replace('/','\\'),"rb")}
                                                status = self.TraceUPL.PutRequest()
                                                # print(f"status:{status}")
                                                if status == 200 and self.CheckTraceLoadStatus():       
                                                    end1 = time.perf_counter()
                                                    start2 = time.perf_counter()
                                                    TestValidation(TestID=tests[1],TestCaseName=tests[0],ProjectJson=tests[3],BackupJson = tests[4],TracePath=tests[2])
                                                    end2 = time.perf_counter()
                                                    test_time.append([tests[0], f"Trace loading: {round(end1-start1,3)} sec", f"Validation time: {round(end2-start2,3)} sec"])
                                                    print([tests[0], f"Trace loading: {round(end1-start1,3)} sec", f"Validation time: {round(end2-start2,3)} sec"])
                                                    self.update_logs("UI",f"{tests[0]} --> Trace loading: {round(end1-start1,3)} sec, Validation time: {round(end2-start2,3)} sec")

                                    except Exception as e:
                                        print(e)
                                    #Check for force stop
                                    self.master.JsettingsData = self.master.Jsettings.read_file()
                                    if self.master.JsettingsData['_stop_flag'] == True :break
                                self.Enable_frame(self.RN_FR4)
                                if self.master.JAllMOIData['Switch']=='Offline':self.Enable_frame(self.RN_FR4_2)
                            # print(test_time)
                    else: self.update_logs("UI","No project loaded")
                    #Sync With DB
                    self.update_logs("UI","Offline validation is complete. Proceeding with the results to update the database.")
                  
                    self.master.SQLConn.SyncWithJsonReportFile()
                    #Update results into SQLlite DB, for results.
                    #Sync sqlite to mongoDB
                    # self.master.SQLConn.sync_table()
                    self.update_logs("UI","Database Sync completed.")
                self.master.JsettingsData['_stop_flag'] = True
                self.master.Jsettings.update_file(self.master.JsettingsData)
            else:self.update_logs("UI","Tool is busy with running other progress..! wait/kill the existing thread.")
        except Exception as e:
            traceback.print_exc()
            # print(e)

    def CheckTraceLoadStatus(self):
        time.sleep(1)
        Status=False
        TraceStatus = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetFileReadStatus'],retype='text')
        while not Status:
            out=TraceStatus.GetRequest()
            print(out)
            if out =='"READY"':
                Status=True
        return Status

    def Validation(self,tests,ProjRun):
        status = self.TraceUPL.PutRequest()
        if status == 200:
            t_end = time.time() + 60
            while time.time() < t_end:
                try:
                    data = self.TCstatus.GetRequest()
                    if data is not None:
                        # print(len(data['2']['displayDataChunk']))
                        if len(data['2']['displayDataChunk'])>0:
                        #call Validation
                            if self.master.sts == True and self.master.Mode == 'TPT':
                                ExcerciseValidation()  #Exerciser traces validation
                            elif self.master.JMOIData[self.master.Mode][tests]['Status'] == True:
                                # if self.master.Mode == 'TPR':
                                OfflineValidation(TestID=tests,ProjectJson=self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][ProjRun][tests][2],TracePath=self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][ProjRun][tests][1],mode=self.master.Mode,product=self.master.Product)
                                # elif self.master.Mode == 'TPT':
                                #     OfflineValidationMPPTPT(TestID=tests,ProjectJson=self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][ProjRun][tests][2],TracePath=self.master.JTestConfData[self.master.Product][self.master.Mode]['Offline'][ProjRun][tests][1])
                            else: self.update_logs("UI",f'No Validation config for Test {tests}')
                            break
                except Exception as e:
                    self.update_logs("sys",str(e))
                    break
        #self.update_logs("UI","Offline validation Ended.")
    def PopupMsg(self,head,msg):
        messagebox.showinfo(head, msg)

    def RunTest(self):
        # Optimum finding
        if self.master.Product == "MPP":
            if bool(int(self.FindOptimumCk.getvar(self.FindOptimumCk.winfo_name()))) and bool(int(self.EnablePosCk.getvar(self.EnablePosCk.winfo_name()))):
                self.update_logs("UI","Optimum position finding started.")
                self.StartOptimumRun()
                self.update_logs("UI","Optimum position finding ended.")
            # else: messagebox.showwarning("Position tool", "Please enable both postion tool and Find optimum to perform optimum position")

        # Execution
        if bool(int(self.RunTestsCk.getvar(self.RunTestsCk.winfo_name()))):
            if self.master.JsettingsData['_stop_flag'] == True:
                self.JAllMOI = JsonOperations('json/AllMOIRun.json')
                self.Disable_Frames(self.master.SM1_frame)
                index = self.RnPOSListBox.curselection()
                offsetlist = [self.RnPOSListBox.get(i) for i in index] if len(index)>0 else []
                # if len(offsetlist)>0:
                self.master.JsettingsData['_stop_flag'] = False
                self.master.JsettingsData['_Logs_flag'] = False
                self.master.Jsettings.update_file(self.master.JsettingsData)
                self.JAllMOIData = self.JAllMOI.read_file()
                self.update_logs("UI","Test Excecution started.")
                print("run:",self.JAllMOIData["Plug_IP"])
                print("offsetlist:",offsetlist)
                fltr = {
                        "Pos":offsetlist,
                        "TAD":self.master.JAllMOIData['Run']['TAD'],
                        "TADmode":self.master.JAllMOIData['Run']['TADFilter'],
                        "PowerProfile":self.master.JAllMOIData['PowerProfile'],
                        "PositionTool":self.master.JAllMOIData['Run']['PositionTool'],
                        "EnableSmartSwitch":self.master.JAllMOIData['Run']['EnableSmartSwitch']
                        }
                print(fltr)
                threading.Thread(target=self.safe_refresh_logs,daemon=True).start()

                # if self.EnablePosCk.getvar(self.EnablePosCk.winfo_name()) == '1':
                #     if self.master.Product == "MPP":
                #         self.master.postool.Disconnection()
                #         self.ArduinoCon = self.master.postool.Connection(port=self.master.JsettingsData['PositionTool']['Port'])
                #         print("ArduinoCon:",self.ArduinoCon)
                #         if self.ArduinoCon is not None:
                #             RunTests(fltr)

                # else: RunTests(fltr)

                RunTests(fltr)


                self.update_logs("UI","Test Excecution finished.")
                print("Execution finished")

                # Rerun Fail and inconclusive testcases
                # if bool(int(self.RerunCk.getvar(self.RerunCk.winfo_name()))):
                #     time.sleep(20)
                #     self.Rerun()
                #     APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutClearCapture']).PutRequest()
                #     self.JAllMOI = JsonOperations('json/AllMOIRun.json')
                #     self.Disable_Frames(self.master.SM1_frame)

                #     self.master.JsettingsData['_stop_flag'] = False
                #     self.master.JsettingsData['_Logs_flag'] = False
                #     self.master.Jsettings.update_file(self.master.JsettingsData)
                #     self.JAllMOIData = self.JAllMOI.read_file()
                #     self.update_logs("UI","Test Excecution started.")
                #     print("run:",self.JAllMOIData["Plug_IP"])
                    
                #     fltr["Rerun"] = True

                #     threading.Thread(target=self.safe_refresh_logs,daemon=True).start()
                #     RunTests(fltr)
                #     self.Enable_frame(self.master.SM1_frame)
                #     print("Rerun finished")
                    
                #start validation automatically
                if bool(int(self.AutoValidButton.getvar(self.AutoValidButton.winfo_name()))):
                    time.sleep(3)
                    self.AutoValidate()
                self.Enable_frame(self.master.SM1_frame)
            else: 
                self.update_logs("UI","Tool is busy with running other progress..! wait/kill the existing thread.")
    def AutoValidate(self):
        try:
            #Get Project Name from API
            GetProject =  APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetProjectConfiguration'],retype="json")
            data = GetProject.GetRequest()
            reports = {'MPP':{'TPR':'GRL-C3-MP-TPR','TPT':'GRL-C3-MP-TPT'},'C3':{'TPR':'GRL-WP-TPR-C3','TPT':'GRL-C3-MP-TPT'}}
            ProjectName = None
            if data is not None:
                ProjectName = data['projectConfigurationModel']['projectName']
            if ProjectName is not None:
                folderpath = ''
                for root, dirs, files in os.walk(rf"C:\GRL\{reports[self.master.Product][self.master.Mode]}\Report"): #for root, dirs, files in os.walk(rf"C:\GRL\GRL-C3-MP-{self.master.Mode}\Report"):
                    for dir_name in dirs:
                        if dir_name.startswith(self.ProjectName.get()):
                            folderpath = str(Path(os.path.join(root, dir_name)))
                self.update_logs("UI","Wait for the auto validation to start.")
                folderpath = folderpath.replace("\\", "/")
                self.master.JsettingsData['Offline_validation']['json_path'][self.master.Product][self.master.Mode].clear()
                self.master.Jsettings.update_file(self.master.JsettingsData)
                self.ProjAddOffValidation(folderpath)
                time.sleep(1)
                self.PrepareOffValidation()
                self.master.JsettingsData['_stop_flag']=True
                self.master.Jsettings.update_file(self.master.JsettingsData)
                time.sleep(1)
                self.OfflineValidation()
                self.update_logs("UI","Auto validation Finished.")
            else:self.update_logs("UI","Project folder could not found in the report location.")
        except Exception as e:
            print(e)
            self.update_logs("UI",f"Exception : {str(e)}")
    def safe_refresh_logs(self):
        try:
            while True:
                self.master.JsettingsData = self.master.Jsettings.read_file()
                if self.master.JsettingsData is not None:
                    # print("GUI_Logs_flag:",self.master.JsettingsData['_Logs_flag'])
                    if self.master.JsettingsData['_Logs_flag'] == True: break
                    UIlogs=[]
                    self.master.JLogsData = self.master.JLogs.read_file()
                    if self.master.JLogsData:
                        for log in self.master.JLogsData:
                            if log[1] == "UI":
                                UIlogs.append(f"{str(log[0]).split(' ')[1].split('.')[0]} : {log[2]}")
                        if self.logsLB.winfo_exists():
                            self.logsLB.UpdateValues(UIlogs[::-1])
                        # threading.Thread(target=self.LogsUI,daemon=True).start()
                        # self.LogsUI()
                    
                    time.sleep(0.5)
        except Exception as e: 
            # print(e)
            traceback.print_exc()
            self.safe_refresh_logs()
    def ForceStopProcess(self,Type=None):
        self.master.JsettingsData =self.master.Jsettings.read_file()
        if self.master.JsettingsData['_stop_flag'] == False:
            self.update_logs("UI","Force Stoping the current Thread.")
            self.master.JsettingsData['_stop_flag'] = True
            #self.master.JsettingsData['_Logs_flag'] = True
            self.master.Jsettings.update_file(self.master.JsettingsData)
        else:self.update_logs("UI","No active threads to stop.")
    def CreateResultJson(self,project):
        #create json file for report
        now = datetime.now()
        timestamp = now.strftime("%d%m%Y_%H%M%S")
        reponame = f'{self.master.Mode}_{project}_{timestamp}_Offline'
        path ="Results\\JsonReports\\"+reponame+'.json'
        li = []        
        resjson = JsonOperations(path)
        resjson.update_file(li)
        #update path in TCP
        # print(str(os.path.abspath(path)))
        self.master.JTCPData["test_config_data"]["Report_path"] = str(os.path.abspath(path))
        self.master.JTCP.update_file(self.master.JTCPData)
    def CallAPI(self,URL):
        Obj = APIOperations(url=URL)
        if 'Put' in URL and 'PutPowerProfile' not in URL:
            status = Obj.PutRequest()
        else:
            status = Obj.GetRequest()
    # def update_logs(self,logtype,log):
    #     dt_object = datetime.fromtimestamp(datetime.now().timestamp())
    #     self.master.JLogsData = self.master.JLogs.read_file()
    #     self.master.JLogsData.append([str(dt_object),logtype,log])
    #     self.master.JLogs.update_file(self.master.JLogsData)
    #     if logtype == 'UI':self.LogsUI()
    def update_logs(self,logtype,log):
        dt_object = datetime.fromtimestamp(datetime.now().timestamp())
        self.master.JLogsData = self.master.JLogs.read_file()

        self.master.JLogsData.append([str(dt_object),logtype,log])
        self.master.JLogs.update_file(self.master.JLogsData)
        if logtype == 'UI':self.LogsUI()
    #Based on the Allmoi json file status, check/Uncheck the checksboxes
    def AutoCheckPosPhase(self):
        if len(self.RN_FR3.winfo_children()) > 0:
            for wdgt in self.RN_FR3.winfo_children():
                if wdgt.winfo_class() in ['Checkbutton']:
                    if 'p-' in wdgt.winfo_name():
                        res = self.master.SQLConn.FetchDataFromQRY(f"SELECT status from TestFilters where FilterType='Phase' and Name='{wdgt.cget("text")}'")
                        if res is not None:
                            wdgt.setvar(wdgt.cget("variable"),res['Status'].loc[0])
                        else:self.update_logs("UI",f"Phase {wdgt.cget("text")} status not ftech from DB!")
                    if 'a-' in wdgt.winfo_name():
                        res = self.master.SQLConn.FetchDataFromQRY(f"SELECT status from TestFilters where FilterType='Cat' and Name='{wdgt.cget("text")}'")
                        if res is not None:
                            wdgt.setvar(wdgt.cget("variable"),res['Status'].loc[0])
                        else:self.update_logs("UI",f"Category {wdgt.cget("text")} status not ftech from DB!")
                    if 'o-' in wdgt.winfo_name():
                        res = self.master.SQLConn.FetchDataFromQRY(f"SELECT status from TestFilters where FilterType='offset' and Name='{wdgt.cget("text")}'")
                        if res is not None:
                            wdgt.setvar(wdgt.cget("variable"),res['Status'].loc[0])
                        else:self.update_logs("UI",f"Offset {wdgt.cget("text")} status not ftech from DB!")
                    if 'c-' in wdgt.winfo_name():
                        res = self.master.SQLConn.FetchDataFromQRY(f"SELECT status from TestFilters where FilterType='Coil' and Name='{wdgt.cget("text")}'")
                        if res is not None:
                            wdgt.setvar(wdgt.cget("variable"),res['Status'].loc[0])
                        else:self.update_logs("UI",f"Coil {wdgt.cget("text")} status not ftech from DB!")
    #Update the filtered positions ,phases and coils to the DB to prepare the selected Testcases .
    def UpdatePosPhaseFilter(self):
        # if len(self.RN_FR3.winfo_children()) > 0:
        #     for wdgt in self.RN_FR3.winfo_children():
        #         if wdgt.winfo_class() in ['Checkbutton']:
        #             if 'p-' in wdgt.winfo_name():
        #                 self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={int(wdgt.getvar(wdgt.winfo_name()))} where FilterType='Phase' and Name='{wdgt.cget("text")}'")
        #             elif 'a-' in wdgt.winfo_name():
        #                 self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={int(wdgt.getvar(wdgt.winfo_name()))} where FilterType='Cat' and Name='{wdgt.cget("text")}'")
        #             elif 'c-' in wdgt.winfo_name():
        #                 self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={int(wdgt.getvar(wdgt.winfo_name()))} where FilterType='Coil' and Name='{wdgt.cget("text")}'")
        #             elif 'o-' in wdgt.winfo_name():
        #                 self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={int(wdgt.getvar(wdgt.winfo_name()))} where FilterType='offset' and Name='{wdgt.cget("text")}'")
        #     #update Alltest Tables based on filters
        #     self.master.AllMOIModule.PrepareTestCases()
        #print({"coils": self.selectedcoils.get_selected(),"positions":self.selectedpositions.get_selected(), "phases":self.selectedphases.get_selected()})
        self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={0}")
        for key, value in {"coils": getattr(vars(self).get('selectedcoils', []), 'get_selected', lambda: [])(),"positions":getattr(vars(self).get('selectedpositions', []), 'get_selected', lambda: [])(), "phases":getattr(vars(self).get('selectedphases', []), 'get_selected', lambda: [])()}.items():
            for ele in value:
                if key == "coils":
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={1} where FilterType='Coil' and Name='{ele}'")
                elif key == "positions":
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={1} where FilterType='offset' and Name='{ele}'")
                elif key == "phases":
                    self.master.SQLConn.ExecutebyQuery(f"UPDATE TestFilters SET Status={1} where FilterType='Phase' and Name='{ele}'")
        #update Alltest Tables based on filters
        self.master.AllMOIModule.PrepareTestCases()
    #Load Offset,Phase and Testcases for the selected MOI
    def UpdateMOI(self):
        try: 
            testerStatus = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['ConnectionSetup'],retype='json').GetRequest()['testerStatus']
            # self.update_logs("UI",f"Automation tool set for {self.master.Product} {self.master.Mode}")
            # if self.master.TesterConnection == True:
            if testerStatus == "Connected":
                self.master.AllMOIModule.GetAllTestcases()
                self.update_logs("UI",f"Offset,Phase and testcases are loaded for the selected MOI.")
                if self.master.projloaded:
                    self.update_logs("UI",f"{self.ProjectName.get()} Project loaded successfully" if self.master.projloaded else f"{self.ProjectName.get()} Project Created successfully")
            else:
                self.update_logs("UI",f"Offset,Phase and testcases not loaded. Please reconnect the tester and Try again") 
                messagebox.showwarning("Project","Offset,Phase and testcases not loaded. Please reconnect the tester and Try again")
            self.PutTestSel()
            self.PutListTests()
            self.PutRunTests()
            self.AutoCheckPosPhase()
        except Exception as e:
            traceback.print_exc()
    #update phase for the selected pos in view tests
    def LoadPhaseforPos(self,ts):
        self.PhaseSelCombo['values']=list(self.master.JAllMOIData['Selected_Testcases'][self.PosSelCombo.get()].keys())
        self.PhaseSelCombo.set("")
        self.TestListBox.delete(0,tk.END)
    #Update run pos list box to json
    def UpdateRunPos(self,ts):
        index = self.RnPOSListBox.curselection()
        self.master.JAllMOIData['Run']['Position'] = [self.RnPOSListBox.get(i) for i in index] if len(index)>0 else []
        self.master.JAllMOI.update_file(self.master.JAllMOIData)
    #Create Project 
    # def CreateProject(self):
    #     APIcreateProj = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutProjectFolder'],json={"projectName":self.master.JAllMOIData['Run']['Project'],"moiName":self.master.JAllMOIData['Certificate']})
    #     res = APIcreateProj.PutRequest()
    #     self.update_logs("UI",f"Project {self.master.JAllMOIData['Run']['Project']} created for {self.master.Product}:{self.master.Mode}:{self.master.JAllMOIData['Certificate']}")
    #Start Optimim
    def StartOptimumRun(self):
        # self.ToolConsistencyTest()

        try:
            coil = ""
            for coil in self.optimumcoils.get_selected():
                coil = coil
                if self.master.JsettingsData['_stop_flag'] == True:
                    #Set stop flag to False , to indicate that thread is active
                    self.master.JsettingsData['_stop_flag'] = False
                    self.master.Jsettings.update_file(self.master.JsettingsData)
                    threading.Thread(target=self.safe_refresh_logs,daemon=True).start()
                    print("optimum for coil:",coil)
                    GetOptimumPosition(coil)
                    #Force Stop ./ if triggered from user.
                    time.sleep(3)
                    #Set Stop flag back to true to indicate thread execution completed.
                    self.master.JsettingsData['_stop_flag'] = True
                    self.master.Jsettings.update_file(self.master.JsettingsData)
                    # self.update_logs("UI","Optimum position check Excecution Completed.")
                    #setting final optimum positions as home
                    self.ArduinoCon = None
                    self.master.postool.Disconnection()
                    self.ArduinoCon = self.master.postool.Connection(port=self.master.JsettingsData['PositionTool']['Port'])
                    self.Move("SetHome", "MOVE_X")
                    self.Move("SetHome", "MOVE_Y")
                    # self.Move("SetHome", "MOVE_Z")
                    self.master.postool.Disconnection()
                else: self.update_logs("UI","Tool is busy with running other progress..! wait/kill the existing thread.")
                time.sleep(3)

            coilvalues = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['GetOptimumCoilValues'],retype='json').GetRequest()
            print("coilvalues API response:",coilvalues)

            # optijson = {"Optimum": {"SSCheck": True,"Coil_Type": coil,"Coil_Position": "(0.0,0.0)","Coil_Values": coilvalues['coilOptData']}}
            # print("optijson:",optijson)
            for item in coilvalues['coilOptData']:
                item['position'] = "(0.0,0.0)"
            print("updated coilvalues",coilvalues)

            now = datetime.now()
            timestamp = now.strftime("%d%m%Y_%H%M%S")
            # with open(f"Results/OptimumResults/{self.ProjectName.get()}_optimumdata_{timestamp}.json", "w") as f:
            #     json.dump(coilvalues, f, indent=4)
            with open(f"Results/OptimumResults/{self.ProjectName.get()}_optimumdata_{timestamp}.json", "wb") as f:
                f.write(orjson.dumps(coilvalues,option=orjson.OPT_INDENT_2))

            PutcoilAPI = APIOperations(url=self.master.JapiData[self.master.Product][self.master.Mode]['PutOptimumCoilValues'])
            # PutcoilAPI.json = {"coilOptData":coilvalues['coilOptData']}
            PutcoilAPI.json = coilvalues
            res= PutcoilAPI.PutRequest()
            print("loadopt:",res)

        except Exception as e:
            traceback.print_exc()
    def ToolConsistencyTest(self):
        cnt = 0
        self.ArduinoCon = self.master.postool.Connection(port=self.master.JsettingsData['PositionTool']['Port'])
        while cnt <= 50:
            print("count:",cnt)
            print("MOVE_Z upward",float(self.master.JsettingsData['PositionTool']['MOVE_Z'])*float(self.master.JsettingsData['PositionTool']['Motors']['StepsTomm']))
            self.master.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {float(self.master.JsettingsData['PositionTool']['MOVE_Z'])*float(self.master.JsettingsData['PositionTool']['Motors']['StepsTomm'])}")
            print("waiting 5 sec started")
            time.sleep(5)
            print("waiting 5 sec finished")
            print("MOVE_Z down")
            self.master.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
            print("waiting 5 sec started")
            time.sleep(5)
            print("waiting 5 sec finished")
            cnt += 1
    def Move(self, direction, axis):     
        try:
            if self.ArduinoCon is not None:
                if axis=="SmartPlug":
                    print(axis,direction)
                    self.master.postool.SendCommands(self.ArduinoCon,f"{axis} {direction}")
                else:
                    if direction == "Forward":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} {int(float(self.master.JsettingsData['PositionTool'][axis])*float(self.master.JsettingsData['PositionTool']['Motors']['StepsTomm']))}")
                    elif direction == "Backward":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} {int(float(self.master.JsettingsData['PositionTool'][axis])*float(self.master.JsettingsData['PositionTool']['Motors']['StepsTomm']))*-1}")
                    elif direction == "Home":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} Home")
                    elif direction =="SetHome":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} SetHome")
            else:print("Position tool is not connected!")
        except Exception as e:
            print(e)

class IP(MPPGUI):
    def __init__(self,master):
        self = self
        self.master = master
        self.master.ClearFrame(self.master.SM2_frame)
        self.ArduinoCon = None
        #Create Frames
        self.IP_FR1 = Menu(self.master.SM2_frame,height=625,width=300,bg=self.master.Ccodes["frame_bg"],x=5,y=5)
        # self.IP_FR2 = Menu(self.master.SM2_frame,height=400,width=300,bg=self.master.Ccodes["frame_bg"],x=310,y=5)
        self.CreateIP()   
        self.UpdatePort('ts')
        # self.OptimumPositionUI()
    # def OptimumPositionUI(self):
    #     Labels(self.IP_FR2,text="Get Optimum Position",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
    #     Labels(self.IP_FR2,text="Project Name :",x=0,y=25,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
    #     self.OPTPOSproject = Entries(self.IP_FR2,width=20,x=100,y=25,font=self.master.FT12BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],textvar=self.master.JsettingsData['OptimumData']['ProjectName'])
    #     Buttons(self.IP_FR2,text='Create Project',x=100,y=50,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=13,font=self.master.FT10BW)
    #     Labels(self.IP_FR2,text="DUTName :",x=0,y=75,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
    #     self.OPTPOSDUTname = Entries(self.IP_FR2,width=20,x=100,y=75,font=self.master.FT12BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],textvar=self.master.JsettingsData['OptimumData']['DUTname'])
    #     Labels(self.IP_FR2,text="Coil Name :",x=0,y=100,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
    #     self.OPTPOSCoil = Entries(self.IP_FR2,width=20,x=100,y=100,font=self.master.FT12BW,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],textvar=self.master.JsettingsData['OptimumData']['Coil'])
    #     Buttons(self.IP_FR2,text='Start Optimum',x=100,y=125,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=12,font=self.master.FT10BW)
    #     Buttons(self.IP_FR2,text='Force Stop',x=193,y=125,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=9,font=self.master.FT10BW)
    #     Labels(self.IP_FR2,text="Status",x=0,y=150,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
    #     self.PosListBox = ListBx(self.IP_FR2,width=41,height=13,font=self.master.FT10BW,x=1,y=185,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"])
    #     self.OPTPOSDUTname.bind("<KeyRelease>",self.UpdateOptimum)
    #     self.OPTPOSCoil.bind("<KeyRelease>",self.UpdateOptimum)
    def CreateProject(self):
        pass
    def CreateIP(self):
        availablePorts = self.master.postool.GetAvailablePorts()
        Labels(self.IP_FR1,text="Positon Tool - Manual Control",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        Labels(self.IP_FR1,text="Select Port :",x=0,y=25,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.PortCB = Combo(self.IP_FR1,width=12,state="readonly",font=self.master.FT10BW,val=availablePorts,bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"],x=100,y=28,selectedVal=self.master.JsettingsData['PositionTool']['Port'])
        Buttons(self.IP_FR1,text='Refresh',x=205,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=10,font=self.master.FT10BW,command=self.RefreshPorts)
        self.StatusLB = Labels(self.IP_FR1,text="Status : "+self.master.JsettingsData['PositionTool']['Status'],x=100,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=20,font=self.master.FT10BW)
        # if len(availablePorts)>0:
        #     self.PortCB.selectedVal = self.master.JsettingsData['PositionTool']['Port'] if self.master.JsettingsData['PositionTool']['Port'] in availablePorts else availablePorts[0]
        # else:
        #     self.PortCB.selectedVal=""
        #     self.StatusLB.text = "Position tool not connected."
        self.PortCB.bind("<<ComboboxSelected>>",self.UpdatePort)
        Labels(self.IP_FR1,text="X-Axis",x=0,y=75,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        Labels(self.IP_FR1,text="Distance",x=0,y=100,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.XDistance = Entries(self.IP_FR1,width=14,x=125,y=100,font=self.master.FT12BW,textvar=self.master.JsettingsData['PositionTool']['MOVE_X'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Labels(self.IP_FR1,text="mm",x=250,y=100,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=2,font=self.master.FT10BW)
        Buttons(self.IP_FR1,text='Set Home',x=50,y=125,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("SetHome", "MOVE_X"))
        Buttons(self.IP_FR1,text='Forward',x=125,y=125,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Forward", "MOVE_X"))
        Buttons(self.IP_FR1,text='Home',x=183,y=125,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Home", "MOVE_X"))
        Buttons(self.IP_FR1,text='Backward',x=242,y=125,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Backward", "MOVE_X"))
        self.XDistance.bind("<KeyRelease>",self.UpdateDistanceX)
        Labels(self.IP_FR1,text="Y-Axis",x=0,y=150,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        Labels(self.IP_FR1,text="Distance",x=0,y=175,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.YDistance = Entries(self.IP_FR1,width=14,x=125,y=175,font=self.master.FT12BW,textvar=self.master.JsettingsData['PositionTool']['MOVE_Y'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Labels(self.IP_FR1,text="mm",x=250,y=175,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=2,font=self.master.FT10BW)
        Buttons(self.IP_FR1,text='Set Home',x=50,y=200,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("SetHome", "MOVE_Y"))
        Buttons(self.IP_FR1,text='Forward',x=125,y=200,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Backward", "MOVE_Y"))
        Buttons(self.IP_FR1,text='Home',x=183,y=200,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Home", "MOVE_Y"))
        Buttons(self.IP_FR1,text='Backward',x=242,y=200,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Forward", "MOVE_Y"))
        self.YDistance.bind("<KeyRelease>",self.UpdateDistanceY)
        Labels(self.IP_FR1,text="Z-Axis",x=0,y=225,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        Labels(self.IP_FR1,text="Distance",x=0,y=250,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.ZDistance = Entries(self.IP_FR1,name="mOVE_Z",width=14,x=125,y=250,font=self.master.FT12BW,textvar=self.master.JsettingsData['PositionTool']['MOVE_Z'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Labels(self.IP_FR1,text="mm",x=250,y=250,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=2,font=self.master.FT10BW)
        Buttons(self.IP_FR1,text='Set Home',x=50,y=275,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("SetHome", "MOVE_Z"))
        Buttons(self.IP_FR1,text='Forward',x=125,y=275,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Backward", "MOVE_Z"))
        Buttons(self.IP_FR1,text='Home',x=183,y=275,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Home", "MOVE_Z"))
        Buttons(self.IP_FR1,text='Backward',x=242,y=275,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW, command=lambda: self.Move("Forward", "MOVE_Z"))
        self.ZDistance.bind("<KeyRelease>",self.UpdateDistanceZ)
        Labels(self.IP_FR1,text="Motor Settings",x=0,y=350,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        Labels(self.IP_FR1,text="Max Speed",x=0,y=375,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.MaxSpeed = Entries(self.IP_FR1,width=14,x=125,y=375,font=self.master.FT12BW,textvar=self.master.JsettingsData['PositionTool']['Motors']['MaxSpeed'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Labels(self.IP_FR1,text="mm",x=250,y=375,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=2,font=self.master.FT10BW)
        Labels(self.IP_FR1,text="Acceleration",x=0,y=400,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.Acceleration = Entries(self.IP_FR1,width=14,x=125,y=400,font=self.master.FT12BW,textvar=self.master.JsettingsData['PositionTool']['Motors']['Acceleration'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Labels(self.IP_FR1,text="mm",x=250,y=400,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=2,font=self.master.FT10BW)
        Labels(self.IP_FR1,text="Z Distance",x=0,y=425,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.Zdistance = Entries(self.IP_FR1,width=14,x=125,y=425,font=self.master.FT12BW,textvar=self.master.JsettingsData['PositionTool']['Motors']['ZDistance'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        Labels(self.IP_FR1,text="mm",x=250,y=425,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=2,font=self.master.FT10BW)
        Buttons(self.IP_FR1,text='Update Frimware',x=125,y=455,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=16,font=self.master.FT10BW,command=self.UpdateFrimware)
        Labels(self.IP_FR1,text="Smart Switch",x=0,y=490,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=42,font=self.master.FT10BW)
        Buttons(self.IP_FR1,text='ON/OFF',x=10,y=530,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=8,font=self.master.FT10BW,command=lambda: self.Move("ONOROFF","SmartPlug"))
        Buttons(self.IP_FR1,text='ON&OFF',x=110,y=530,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=8,font=self.master.FT10BW,command=lambda: self.Move("ONANDOFF","SmartPlug"))
        Buttons(self.IP_FR1,text='Home',x=210,y=530,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=8,font=self.master.FT10BW,command=lambda: self.Move("Home","SmartPlug"))
        # Buttons(self.IP_FR1,text='Read Force sensor:',x=210,y=530,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=8,font=self.master.FT10BW,command= threading.Thread(target=self.ReadForceSensor,daemon=True).start())
    # def ReadForceSensor(self):
    #     while True:
    #         self.master.postool.ReadSerial(self.ArduinoCon)
    def UpdateDistanceZ(self,event):
        try:
            if float(self.ZDistance.get())<=20 and float(self.ZDistance.get())>=0:
                self.master.JsettingsData['PositionTool']['MOVE_Z'] =float(self.ZDistance.get())
                self.master.Jsettings.update_file(self.master.JsettingsData)
            else: messagebox.showinfo("Limit Exceeded Z:Axis","The Z axis limit is 0 to +20, Provide the value between the tolarence.")
        except Exception as e:
            print(e)
    def UpdateDistanceX(self,event):
        try:
            if float(self.XDistance.get())<=50 and float(self.XDistance.get())>=0:
                # self.master.JsettingsData['PositionTool']['MOVE_X'] = self.XDistance.get()
                self.master.JsettingsData['PositionTool']['MOVE_X'] = float(self.XDistance.get())
                self.master.Jsettings.update_file(self.master.JsettingsData)
            else: messagebox.showinfo("Limit Exceeded X:Axis","The X axis limit is 0 to 50, Provide the value between the tolarence.")
        except Exception as e:
            print(e)
    def UpdateDistanceY(self,event):
        try:
            if float(self.YDistance.get())<=30 and float(self.YDistance.get())>=0:
                self.master.JsettingsData['PositionTool']['MOVE_Y'] = float(self.YDistance.get())
                self.master.Jsettings.update_file(self.master.JsettingsData)
            else: messagebox.showinfo("Limit Exceeded Y:Axis","The X axis limit is 0 to 30, Provide the value between the tolarence.")
        except Exception as e:
            print(e)
    def UpdateFrimware(self):
        try:
            self.master.JsettingsData['PositionTool']['Motors']['MaxSpeed'] = int(self.MaxSpeed.get())
            self.master.JsettingsData['PositionTool']['Motors']['Acceleration'] = int(self.Acceleration.get())
            self.master.JsettingsData['PositionTool']['Motors']['ZDistance'] = int(self.Zdistance.get())
            self.master.Jsettings.update_file(self.master.JsettingsData)
            #trigger the frimware update
        except Exception as e:
            print(e)
    # def UpdatePort(self,ts):
    #     #Check Board Connected 
    #     print("port:",self.PortCB.get())
    #     self.master.postool.Disconnection()
    #     self.ArduinoCon = self.master.postool.Connection(port=self.PortCB.get())
    #     print("connection:",self.ArduinoCon)
    #     self.master.JsettingsData['PositionTool']['Port'] =  self.PortCB.get()
    #     if self.ArduinoCon is not None:
    #         if 'Not Connected' not in self.ArduinoCon:
    #             self.master.JsettingsData['PositionTool']['Status'] = "Connected."
    #         else:
    #             self.master.JsettingsData['PositionTool']['Status'] = "Not Connected!"
    #             self.master.JsettingsData['PositionTool']['Port'] = ""
    #     self.master.Jsettings.update_file(self.master.JsettingsData)
    #     self.CreateIP()
    def UpdatePort(self,ts):
        #Check Board Connected 
        print("port:",self.PortCB.get())
        self.master.postool.Disconnection()
        self.ArduinoCon = self.master.postool.Connection(port=self.PortCB.get())
        print("connection:",self.ArduinoCon)
        if self.ArduinoCon is not None:
            self.master.JsettingsData['PositionTool']['Port'] =  self.PortCB.get()
            self.master.JsettingsData['PositionTool']['Status'] = "Connected."   
        else:
            self.master.JsettingsData['PositionTool']['Status'] = "Not Connected!"
            self.master.JsettingsData['PositionTool']['Port'] = ""
            messagebox.showwarning("Arduino Connection", f"Arduino not available in the port: {self.PortCB.get()}")                                                                                                                                                                                                                                                                                                                                                   
        # self.master.JsettingsData['PositionTool']['Port'] =  self.PortCB.get()
        # if self.ArduinoCon is not None:
        #     if 'Not Connected' not in self.ArduinoCon:
        #         self.master.JsettingsData['PositionTool']['Status'] = "Connected."
        #     else:
        #         self.master.JsettingsData['PositionTool']['Status'] = "Not Connected!"
        #         self.master.JsettingsData['PositionTool']['Port'] = ""
        self.master.Jsettings.update_file(self.master.JsettingsData)
        self.CreateIP()
    def RefreshPorts(self):
        self.CreateIP()
        self.UpdatePort('ts')
    def Move(self, direction, axis):
        print("checking")
        try:
            if self.ArduinoCon is not None:
                if axis=="SmartPlug":
                    print(axis,direction)
                    self.master.postool.SendCommands(self.ArduinoCon,f"{axis} {direction}")
                else:
                    if direction == "Forward":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} {int(float(self.master.JsettingsData['PositionTool'][axis])*float(self.master.JsettingsData['PositionTool']['Motors']['StepsTomm']))}")
                    elif direction == "Backward":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} {int(float(self.master.JsettingsData['PositionTool'][axis])*float(self.master.JsettingsData['PositionTool']['Motors']['StepsTomm']))*-1}") #"StepsTomm": 45
                    elif direction == "Home":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} Home")
                    elif direction =="SetHome":
                        self.master.postool.SendCommands(self.ArduinoCon,f"{axis} SetHome")
            else:print("Position tool is not connected!")
        except Exception as e:
            print(e)
    

class Settings(MPPGUI):
    def __init__(self,master):
        self = self
        self.master = master
        self.master.ClearFrame(self.master.SM2_frame)
        self.SettingsMenu()
    def SettingsMenu(self):
        self.ST_FR1 = Menu(self.master.SM2_frame,height=640,width=110,bg=self.master.Ccodes["frame_bg"],x=5,y=5)
        self.ST_FR2 = Menu(self.master.SM2_frame,height=640,width=825,bg=self.master.Ccodes["grey"],x=120,y=5)
        #add menu buttons
        Labels(self.ST_FR1,text="Database Settings",x=0,y=1,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        Buttons(self.ST_FR1,text='MongoDB',x=2,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=14,font=self.master.FT10BW,command=self.CreateMongoDBUI)
    def CreateMongoDBUI(self):
        self.ST_FR2_1 =  Menu(self.ST_FR2,height=265,width=360,bg=self.master.Ccodes["frame_bg"],x=0,y=0)

        self.PutMongoDBConnection()
    def PutMongoDBConnection(self):
        self.master.ClearFrame(self.ST_FR2_1)
        Labels(self.ST_FR2_1,text="MongoDB Connection Setup",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=55,font=self.master.FT10BW)

        Labels(self.ST_FR2_1,text="Server IP Address :",x=20,y=30,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW,anchor=tk.E)
        Labels(self.ST_FR2_1,text="Port Number:",x=20,y=60,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW,anchor=tk.E)
        Labels(self.ST_FR2_1,text="Username:",x=20,y=90,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW,anchor=tk.E)
        Labels(self.ST_FR2_1,text="Password:",x=20,y=120,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW,anchor=tk.E)
        Labels(self.ST_FR2_1,text="Database:",x=20,y=150,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW,anchor=tk.E)
        self.MongoIP = Entries(self.ST_FR2_1,width=20,x=150,y=30,font=self.master.FT12BW,textvar=self.master.JsettingsData['MongoDB']['ServerIP'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        self.MongoPort = Entries(self.ST_FR2_1,width=20,x=150,y=60,font=self.master.FT12BW,textvar=self.master.JsettingsData['MongoDB']['Port'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        self.Mongouser = Entries(self.ST_FR2_1,width=20,x=150,y=90,font=self.master.FT12BW,textvar=self.master.JsettingsData['MongoDB']['UserName'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        self.Mongopsw = Entries(self.ST_FR2_1,width=20,x=150,y=120,font=self.master.FT12BW,textvar=self.master.JsettingsData['MongoDB']['Password'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        self.MongoDB = Entries(self.ST_FR2_1,width=20,x=150,y=150,font=self.master.FT12BW,textvar=self.master.JsettingsData['MongoDB']['DB'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        self.MongoAutoSync=CheckBtn(self.ST_FR2_1,font=self.master.FT10BW,text="AutoSync",x=150,y=180,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],selectedVal=self.master.JsettingsData['MongoDB']['Status'],command=self.UpdateAutoSync)
        Buttons(self.ST_FR2_1,text='Test Connection',x=150,y=210,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=14,font=self.master.FT10BW,command=self.CheckConnection)
        Buttons(self.ST_FR2_1,text='Save',x=260,y=210,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=7,font=self.master.FT10BW,command=self.UpdateMongoDBConfig)
        Buttons(self.ST_FR2_1,text='Sync Results',x=150,y=240,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=23,font=self.master.FT10BW) 
    #backend functions
    def UpdateMongoDBConfig(self):
        self.master.JsettingsData['MongoDB']['ServerIP']=self.MongoIP.get()
        self.master.JsettingsData['MongoDB']['Port']=self.MongoPort.get()
        self.master.JsettingsData['MongoDB']['UserName']=self.Mongouser.get()
        self.master.JsettingsData['MongoDB']['Password']=self.Mongopsw.get()
        self.master.JsettingsData['MongoDB']['DB']=self.MongoDB.get()
        self.master.Jsettings.update_file(self.master.JsettingsData)
    def UpdateAutoSync(self):
        self.master.JsettingsData['MongoDB']['AutoSync'] = True if self.MongoAutoSync.getvar(self.MongoAutoSync.winfo_name()) else False
    def CheckConnection(self):
        try:
            client = MongoClient(f"mongodb://{self.MongoIP.get()}:{self.MongoPort.get()}", serverSelectionTimeoutMS=3000)  # 3s timeout
            client.admin.command("ping")
            messagebox.showinfo("MongoDB Connection","Connected to MongoDB!")
        except Exception as e:
            messagebox.showinfo("MongoDB Connection",f"Failed to connect:{e}")
class Reports(MPPGUI):
    def __init__(self,master):
        self=self
        self.master = master
        self.master.ClearFrame(self.master.SM2_frame)
        self.JCon = JsonOperations(self.master.JsettingsData['ConsolidatedJSON'])
        self.JConData = self.JCon.read_file()
        self.ReportMenu()
    def ReportMenu(self):
        self.RP_FR1 = Menu(self.master.SM2_frame,height=640,width=110,bg=self.master.Ccodes["frame_bg"],x=5,y=5)
        self.RP_FR2 = Menu(self.master.SM2_frame,height=640,width=825,bg=self.master.Ccodes["grey"],x=120,y=5)
        #add menu buttons
        Labels(self.RP_FR1,text="Testing Reports",x=0,y=1,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        Buttons(self.RP_FR1,text='Validation Results',x=2,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=14,font=self.master.FT10BW,command=self.CreateReports)
        Labels(self.RP_FR1,text="Reports Comparison",x=0,y=50,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        Buttons(self.RP_FR1,text='JSON Comparison',x=2,y=75,width=14,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.JSONComparison)
        Buttons(self.RP_FR1,text='Golden Comparison',x=2,y=100,bg=self.master.Ccodes["blue"],fg="#FFFFFF",width=14,font=self.master.FT10BW)
        Labels(self.RP_FR1,text="Reports Merge",x=0,y=125,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        Buttons(self.RP_FR1,text='JSON Merge',x=2,y=150,width=14,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.JsonMerge)
        Labels(self.RP_FR1,text="Other Features",x=0,y=175,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        Buttons(self.RP_FR1,text='ASK/FSK Decode',x=2,y=200,width=14,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW)
        Buttons(self.RP_FR1,text='Eye Plot Merge',x=2,y=225,width=14,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW)
        Buttons(self.RP_FR1,text='BI Analysis',x=2,y=250,width=14,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.BIAnalysis)
        Buttons(self.RP_FR1,text='Schema Analyser',x=2,y=275,width=14,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.SchemaComparison)
      
             
    def CreateReports(self):
        self.RP_FR2_1 = Menu(self.RP_FR2,height=200,width=825,bg=self.master.Ccodes["frame_bg"],x=0,y=0)
        self.RP_FR2_2 = Menu(self.RP_FR2,height=100,width=825,bg=self.master.Ccodes["frame_bg"],x=0,y=205)
        self.RP_FR2_3 = Menu(self.RP_FR2,height=130,width=825,bg=self.master.Ccodes["frame_bg"],x=0,y=310)
        #Add Reports Input form

        self.PutInput()
        self.PutReportSummary()
        self.PutReportMenu()   
    def JsonMerge(self):
        self.master.ClearFrame(self.RP_FR2)
        self.RP_FR2_1 = Menu(self.RP_FR2,height=400,width=825,bg=self.master.Ccodes["frame_bg"],x=0,y=0)
        Labels(self.RP_FR2_1,text="Report Analysis with JSON",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=120,font=self.master.FT10BW)
        Buttons(self.RP_FR2_1,text='Browse & Add Projects',width=30,x=1,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.open_Directory_path('JsonMerge'))
        Buttons(self.RP_FR2_1,text='Remove Selected',width=30,x=220,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.RemoveItemLB(self.JSONMrgListBox,'JsonMerge'))
        Buttons(self.RP_FR2_1,text='Clear All',width=30,x=440,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.ClearLB('JsonMerge'))
        self.JSONMrgListBox = ListBx(self.RP_FR2_1,width=117,height=20,font=self.master.FT10BW,x=1,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],values=self.master.JsettingsData['JsonMerge']['JsonMergePath'])
        Buttons(self.RP_FR2_1,text='Merge & Generate JSON',width=30,x=1,y=375,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=JsonReports)
    def BIAnalysis(self):
        self.master.ClearFrame(self.RP_FR2)
        self.RP_FR2_1 = Menu(self.RP_FR2,height=400,width=825,bg=self.master.Ccodes["frame_bg"],x=0,y=0)
        Labels(self.RP_FR2_1,text="Create JSON for BI Analysis",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=120,font=self.master.FT10BW)
        Buttons(self.RP_FR2_1,text='Browse & Add Projects',width=30,x=1,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.open_Directory_path('BIAnly'))
        Buttons(self.RP_FR2_1,text='Remove Selected',width=30,x=220,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.RemoveItemLB(self.BIListBox,'BIAnly'))
        Buttons(self.RP_FR2_1,text='Clear All',width=30,x=440,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.ClearLB('BIAnly'))
        self.BIListBox = ListBx(self.RP_FR2_1,width=117,height=20,font=self.master.FT10BW,x=1,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],values=self.master.JsettingsData['BIAnalyis'].keys())
        Buttons(self.RP_FR2_1,text='Merge & Generate JSON',width=30,x=1,y=375,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.GenerateBIreport2)
   
    def JSONComparison(self):
        self.master.ClearFrame(self.RP_FR2)
        self.RP_FR2_1 = Menu(self.RP_FR2,height=400,width=825,bg=self.master.Ccodes["frame_bg"],x=0,y=0)
        Labels(self.RP_FR2_1,text="Compare JSON files with High Level Results",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=120,font=self.master.FT10BW)
        Buttons(self.RP_FR2_1,text='Browse & Add JSON files',width=30,x=1,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.open_Directory_path('JsonComp'))
        Buttons(self.RP_FR2_1,text='Remove Selected',width=30,x=220,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.RemoveItemLB(self.JSONCompListBox,'JsonMerge'))
        Buttons(self.RP_FR2_1,text='Clear All',width=30,x=440,y=25,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=lambda:self.ClearLB('JsonMerge'))
        self.JSONCompListBox = ListBx(self.RP_FR2_1,width=117,height=20,font=self.master.FT10BW,x=1,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],values=self.master.JsettingsData['JSONCompare'])
        Buttons(self.RP_FR2_1,text='Merge & Generate XLS',width=30,x=1,y=375,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=JsonReports)

    def SchemaComparison(self):
        self.master.ClearFrame(self.RP_FR2)
        self.Schema_FR2_1 = Menu(self.RP_FR2,height=400,width=825,bg=self.master.Ccodes["frame_bg"],x=0,y=0)
        Labels(self.Schema_FR2_1,text="Compare QI-Report Json / PDF File with Standard Schema Json File",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=120,font=self.master.FT10BW)
        Labels(self.Schema_FR2_1,text="Select PDF/Json ",x=10,y=40,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.SelctedSchema = Combo(self.Schema_FR2_1,val=['QI-Report Json',' PDF File'],width=14,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=10,y=60)
        self.SelctedSchema.bind("<<ComboboxSelected>>",self.UpdateSchemaSelection)
      
    def UpdateSchemaSelection(self,ts):
       
        self.JsonPathList={
            "Automation":"json\\JsonSchema.json",
            "Software":""
        }
    
        if self.SelctedSchema.get()=='QI-Report Json':
            self.JsonSchema_FR2_1 = Menu(self.Schema_FR2_1,height=300,width=810,bg=self.master.Ccodes["frame_bg"],x=30,y=80)
            # Buttons(self.JsonSchema_FR2_1,text='Browse & Add JSON files',width=30,x=80,y=20,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.LoadProjFile)
            Buttons(self.JsonSchema_FR2_1,text='Browse & Add Proj File',width=30,x=80,y=20,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.LoadProjFile)
            self.DefaultSchema = Combo(self.JsonSchema_FR2_1,val=['Own Json Schema','Default Automation Schema'],selectedVal='Default Automation Schema',width=20,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=318,y=20)
            self.DefaultSchema.bind("<<ComboboxSelected>>",self.UpadteSchema)
            Buttons(self.JsonSchema_FR2_1,text='Validate Schema',width=30,x=500,y=20,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.ValidateJsonSchema)
            self.SchemaListBox = ListBx(self.JsonSchema_FR2_1,width=110,height=15,font=self.master.FT10BW,x=5,y=60,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"])

        else:
            self.PdfSchema_FR2_1 = Menu(self.Schema_FR2_1,height=300,width=810,bg=self.master.Ccodes["frame_bg"],x=30,y=80)
            Buttons(self.PdfSchema_FR2_1,text='Browse & Add Proj File',width=30,x=80,y=20,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.LoadProjFile)
            Buttons(self.PdfSchema_FR2_1,text='Validate Schema',width=30,x=318,y=20,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,command=self.ValidatePdfSchema)      

    def UpadteSchema(self,tk):
        if self.DefaultSchema.get()=='Own Json Schema':self.LoadQIJson()
        else:self.JsonPathList['Automation']="json\\JsonSchema.json"

    # def LoadQIJson(self):
    #     filename = askopenfilename()
    #     if filename:
    #         if '.json' in filename:
    #             if self.DefaultSchema.get()=='Own Json Schema':self.JsonPathList['Automation']=filename
    #             else:self.JsonPathList['Software']=filename
    #         else:messagebox.showinfo("Not Updated","Select only Json files")

    def LoadProjFile(self):

        self.Backuppath = None
        self.jsonpath = None
        self.PdfPath=None
        pro=filedialog.askdirectory(title="Select Folder")
        if pro:
            for root, dirs, files in os.walk(pro):
                if "ReferenceData" in dirs:
                    dirs.remove("ReferenceData")
                for file in files:
                    if file.endswith("Final_TestBackup.gproj"):
                        self.Backuppath =os.path.join(Path(root), Path(file))
                        for file in files:
                            if file.endswith("FinalReport.json"):
                                self.jsonpath = os.path.join(Path(root), Path(file))
                                self.JsonPathList['Software']=self.jsonpath
                            if file.endswith("FinalReport.pdf"):
                                self.PdfPath=os.path.join(Path(root), Path(file))
                    if self.Backuppath is not None: break

    def ValidateJsonSchema(self):

        if self.DefaultSchema.get()=='Own Json Schema' and self.JsonPathList['Automation']=="json\\JsonSchema.json":
            messagebox.showerror("Not Updated","Schema Selected to Autaomation")
        elif self.JsonPathList['Software']=='':
            messagebox.showerror("Not Updated","Software Json file is not selected")
        else:
            print(self.JsonPathList)
            JsonObj=C3_MPP_JsonSchema(self.Backuppath,self.jsonpath,self.master.Product,self.master.Mode,self.JsonPathList['Automation'])
            # JsonObj=C3_MPP_JsonSchema(self.JsonPathList['Automation'],self.JsonPathList['Software'])
            out=JsonObj.validate_with_exceptions()
            if len(out)>0:self.SchemaListBox.UpdateValues(out)
            else:self.SchemaListBox.UpdateValues([" No errors found. JSON validates against the schema"]) 
        
    def ValidatePdfSchema(self):
        if self.Backuppath and self.jsonpath and self.PdfPath is not None:
            PdfObj=C3_MPP_PdfSchema( self.Backuppath,self.jsonpath,self.PdfPath,self.master.Product,self.master.Mode)
            PdfObj.FormatPDFReport()
            res=PdfObj.PdfDB()
            if res is not None:messagebox.showinfo("Updated",f"Generated PDF_Schema Report in the Path :{res}")
            else:messagebox.showerror("Not Updated"," Issue in the Script/ File")
        else: messagebox.showerror("Not Updated","Selct Valid Project File")

    def PutInput(self):
        #Get Cerifications
        # print('Product',self.Product)
        if self.master.Product == "C3":
            self.BoardMDL = "C3_TPR" if self.master.Mode =="TPR" else "C3_TPT"
        elif self.master.Product == "MPP":
            self.BoardMDL = "MPP_TPR" if self.master.Mode =="TPR" else "MPP_TPT"
        Certificates = self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(Certification) FROM Header WHERE BoardModel="{self.BoardMDL}"''')
        self.master.ClearFrame(self.RP_FR2_1)
        Labels(self.RP_FR2_1,text="Report Inputs",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=120,font=self.master.FT10BW)

        # Labels(self.RP_FR2_1,text="Report Path:",x=5,y=28,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=10,font=self.master.FT10BW)
        # self.ReportPath = Entries(self.RP_FR2_1,width=33,x=80,y=30,font=self.master.FT10BW,textvar=self.master.JTCPData['test_config_data']['ConsolidateReport'],bg=self.master.Ccodes["text_bg"],fg=self.master.Ccodes["black"])
        # Buttons(self.RP_FR2_1,text='Browse',x=320,y=28,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW)

        Labels(self.RP_FR2_1,text="Certification:",x=5,y=28,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=10,font=self.master.FT10BW)
        self.CRCB = Combo(self.RP_FR2_1,width=14,state="readonly",name="crcb",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=82,y=30,val=Certificates)

        Labels(self.RP_FR2_1,text="SW Version :",x=5,y=60,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.SWCB = Combo(self.RP_FR2_1,name="swcb",width=14,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=5,y=80,val=Certificates)
        Labels(self.RP_FR2_1,text="FW Version :",x=130,y=60,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.FWCB = Combo(self.RP_FR2_1,name="fwcb",width=14,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=130,y=80)
        Labels(self.RP_FR2_1,text="HW Version :",x=255,y=60,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.HWCB = Combo(self.RP_FR2_1,name="hwcb",width=14,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=255,y=80)

        # Labels(self.RP_FR2_1,text="Test Results :",x=380,y=60,fg=self.master.Ccodes["white"],bg='#343638',width=15,font=self.master.FT10BW)
        # ListBx(self.RP_FR2_1,width=15,height=3,font=self.master.FT10BW,x=380,y=80,bg=self.Ccodes["blue"],fg=self.master.Ccodes["white"])

        Labels(self.RP_FR2_1,text="Board Number :",x=5,y=100,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.BNCB=Combo(self.RP_FR2_1,name="bncb",width=14,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=5,y=120)
        Labels(self.RP_FR2_1,text="DUT Name :",x=130,y=100,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.DNCB = Combo(self.RP_FR2_1,name="dncb",width=14,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=130,y=120)
        Labels(self.RP_FR2_1,text="DUT ID :",x=255,y=100,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT10BW)
        self.DICB = Combo(self.RP_FR2_1,name="dicb",width=14,state="readonly",font=self.master.FT10BW,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],x=255,y=120)

        self.EnTimings = CheckBtn(self.RP_FR2_1,font=self.master.FT10BW,x=5,y=140,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],name='entime',text="Timing Checks")
        self.EnMeasures = CheckBtn(self.RP_FR2_1,font=self.master.FT10BW,x=125,y=140,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],name='enmesure',text="Measure Checks")
        self.EnOthers = CheckBtn(self.RP_FR2_1,font=self.master.FT10BW,x=255,y=140,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],name='enothers',text="Other Cheks")

        Buttons(self.RP_FR2_1,text='Prepare Report',x=5,y=170,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,width=15)
        Buttons(self.RP_FR2_1,text='Refresh',x=120,y=170,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT10BW,width=15)

        Labels(self.RP_FR2_1,text="Chapters : ALL",x=385,y=28,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=11,font=self.master.FT10BW)
        self.ChapCKSA = CheckBtn(self.RP_FR2_1,font=self.master.FT10BW,x=470,y=27,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],name='chapCKSA',command=self.ChapLBSA)
        self.ChapLB = ListBx(self.RP_FR2_1,name="chaplb",width=20,height=9,font=self.master.FT10BW,x=385,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"])

        Labels(self.RP_FR2_1,text="Positions:ALL",x=535,y=28,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=11,font=self.master.FT10BW)
        self.PosCKSA = CheckBtn(self.RP_FR2_1,font=self.master.FT10BW,x=620,y=27,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],name='posCKSA',command=self.PosLBSA)
        self.PosLB = ListBx(self.RP_FR2_1,name="poslb",width=20,height=9,font=self.master.FT10BW,x=535,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"])

        Labels(self.RP_FR2_1,text="Tests : ALL",x=685,y=28,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=11,font=self.master.FT10BW)
        self.TestCKSA = CheckBtn(self.RP_FR2_1,font=self.master.FT10BW,x=770,y=27,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"],name='testCKSA',command=self.TestLBSA)
        self.TestLB = ListBx(self.RP_FR2_1,name="testlb",width=20,height=9,font=self.master.FT10BW,x=685,y=50,bg=self.master.Ccodes["white"],fg=self.master.Ccodes["black"])

        self.CRCB.bind("<<ComboboxSelected>>",self.UpdateRepParams)
        self.SWCB.bind("<<ComboboxSelected>>",self.UpdateRepParams)
        self.FWCB.bind("<<ComboboxSelected>>",self.UpdateRepParams)
        self.HWCB.bind("<<ComboboxSelected>>",self.UpdateRepParams)
        self.BNCB.bind("<<ComboboxSelected>>",self.UpdateRepParams)
        self.DNCB.bind("<<ComboboxSelected>>",self.UpdateRepParams)
        self.DICB.bind("<<ComboboxSelected>>",self.UpdateRepParams)
        self.ChapLB.bind("<<ListboxSelect>>",self.UpdateRepParams)
        self.PosLB.bind("<<ListboxSelect>>",self.UpdateRepParams)    
    def PutReportSummary(self):
        self.master.ClearFrame(self.RP_FR2_2)
        Labels(self.RP_FR2_2,text="Report Summary",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=120,font=self.master.FT10BW)

        Labels(self.RP_FR2_2,text="Total Tests",x=20,y=22,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)
        Labels(self.RP_FR2_2,text="Pass Count",x=220,y=22,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)
        Labels(self.RP_FR2_2,text="Fail Count",x=420,y=22,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)
        Labels(self.RP_FR2_2,text="Incl. Count",x=620,y=22,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)

        Labels(self.RP_FR2_2,text="0",x=20,y=55,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)
        Labels(self.RP_FR2_2,text="0",x=220,y=55,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)
        Labels(self.RP_FR2_2,text="0",x=420,y=55,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)
        Labels(self.RP_FR2_2,text="0",x=620,y=55,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=15,font=self.master.FT15BW)    
    def PutReportMenu(self):
        self.master.ClearFrame(self.RP_FR2_3)
        Labels(self.RP_FR2_3,text="Generate Report",x=0,y=0,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],width=120,font=self.master.FT10BW)
        Buttons(self.RP_FR2_3,text='CTS Validation Report',x=5,y=30,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT12BW,width=19, command=self.GetReportData)
        Labels(self.RP_FR2_3,text=": Generate XLS report with all CTS checks and other checks like timings etc. based on the selection from Input section",x=170,y=30,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],font=self.master.FT10BW)
        # Buttons(self.RP_FR2_3, text="Export CTS Checks", x=5, y=70,bg=self.master.Ccodes["blue"],fg="#FFFFFF",font=self.master.FT12BW, width=19,command=self.export_cts)
        # Labels(self.RP_FR2_3,text=": Export CTS Checks to Excel based on the selection from Input section",x=170,y=70,bg=self.master.Ccodes["lyt_cyan"],fg=self.master.Ccodes["black"],font=self.master.FT10BW)
    # def export_cts(self):
    #     xl_report = XLreport(mode=self.master.Mode, name="CTS Checks")  
    #     xl_report.ExportCTSChecks()
    def GetReportData(self):
        ch_index = self.ChapLB.curselection()
        pos_index = self.PosLB.curselection()
        ts_index = self.TestLB.curselection()
        timechk = True if self.EnTimings.getvar(self.EnTimings.winfo_name())=='1' else False
        meschk = True if self.EnMeasures.getvar(self.EnMeasures.winfo_name())=='1' else False
        othchk = True if self.EnOthers.getvar(self.EnOthers.winfo_name())=='1' else False
        fltr ={
            "SW":[self.SWCB.get()],"FW":[self.FWCB.get()],"HW":[self.HWCB.get()],"Board":[self.BNCB.get()],"DUTname":[self.DNCB.get()],"DUTID":[self.DICB.get()],
            "Chap":[self.ChapLB.get(i) for i in ch_index],"Coil":[self.PosLB.get(i) for i in pos_index],"Tests":[self.TestLB.get(i) for i in ts_index],
            "Timings":timechk,"Measures":meschk,"Others":othchk,"Product":self.BoardMDL,"Certification":self.CRCB.get()}
        # print(fltr)
        self.master.ExcelRep.CTSDetailedReport(fltr,self.master.Product)
        self.master.ExcelRep.CTSCompleteReport(self.master.Product,self.master.Mode,fltr)
        self.master.ExcelRep.PacketPayLoadDetailedReport(fltr,self.master.Product)
        self.master.ExcelRep.summarize_Report(fltr,self.master.Product)
        # self.CTSrep = CSVreport(filters=fltr,mode=self.master.Mode)
        # for Tcdata in 
        #Add summary frame --TBD
    #Backend Functions
    def UpdateRepParams(self,ts):
        WidName = ts.widget.winfo_name() if type(ts) != str else ts
        if WidName == "crcb":
            self.SWCB['values'] = self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(SWVersion) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}"''')
        elif WidName == "swcb":
            self.FWCB['values'] = self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(FWVersion) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                            AND SWVersion="{self.SWCB.get()}"''')
        elif WidName == "fwcb":
            self.HWCB['values'] = self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(HWVersion) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                            AND SWVersion="{self.SWCB.get()}" AND FWVersion="{self.FWCB.get()}"''')
        elif WidName == "hwcb":
            self.BNCB['values'] = self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(BoardNo) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                            AND SWVersion="{self.SWCB.get()}" AND FWVersion="{self.FWCB.get()}" AND HWVersion="{self.HWCB.get()}"''')
        elif WidName == "bncb":
            self.DNCB['values'] = self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(DUTName) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                            AND SWVersion="{self.SWCB.get()}" AND FWVersion="{self.FWCB.get()}" AND HWVersion="{self.HWCB.get()}" 
                                                                                            AND BoardNo="{self.BNCB.get()}"''')
        elif WidName == "dncb":
            self.DICB['values'] = self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(DUTID) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                            AND SWVersion="{self.SWCB.get()}" AND FWVersion="{self.FWCB.get()}" AND HWVersion="{self.HWCB.get()}" 
                                                                                            AND BoardNo="{self.BNCB.get()}" AND DUTName="{self.DNCB.get()}"''')
        elif WidName == "dicb":
            self.ChapLB.UpdateValues(self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(ChapterName) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                            AND SWVersion="{self.SWCB.get()}" AND FWVersion="{self.FWCB.get()}" AND HWVersion="{self.HWCB.get()}" 
                                                                                            AND BoardNo="{self.BNCB.get()}" AND DUTName="{self.DNCB.get()}" AND DUTID="{self.DICB.get()}"'''))
        elif WidName == "chaplb":
            index = self.ChapLB.curselection()
            chap = [self.ChapLB.get(i) for i in index]
            if len(chap)>0:
                chaplist = f"('{chap[0]}')"  if len(chap)==1 else tuple(chap)
                print(chaplist)
                self.PosLB.UpdateValues(self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(Coil) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                                AND SWVersion="{self.SWCB.get()}" AND FWVersion="{self.FWCB.get()}" AND HWVersion="{self.HWCB.get()}" 
                                                                                                AND BoardNo="{self.BNCB.get()}" AND DUTName="{self.DNCB.get()}" AND DUTID="{self.DICB.get()}" 
                                                                                                AND ChapterName in {chaplist}'''))
                
            else: self.PosLB.UpdateValues([])
        elif WidName == "poslb":
            ch_index = self.ChapLB.curselection()
            chap = [self.ChapLB.get(i) for i in ch_index]
            pos_index = self.PosLB.curselection()
            pos = [self.PosLB.get(i) for i in pos_index]
            if len(pos)>0:
                chaplist = f"('{chap[0]}')"  if len(chap)==1 else tuple(chap)
                poslist = f"('{pos[0]}')"  if len(pos)==1 else tuple(pos)
                self.TestLB.UpdateValues(self.master.SQLConn.GetSingleValuesFromDB(Header_Qry=f'''SELECT DISTINCT(TestcaseID) FROM Header WHERE BoardModel="{self.BoardMDL}" AND Certification="{self.CRCB.get()}" 
                                                                                            AND SWVersion="{self.SWCB.get()}" AND FWVersion="{self.FWCB.get()}" AND HWVersion="{self.HWCB.get()}" 
                                                                                            AND BoardNo="{self.BNCB.get()}" AND DUTName="{self.DNCB.get()}" AND DUTID="{self.DICB.get()}" 
                                                                                            AND ChapterName in {chaplist} and Coil in {poslist}'''))
            else: self.TestLB.UpdateValues([])
    def ChapLBSA(self):
        status = self.ChapCKSA.getvar(self.ChapCKSA.winfo_name())
        if status =='1':
            self.ChapLB.select_set(0,tk.END)
        else: self.ChapLB.select_clear(0,tk.END)
        self.UpdateRepParams('chaplb')
    def PosLBSA(self):
        status = self.PosCKSA.getvar(self.PosCKSA.winfo_name())
        if status =='1':
            self.PosLB.select_set(0,tk.END)
        else: self.PosLB.select_clear(0,tk.END)
        self.UpdateRepParams('poslb')
    def TestLBSA(self):
        status = self.TestCKSA.getvar(self.TestCKSA.winfo_name())
        if status =='1':
            self.TestLB.select_set(0,tk.END)
        else: self.TestLB.select_clear(0,tk.END)
    def open_Directory_path(self,value):
        foldernames = list(tkfilebrowser.askopendirnames(title="Select Project Folders"))
        if len(foldernames)>0:
            if value == 'JsonMerge':
                jsonlist = []
                #fetch final reports avaialable in path
                for path in foldernames:
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if file.endswith(".json") and file.__contains__("FinalReport"):
                                jsonlist.append(os.path.join(root, file))
                if len(jsonlist)>0:
                    for jpath in jsonlist:
                        if jpath not in self.master.JsettingsData['JsonMerge']['JsonMergePath']:self.master.JsettingsData['JsonMerge']['JsonMergePath'].append(jpath)
                    self.master.Jsettings.update_file(self.master.JsettingsData)
                    self.JsonMerge()
            if value =='JsonComp':
                pass
            if value =='BIAnly':
                csvpaths = {}
                ipjson = []
                for path in foldernames:
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if 'input' in file and '.json' in file:
                                ipjson.append(os.path.join(root, file))
                if len(ipjson)>0:
                    for proj in ipjson:
                        # print(proj)
                        csvpaths[proj] = []
                        projli = proj.split('\\')
                        projpath = '\\'.join(projli[0:len(projli)-1])
                        for root, dirs, files in os.walk(projpath):
                            for file in files:
                                if file.startswith('TPT_') and file.endswith('.csv'):
                                    csvpaths[proj].append(os.path.join(root, file))
                if len(csvpaths)>0:
                    for jsonpath in csvpaths:
                        if jsonpath not in self.master.JsettingsData['BIAnalyis']:
                            self.master.JsettingsData['BIAnalyis'][jsonpath] = csvpaths[jsonpath]
                    self.master.Jsettings.update_file(self.master.JsettingsData)
                    self.BIAnalysis()
    def RemoveItemLB(self,LB,value):
        index = LB.curselection()
        if len(index)>0:
            items = [LB.get(i) for i in index]
            if value =='JsonMerge':
                for item in items:
                    self.master.JsettingsData['JsonMerge']['JsonMergePath'].remove(item)
                self.master.Jsettings.update_file(self.master.JsettingsData)
                self.JsonMerge()
            if value =='BIAnly':
                for item in items:
                    self.master.JsettingsData['BIAnalyis'].pop(item)
                self.master.Jsettings.update_file(self.master.JsettingsData)
                self.BIAnalysis()
    def ClearLB(self,value):
        if value == 'JsonMerge':
            self.master.JsettingsData['JsonMerge']['JsonMergePath'].clear()
            self.master.Jsettings.update_file(self.master.JsettingsData)
            self.JsonMerge()
        if value == 'BIAnly':
            self.master.JsettingsData['BIAnalyis'].clear()  
            self.master.Jsettings.update_file(self.master.JsettingsData)
            self.BIAnalysis()
    def GenerateBIreport2(self):
        #consider old and new file structure of the SW
        results={}
        BIData = self.master.JsettingsData['BIAnalyis']
        if len(BIData)>0:
            for proj in BIData:
                jsonpath=JsonOperations(proj)
                jsondata = jsonpath.read_file()
                Board = jsondata['TestToolInfo']['SerialNumber']
                #read from CSV
                if Board not in results:results[Board]={}
                #add csv data
                for cpath in BIData[proj]:
                    # print(cpath)
                    pathli = cpath.split('\\')
                    if 'input_new.json' in proj:
                        #new frmt
                        dut = jsondata['TestToolInfo']['DUTname']
                        position = jsondata['TestToolInfo']['Position']
                        offsetData = jsondata['Calculations']['00'] if position == '0,0,0' else jsondata['Calculations']['22']
                        run = str(pathli[len(pathli)-3]).split('Run')[1] 
                        Power=0
                        if jsondata['TestToolInfo']['DUTname'] not in results[Board]: results[Board][dut]={}
                        if jsondata['TestToolInfo']['Position'] not in results[Board][dut]:results[Board][dut][position]={}
                        data = open(cpath)
                        csvFile = csv.reader(data)
                        cnt=0
                        Tempdata = {"Time":[],"Prect":[],"PFO":[],'NewPFO':[],'Inlimit':[]}
                        for lines in csvFile:
                            print(cnt)
                            if cnt !=0:
                                if cnt > 4 and float(lines[2]) < 1:
                                    #considered next power started and get max prect value and find the power
                                    if max(Tempdata['Prect']) >= 15: 
                                        Power = 15
                                    elif max(Tempdata['Prect']) > 12.5 and max(Tempdata['Prect']) < 15:
                                        Power = 12.5
                                    elif max(Tempdata['Prect']) > 10 and max(Tempdata['Prect']) < 12:
                                        Power = 10
                                    elif max(Tempdata['Prect']) > 7.5 and max(Tempdata['Prect']) < 10:
                                        Power = 7.5
                                    elif max(Tempdata['Prect']) > 5 and max(Tempdata['Prect']) < 7.5:
                                        Power = 5
                                    elif max(Tempdata['Prect']) > 3.5 and max(Tempdata['Prect']) < 5:
                                        Power = 3.5
                                    # print('Power',Power,cnt)
                                    cnt=1
                                    if Power not in results[Board][dut][position]:results[Board][dut][position][Power]={}
                                    results[Board][dut][position][Power][run]=Tempdata
                                    Tempdata = {"Time":[],"Prect":[],"PFO":[],'NewPFO':[],'Inlimit':[]}
                                Inlimit = 'No'
                                Tempdata['Time'].append(lines[0])
                                Tempdata['Prect'].append(float(lines[2]))
                                #find limits for each power
                                if Power in jsondata['PowerLimits']:
                                    tolper = [float(Power) - ((float(Power)*jsondata['PowerLimits'][Power])/100),float(Power) + ((float(Power)*jsondata['PowerLimits'][Power])/100)]
                                    # print(Power, tolper)
                                    if (float(lines[14]) <= 350 and (float(lines[14]) >= -350)) and (float(lines[2]) >= tolper[0] and float(lines[2]) <= tolper[1]):
                                        Inlimit = 'Yes'
                                Tempdata['PFO'].append(float(lines[14]))
                                NewCircutLoss = ((pow(float(lines[8]),2))*offsetData['GRAD'])+offsetData['offset']
                                NewPFM = ((pow(float(lines[8]),2))*jsondata['Calculations']['AlphaFM']*jsondata['Calculations']['GFM'])+(jsondata['Calculations']['AlphaFMDC']*jsondata['Calculations']['GFMDC'])
                                Tempdata['NewPFO'].append((((float(lines[12])*float(lines[6]))-(NewPFM+float(lines[10])+NewCircutLoss))-(float(lines[1])))*1000)
                                Tempdata['Inlimit'].append(Inlimit)
                            cnt+=1
                        #considered next power started and get max prect value and find the power
                        if max(Tempdata['Prect']) >= 15: 
                            Power = 15
                        elif max(Tempdata['Prect']) > 12.5 and max(Tempdata['Prect']) < 15:
                            Power = 12.5
                        elif max(Tempdata['Prect']) > 10 and max(Tempdata['Prect']) < 12:
                            Power = 10
                        elif max(Tempdata['Prect']) > 7.5 and max(Tempdata['Prect']) < 10:
                            Power = 7.5
                        elif max(Tempdata['Prect']) > 5 and max(Tempdata['Prect']) < 7.5:
                            Power = 5
                        elif max(Tempdata['Prect']) > 3.5 and max(Tempdata['Prect']) < 5:
                            Power = 3.5
                        if Power not in results[Board][dut][position]:results[Board][dut][position][Power]={}
                        results[Board][dut][position][Power][run]=Tempdata
                    else:
                        # print(pathli)
                        finaldata = {"Time":[],"Prect":[],"PFO":[],'ACCurrent':[],'InverterVoltage':[],'DCCurrent':[],'CoilLoss':[],'ReceivedPower':[],'TxPower':[]}
                        #old format
                        dut = pathli[len(pathli)-5]
                        position = str(pathli[len(pathli)-4]).replace('(','').replace(')','').replace(',','_')
                        run = str(pathli[len(pathli)-3]).split('Run')[1]
                        Power = str(pathli[len(pathli)-2]).replace('W','')
                        # offsetData = jsondata['Calculations']['00'] if position == '0,0,0' else jsondata['Calculations']['22']
                        if dut not in results[Board]: results[Board][dut]={}
                        if position not in results[Board][dut]:results[Board][dut][position]={}
                        if Power not in results[Board][dut][position]:results[Board][dut][position][Power]={}
                        data = open(cpath)
                        csvFile = csv.reader(data)
                        cnt=0
                        # print(Board,dut,position,Power,run)
                        for lines in csvFile:
                            if cnt !=0:
                                # Inlimit = 'No'
                                finaldata['Time'].append(lines[0])
                                finaldata['Prect'].append(lines[2])
                                finaldata['PFO'].append(float(lines[14]))
                                finaldata['ACCurrent'].append(float(lines[8]))
                                finaldata['InverterVoltage'].append(float(lines[12]))
                                finaldata['DCCurrent'].append(float(lines[6]))
                                finaldata['CoilLoss'].append(float(lines[10]))
                                finaldata['ReceivedPower'].append(float(lines[1]))
                                finaldata['TxPower'].append(lines[13])
                            cnt+=1
                        # break
                        results[Board][dut][position][Power][run]=finaldata
        #export merged results to csv
        if len(results)>0:
            rows = []
            fields = ['Board', 'DUT', 'Position', 'Power','Run','PFO','Prect','Time','ACCurrent','InverterVoltage','DCCurrent','CoilLoss','ReceivedPower','TxPower']
            for Board in results:
                for DUT in results[Board]:
                    for pos in results[Board][DUT]:
                        for powr in results[Board][DUT][pos]:
                            for run in results[Board][DUT][pos][powr]:
                                for PFOval,Prectval,Timeval,ACCurrentval,InverterVoltageVal,DCCurrentval,CoilLossval,ReceivedPowerval,TxPowerval in zip(results[Board][DUT][pos][powr][run]['PFO'],
                                                                                        results[Board][DUT][pos][powr][run]['Prect'],
                                                                                        results[Board][DUT][pos][powr][run]['Time'],
                                                                                        results[Board][DUT][pos][powr][run]['ACCurrent'],
                                                                                        results[Board][DUT][pos][powr][run]['InverterVoltage'],
                                                                                        results[Board][DUT][pos][powr][run]['DCCurrent'],
                                                                                        results[Board][DUT][pos][powr][run]['CoilLoss'],
                                                                                        results[Board][DUT][pos][powr][run]['ReceivedPower'],
                                                                                        results[Board][DUT][pos][powr][run]['TxPower']):
                                    # rows.append({"Board":board,"DUT":DUT,"Position":pos,"Power":pow,"Run":run,"PFP":PFOval,"Prect":Prectval,"Time":Timeval})
                                    rows.append([Board,DUT,pos,powr,run,PFOval,Prectval,Timeval,ACCurrentval,InverterVoltageVal,DCCurrentval,CoilLossval,ReceivedPowerval,TxPowerval])
            if len(rows)>0:
                now = datetime.now()
                timestamp = now.strftime("%d%m%Y_%H%M%S")
                filename = "Results/MPP Excel Results/BIData_"+timestamp+'.csv'
                # writing to csv file
                with open(filename, 'w',newline='') as csvfile:
                    write = csv.writer(csvfile)
                    write.writerow(fields)
                    write.writerows(rows)
    def GenerateBIreport(self):
        #consider old and new file structure of the SW
        results={}
        BIData = self.master.JsettingsData['BIAnalyis']
        if len(BIData)>0:
            for proj in BIData:
                jsonpath=JsonOperations(proj)
                jsondata = jsonpath.read_file()
                Board = jsondata['TestToolInfo']['SerialNumber']
                #read from CSV
                if Board not in results:results[Board]={}
                #add csv data
                for cpath in BIData[proj]:
                    pathli = cpath.split('\\')
                    if 'input_new.json' in proj:
                        #new frmt
                        dut = jsondata['TestToolInfo']['DUTname']
                        position = jsondata['TestToolInfo']['Position']
                        offsetData = jsondata['Calculations']['00'] if position == '0,0,0' else jsondata['Calculations']['22']
                        run = str(pathli[len(pathli)-3]).split('Run')[1] 
                        Power=0
                        if jsondata['TestToolInfo']['DUTname'] not in results[Board]: results[Board][dut]={}
                        if jsondata['TestToolInfo']['Position'] not in results[Board][dut]:results[Board][dut][position]={}
                        data = open(cpath)
                        csvFile = csv.reader(data)
                        cnt=0
                        Tempdata = {"Time":[],"Prect":[],"PFO":[],'NewPFO':[],'Inlimit':[]}
                        for lines in csvFile:
                            print(cnt)
                            if cnt !=0:
                                if cnt > 4 and float(lines[2]) < 1:
                                    #considered next power started and get max prect value and find the power
                                    if max(Tempdata['Prect']) >= 15: 
                                        Power = 15
                                    elif max(Tempdata['Prect']) > 12.5 and max(Tempdata['Prect']) < 15:
                                        Power = 12.5
                                    elif max(Tempdata['Prect']) > 10 and max(Tempdata['Prect']) < 12:
                                        Power = 10
                                    elif max(Tempdata['Prect']) > 7.5 and max(Tempdata['Prect']) < 10:
                                        Power = 7.5
                                    elif max(Tempdata['Prect']) > 5 and max(Tempdata['Prect']) < 7.5:
                                        Power = 5
                                    elif max(Tempdata['Prect']) > 3.5 and max(Tempdata['Prect']) < 5:
                                        Power = 3.5
                                    # print('Power',Power,cnt)
                                    cnt=1
                                    if Power not in results[Board][dut][position]:results[Board][dut][position][Power]={}
                                    results[Board][dut][position][Power][run]=Tempdata
                                    Tempdata = {"Time":[],"Prect":[],"PFO":[],'NewPFO':[],'Inlimit':[]}
                                Inlimit = 'No'
                                Tempdata['Time'].append(lines[0])
                                Tempdata['Prect'].append(float(lines[2]))
                                #find limits for each power
                                if Power in jsondata['PowerLimits']:
                                    tolper = [float(Power) - ((float(Power)*jsondata['PowerLimits'][Power])/100),float(Power) + ((float(Power)*jsondata['PowerLimits'][Power])/100)]
                                    # print(Power, tolper)
                                    if (float(lines[14]) <= 350 and (float(lines[14]) >= -350)) and (float(lines[2]) >= tolper[0] and float(lines[2]) <= tolper[1]):
                                        Inlimit = 'Yes'
                                Tempdata['PFO'].append(float(lines[14]))
                                NewCircutLoss = ((pow(float(lines[8]),2))*offsetData['GRAD'])+offsetData['offset']
                                NewPFM = ((pow(float(lines[8]),2))*jsondata['Calculations']['AlphaFM']*jsondata['Calculations']['GFM'])+(jsondata['Calculations']['AlphaFMDC']*jsondata['Calculations']['GFMDC'])
                                Tempdata['NewPFO'].append((((float(lines[12])*float(lines[6]))-(NewPFM+float(lines[10])+NewCircutLoss))-(float(lines[1])))*1000)
                                Tempdata['Inlimit'].append(Inlimit)
                            cnt+=1
                        #considered next power started and get max prect value and find the power
                        if max(Tempdata['Prect']) >= 15: 
                            Power = 15
                        elif max(Tempdata['Prect']) > 12.5 and max(Tempdata['Prect']) < 15:
                            Power = 12.5
                        elif max(Tempdata['Prect']) > 10 and max(Tempdata['Prect']) < 12:
                            Power = 10
                        elif max(Tempdata['Prect']) > 7.5 and max(Tempdata['Prect']) < 10:
                            Power = 7.5
                        elif max(Tempdata['Prect']) > 5 and max(Tempdata['Prect']) < 7.5:
                            Power = 5
                        elif max(Tempdata['Prect']) > 3.5 and max(Tempdata['Prect']) < 5:
                            Power = 3.5
                        if Power not in results[Board][dut][position]:results[Board][dut][position][Power]={}
                        results[Board][dut][position][Power][run]=Tempdata
                    else:
                        finaldata = {"Time":[],"Prect":[],"PFO":[],'NewPFO':[],'Inlimit':[]}
                        #old format
                        dut = pathli[len(pathli)-5]
                        position = str(pathli[len(pathli)-4]).replace('(','').replace(')','').replace(',','_')
                        run = str(pathli[len(pathli)-3]).split('Run')[1]
                        Power = str(pathli[len(pathli)-2]).replace('W','')
                        offsetData = jsondata['Calculations']['00'] if position == '0,0,0' else jsondata['Calculations']['22']
                        if dut not in results[Board]: results[Board][dut]={}
                        if position not in results[Board][dut]:results[Board][dut][position]={}
                        if Power not in results[Board][dut][position]:results[Board][dut][position][Power]={}
                        data = open(cpath)
                        csvFile = csv.reader(data)
                        cnt=0
                        print(Board,dut,position,Power,run)
                        for lines in csvFile:
                            if cnt !=0:
                                Inlimit = 'No'
                                finaldata['Time'].append(lines[0])
                                finaldata['Prect'].append(lines[2])
                                #find limits for each power
                                if Power in jsondata['PowerLimits']:
                                    tolper = [float(Power) - ((float(Power)*jsondata['PowerLimits'][Power])/100),float(Power) + ((float(Power)*jsondata['PowerLimits'][Power])/100)]
                                    # print(Power, tolper)
                                    if (float(lines[14]) <= 350 and (float(lines[14]) >= -350)) and (float(lines[2]) >= tolper[0] and float(lines[2]) <= tolper[1]):
                                        Inlimit = 'Yes'
                                finaldata['PFO'].append(float(lines[14]))
                                NewCircutLoss = ((pow(float(lines[8]),2))*offsetData['GRAD'])+offsetData['offset']
                                NewPFM = ((pow(float(lines[8]),2))*jsondata['Calculations']['AlphaFM']*jsondata['Calculations']['GFM'])+(jsondata['Calculations']['AlphaFMDC']*jsondata['Calculations']['GFMDC'])
                                finaldata['NewPFO'].append((((float(lines[12])*float(lines[6]))-(NewPFM+float(lines[10])+NewCircutLoss))-(float(lines[1])))*1000)
                                finaldata['Inlimit'].append(Inlimit)
                            cnt+=1
                        # break
                        results[Board][dut][position][Power][run]=finaldata
        #export merged results to csv
        if len(results)>0:
            rows = []
            fields = ['Board', 'DUT', 'Position', 'Power','Run','PFO','Prect','Time','NewPFO','Inlimit']
            for board in results:
                for DUT in results[Board]:
                    for pos in results[Board][DUT]:
                        for powr in results[Board][DUT][pos]:
                            for run in results[Board][DUT][pos][powr]:
                                for PFOval,Prectval,Timeval,NewPFOval,Inlimitval in zip(results[Board][DUT][pos][powr][run]['PFO'],results[Board][DUT][pos][powr][run]['Prect'],results[Board][DUT][pos][powr][run]['Time'],results[Board][DUT][pos][powr][run]['NewPFO'],results[Board][DUT][pos][powr][run]['Inlimit']):
                                    # rows.append({"Board":board,"DUT":DUT,"Position":pos,"Power":pow,"Run":run,"PFP":PFOval,"Prect":Prectval,"Time":Timeval})
                                    rows.append([board,DUT,pos,powr,run,PFOval,Prectval,Timeval,NewPFOval,Inlimitval])
            if len(rows)>0:
                now = datetime.now()
                timestamp = now.strftime("%d%m%Y_%H%M%S")
                filename = "Results/MPP Excel Results/BIData_"+timestamp+'.csv'
                # writing to csv file
                with open(filename, 'w',newline='') as csvfile:
                    write = csv.writer(csvfile)
                    write.writerow(fields)
                    write.writerows(rows)

class Menu(tk.Frame):   
    def __init__(self, master, height=650, bg=None, width=100, x=0,y=0,grid=None):
        super().__init__(master, height=height, width=width,bg=bg)
        if grid is not None:
            self.grid(row=x,column=y)
        else:self.place(x=x,y=y)
class Buttons(tk.Button):
    def __init__(self, master,bg="#FFFFFF",bd=0,image=None,x=0,y=0,height=None,width=None,command=None,text=None,font=None,grid=None,name=None,fg=None):
        super().__init__(master,image=None,bg=bg,relief='raised',bd=bd,name=name)
        if height is not None: self['height'] = height
        if width is not None: self['width'] = width
        if command is not None: self['command']=command
        if image is not None: self['image']=image
        if text is not None: self['text']=text
        if font is not None: self['font']=font 
        self['fg']= fg if fg is not None else "#FFFFFF"
        if grid is not None:
            self.grid(row=x,column=y)
        else:self.place(x=x,y=y)
class Combo(ttk.Combobox):
    def __init__(self, master,width=10,bg=None,fg=None,val=None,x=0,y=0,grid=None,font=None,name=None,selectedVal=None,state=None):
        style = ttk.Style()
        style.theme_use("default")
        super().__init__(master,width=width,values=val,name=name)
        if font is not None: self['font']=font
        if state is not None:self['state']=state
        if fg is not None: 
            style.map('TCombobox', foreground=[('readonly', fg)])
            style.map('TCombobox', selectforeground=[('readonly', fg)])
        if bg is not None:
            style.map('TCombobox', fieldbackground=[('readonly',bg)])
            style.map('TCombobox', selectbackground=[('readonly', bg)])
        if selectedVal is not None:
            if selectedVal==True:
                self.set("Yes")
            elif selectedVal ==False:
                self.set('No')
            else: self.set(selectedVal)
        if grid is not None:
            self.grid(row=x,column=y)
        else:self.place(x=x,y=y)
class Labels(tk.Label):
    def __init__(self,master,x=0,y=0,text='',name=None,img=None,bg=None,fg=None,font=None,grid=None,width=None,anchor=None):
        super().__init__(master,text=text,name=name)
        if anchor is not None: self['anchor']=anchor
        if font is not None: self['font']=font
        if img is not None: self['image']=img
        if fg is not None: self['fg']=fg
        if bg is not None: self['bg']=bg
        if width is not None: self['width']=width
        if grid is not None:
            self.grid(row=x,column=y)
        else:self.place(x=x,y=y)
class Texts(tk.Text):
    def __init__(self,master,x=0,y=0,width=None,height=None,bg=None,fg=None,font=None,grid=None,wrap=None,state=None,text='',scrollbar=False):
        super().__init__(master,width=width,height=height,relief="flat",bd=0,highlightthickness=0)

        if bg is not None:
            self['bg'] = bg
        if fg is not None:
            self['fg'] = fg
        if font is not None:
            self['font'] = font
        if wrap is not None:
            self['wrap'] = wrap
        if state is not None:
            self['state'] = state
        if width is not None: self['width']=width

        if text:
            self.insert("1.0", text)

         # Make it read-only
        self.config(state="disabled")

        if grid is not None:
            self.grid(row=x, column=y)
        else:
            self.place(x=x, y=y)

        # # Optional scrollbar
        # if scrollbar:
        #     sb = tk.Scrollbar(master, command=self.yview)
        #     sb.place(x=x + (width * 7) + 2, y=y, height=height * 18)
        #     self.config(yscrollcommand=sb.set)
class Entries(tk.Entry):
    def __init__(self, master,width=10,x=0,y=0,font=None,textvar=None,grid=None,bg=None,fg=None,name=None):
        super().__init__(master,width=width,name=name)
        if font is not None: self['font']=font
        if bg is not None: self['bg']=bg
        if fg is not None: self['fg']=fg
        if textvar is not None: self.insert(0,textvar)
        if grid is not None:
            self.grid(row=x,column=y)
        else:
            self.place(x=x,y=y)
class ListBx(tk.Listbox):
    def __init__(self, master,width=10,height=10,font=None,name=None,grid=None,x=0,y=0,bg=None,fg=None,values=None,selectedVal=None):
        super().__init__(master,width=width,height=height,selectmode=tk.MULTIPLE,name=name,exportselection=False)
        if font is not None: self['font']=font
        if bg is not None: self['bg']=bg
        if fg is not None: self['fg']=fg
        if values is not None:
            pos=1
            for v in values:
                self.insert(pos,v)
                pos+=1
        if selectedVal is not None:
            for vs in selectedVal:
                id=0
                while id < self.size():
                    if self.get(id) == vs:
                        self.selection_set(id)
                    id+=1
        if grid is not None:
            self.grid(row=x,column=y)
        else:
            self.place(x=x,y=y)
    def UpdateValues(self,values):
        if self.winfo_exists():
            self.delete(0,tk.END)
            pos=1
            for v in values:
                self.insert(pos,v)
                pos+=1
class CheckBtn(tk.Checkbutton):
    def __init__(self,master,font=None,name='',x=0,y=0,grid=None,bg=None,fg=None,selectedVal=None,text=None,command=None):
        super().__init__(master,name=name,justify=tk.LEFT)
        if font is not None: self['font']=font
        if text is not None: self['text']=text
        if command is not None: self['command']=command
        if fg is not None:
            self['fg']=fg
            self['selectcolor'] = '#D1DADC'
        if bg is not None:
            self['bg'] = self['activebackground'] =bg
            if selectedVal ==True : 
                    self.select()
            else: self.deselect()
        if grid is not None:
            self.grid(row=x,column=y)
        else:
            self.place(x=x,y=y)

class DropdownWithCheckboxes:
    def __init__(self, root, font=None, fg=None, bg=None, width=200, layout='pack',x=0, y=0, row=None, column=None, options=None, selected_options=None):
        self.root = root
        self.font = font
        self.fg = fg
        self.bg = bg
        self.width = width
        self.options = options or []
        self.selected_options = selected_options or []
        self.dropdown_visible = False

        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(root, textvariable=self.entry_var, font=self.font, state="readonly")
        if layout == 'grid' and row is not None and column is not None:
            self.entry.grid(row=row, column=column)
        else:
            self.entry.place(x=x, y=y, width=self.width)

        self.entry.bind("<Button-1>", self.toggle_dropdown)
        self.root.bind_all("<Button-1>", self.on_click_anywhere, "+")

        self.checkbox_vars = [(tk.BooleanVar(value=label in self.selected_options), label) for label in self.options]
        self.update_entry_text()

        # Create dropdown frame but keep it hidden initially
        self.dropdown_frame = tk.Frame(self.root, bd=1, relief="solid", width=self.width)
        self.canvas = tk.Canvas(self.dropdown_frame, width=self.width-20, height=10)
        self.scrollbar = ttk.Scrollbar(self.dropdown_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>",lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        for var, label in self.checkbox_vars:
            cb = tk.Checkbutton(self.scrollable_frame, text=label, variable=var, font=self.font,fg=self.fg, bg=self.bg, anchor="w", command=self.update_entry_text)
            cb.pack(anchor="w", padx=5, pady=2, fill="x")

        # self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def toggle_dropdown(self, event=None):
        if self.dropdown_visible:
            self.hide_dropdown()
        else:
            self.show_dropdown()

    def show_dropdown(self):
        self.dropdown_visible = True
        entry_x = self.entry.winfo_x()
        entry_y = self.entry.winfo_y() + self.entry.winfo_height()
        self.dropdown_frame.place(x=entry_x, y=entry_y, width=self.width, height=30 * len(self.options) if len(self.options) < 6 else 220)
        self.dropdown_frame.lift()

    def hide_dropdown(self):
        self.dropdown_visible = False
        self.dropdown_frame.place_forget()

    def on_click_anywhere(self, event):
        if not self.dropdown_visible:
            return
        widget = event.widget

        # Check if click is inside dropdown or on entry
        if self._is_child_of(widget, self.dropdown_frame) or widget == self.entry:
            return
        self.hide_dropdown()
    def _is_child_of(self, widget, parent):
        # Recursively check if widget is child of parent
        while widget:
            if widget == parent:
                return True
            widget = widget.master
        return False

    def update_entry_text(self):
        selected = [label for var, label in self.checkbox_vars if var.get()]
        self.entry_var.set(", ".join(selected))

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        # if self.dropdown_visible:
        #     self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        if self.dropdown_visible:
            if event.state & 0x0001:  # Shift key is pressed
                self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def get_selected(self):
        return [label for var, label in self.checkbox_vars if var.get()]


            
APP=MPPGUI()
APP.CreateAPP()