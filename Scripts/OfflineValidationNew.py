import os
import sys
sys.path.append('Scripts')
import importlib
import traceback
import uuid
# import zipfile
from MainModule import JsonOperations,APIOperations,GeneralMethods


from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from datetime import datetime,date
from SQLite import SQLiteConnection
import traceback
import json
#offline validation , packet
class TestValidation():
    def __init__(self,TestID="TPT_TD_8_4_11_4",TestCaseName="Test",ProjectJson='',TracePath='',BackupJson=''):
        # self.timing_map = {"Timings":{},"Measures":{},"OtherChecks":{}}
        self.timing_map = {}
        self.GeneralChecks={}
        self.TClogs = []
        self.stability=None
        self.initialVoltage=None
        self.initialCurrent = None
        self.SQLConn = SQLiteConnection()
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
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.JPayLoadCheck = JsonOperations('json/PayLoadChecks.json')
        self.JPayLoadCheckData = self.JPayLoadCheck.read_file()
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        if self.Certification in ["2.0.1","2.1.0","2.2.1","2.3.0"]:
            self.EPRC_pkt = "Extended_Power_Receiver_Capabilities"
        else:
            self.EPRC_pkt = "Extended Power Receiver Capabilities"
           
        
        
 
        # self.Json_TC = self.JMOIData[self.mode][self.TestID]
        #Global Vars
        self.TestCaseName = TestCaseName
        self.TestID=TestID
        self.mode = self.JAllMOIData['Mode']
        self.ProjectJson = ProjectJson
        self.TracePath = TracePath
        self.BackupJson = BackupJson
        self.Product = self.JAllMOIData['Product']
        CTS = JsonOperations(f'json/CTSvalidation/{self.Product}{self.mode}.json')
        self.JCTSData =CTS.read_file()
        self.Header = {}
        #Timing checks setup_________________________________________________________________
        self.JTime = JsonOperations('json/TimingSetup.json')
        self.JTimeData =self.JTime.read_file()
        #CTS checks setup____________________________________________________________________
        # self.JCTS = JsonOperations(f"json/CTSvalidation/{self.JsettingsData['Offline_validation']['CTSConfig']}")
        # self.JCTSData = self.JCTS.read_file()
        self.JGenCheck = JsonOperations('json/GeneralChecks.json')
        self.JGenCheckData = self.JGenCheck.read_file()
        self.TimeTolr = self.JMOIData['TT_4']
        self.Json_Def = self.JMOIData['default_Values']
        self.JTestConf = JsonOperations('json/TestConfig.json')
        self.JTestConfData = self.JTestConf.read_file()  
        self.JPhaPkt = JsonOperations('json/PhasePackets.json')
        self.JPhaPktData = self.JPhaPkt.read_file()  
        self.JTCP = JsonOperations('json/Test_config_properties.json')
        self.JTCPData = self.JTCP.read_file()
        self.FinalRep = JsonOperations(self.JTCPData['test_config_data']['Report_path'])
        self.FinalRepData = self.FinalRep.read_file()
        self.conRep = JsonOperations(self.JsettingsData['ConsolidatedJSON'])
        self.conRepData = self.conRep.read_file()
        #_start validation___________________________________________________________________
        self.TCRemarks = []
        self.update_TClogs("General",f"Validation started for : {self.TestID}")
        self.UpdateHeaderInfo()
        #Get Packets___________________________________________________________________________
        self.PktAPI = APIOperations(url=self.JapiData[self.Product][self.mode]['GetCCLinePackets'],retype='json')
        self.file_list = self.PktAPI.GetRequest()
        self.PlotMethod = PlotMethods(Header=self.Header)
       
        #Define the offline validation module 
        self.PktMethod = PacketMethods(file_list=self.file_list,Header=self.Header)
        # print(self.Header)
        self.flows = self.SegricatePackets()
        # If the Test Contains TWO Trace files then add the TC in List and store the final Limts in Json
        if self.TestID in ["CMAG001_01_Magnetic_Cover_Presence_Check"]:  
            self.TestResultsjson = JsonOperations("json/TestResults.json")
            self.TestData = self.TestResultsjson.read_file()
            if self.TestID in self.TestData['FileList_Data'].keys():
                temp=self.file_list
                self.file_list = self.TestData['FileList_Data'][self.TestID]['Json']
                self.PktMethod.file_list=self.file_list
                self.TestData['FileList_Data'][self.TestID]['flows']=self.SegricatePackets()
                self.TestResultsjson.update_file(self.TestData)
                self.file_list =self.PktMethod.file_list= temp
               
        self.stability = self.flows
        # print(self.flows)
        self.GetAllPackets()    
        self.UpdateToJsonReport()


        # print(self.timing_map)
        # print(self.TimingChecksGeneral())
        # print(self.Header)
### Main Functions #######################################################################################################################
    #To Fetch headers of Testcase from various sources.
    def UpdateHeaderInfo(self):
        try:
            # print("ProjectJson:",self.ProjectJson)
            
            now = datetime.now()
            timestamp = now.strftime("%d%m%Y_%H%M%S")
            jsondata = JsonOperations(self.ProjectJson)
            self.jsonValues = jsondata.read_file()
            # self.Header['DBStatus']= 'NotUpdated'
            self.Header['UID'] = str(uuid.uuid1())
            self.Header['TestcaseID'] = self.TestID
            self.Header['TestcaseName']= self.TestCaseName
            # print("TestcaseName:",self.Header['TestcaseName'])
            # self.Header['ChapterID']=self.GetTCValuesfromBackUpJSON("_chapter")
            self.Header['ChapterName']=self.GetTCValuesfromBackUpJSON("_chapter")
            self.Header['Transmitter']= self.JQIData[self.Product][self.mode]['transmitterType']
            self.Header['potentialPower']=self.JQIData[self.Product][self.mode]['potentialPower']
            self.Header['Coil'] = self.GetJSONTCData(self.TestID,self.BackupJson,"TCcoil") #self.GetJSONTCData(self.TestID,self.jsonValues,"TCcoil")
            # print("potentialPower:",self.Header['potentialPower'])
            # print("Coil:",self.Header['Coil'])
            if 'TestToolInfo' in self.jsonValues:
                self.Header['SWVersion'] = self.jsonValues['TestToolInfo']['SoftwareVersion']
                self.Header['FWVersion'] = self.jsonValues['TestToolInfo']['FirmwareVersion']
                self.Header['HWVersion'] = self.jsonValues['TestToolInfo']['HardwareVersion']
                self.Header['BoardNo'] = self.jsonValues['TestToolInfo']['SerialNumber']
                # self.Header['BoardModel'] = jsonValues['TestToolInfo']['ModelName']
            elif 'TestPlatformInfo' in self.jsonValues:
                self.Header['SWVersion'] = self.jsonValues['TestPlatformInfo']['SoftwareVersion']
                self.Header['FWVersion'] = self.jsonValues['TestPlatformInfo']['FirmwareVersion']
                self.Header['HWVersion'] = self.jsonValues['TestPlatformInfo']['HardwareVersion']
                self.Header['BoardNo'] = self.jsonValues['TestPlatformInfo']['SerialNumber']
            self.Header['QiID'] = self.jsonValues['DutInfo']['QiId']
            self.Header['BoardModel'] = f"{self.JAllMOIData['Product']}_{self.JAllMOIData['Mode']}"
            self.Header['Certification'] = self.jsonValues['TestExecutionDetails']['SpecVersion']
            self.Header['CapturePath'] = self.TracePath
            pathlist = self.TracePath.split("\\")
            # print(pathlist)
            self.Header['ProjectName'] = pathlist[len(pathlist)-4]
            self.Header['Run'] = pathlist[len(pathlist)-3]
            #TBD 
            self.Header['TestedTime_start']="NA"
            self.Header['TestedTime_end']="NA"
            self.Header['TestedTime'] = "NA"
            self.UpdateTestRunTimings(self.TestID,self.jsonValues)
            self.Header['ValidatedTime']=timestamp
            self.Header['DUTName']= self.jsonValues['DutInfo']['BrandName']
            self.Header['DUTID']= self.jsonValues['DutInfo']['ProductName']
            self.Header['DUTSL']= self.jsonValues['TestToolInfo']['SerialNumber']
            
            self.Header['TestLab']=self.JQIData[self.Product][self.mode]['testLab'] = self.jsonValues['TestLab']['LabName'] 
            self.Header['Engineer']=self.JQIData[self.Product][self.mode]['testEngineer'] = self.jsonValues['TestLab']['TestEngineer']
            self.Header['TCresult']='NA'
            self.Header['SWresult'] = self.GetJSONTCData(self.TestID,self.BackupJson,"TCresult")
            self.Header['Product'] = self.Product
            self.Header['Mode'] = self.mode
            # self.Header['CTSVersion'] = self.JCTSData['Version']
            # self.Header['Remarks']=[]
        except Exception as e:
            traceback.print_exc()
            self.update_TClogs("Exception",f"UpdateHeaderInfo : {str(e)}")
    #-to find the last flow of the testcase pacets, to apply the validation. return last flow [start index , end index]
    def SegricatePackets(self):
        try:
            
            packets = []
            TCLimit = []
            limit=[]
            #Ensure the limit by checking the grp testscases
            tmpid = 0
            self.SubTClist = []
            # print("end:",len(self.file_list))
            while tmpid < len(self.file_list):
                if all(res in self.file_list[tmpid]['pktType'] for res in ['Test_Started']):
                    self.SubTClist.append(tmpid)
                tmpid+=1
            TCLimit = [0,len(self.file_list)]
            if self.TestID in ['TEST_PTX_CPX_PNG_S01_TIM_002']:
                return  {1:{"Limit":[0,len(self.file_list)-1],"Flow":1},2:None}
            # if self.TestID in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
            #     return {1:{'Limit': TCLimit, 'Flow': 1}, 2: None}
            # print(self.SubTClist)
            if len(self.SubTClist)>1:
                TCsubID = self.GetTCindexfromGroupRun()
                # print(TCsubID)
                TCLimit = [self.SubTClist[TCsubID],self.SubTClist[TCsubID+1]-1] if len(self.SubTClist)>TCsubID+1 else [self.SubTClist[TCsubID],len(self.file_list)-1]
                # print(TCLimit)
            # print("TCLimit:",TCLimit)
            sid = TCLimit[0]
            while sid < TCLimit[1]:
                # print(self.file_list[sid]['pktType'])
                if all(rs in self.file_list[sid].get('value') for rs in ['Test_Started']) if self.mode=="TPR" else  all(rs in self.file_list[sid].get('pktType') for rs in ['Test_Started']):
                    eid = sid+1
                    # print(eid)
                    while eid < TCLimit[1]-1:
                        if all(rs in self.file_list[eid].get('value') for rs in ['Test_Stop']) if self.mode=="TPR" else all(rs in self.file_list[eid].get('pktType') for rs in ['Test_Stop']): 
                            limit=[sid,eid]
                            break
                        elif all(rs in self.file_list[eid].get('pktType') for rs in ['Shutdown','next_subtest']): 
                            limit=[sid,eid]
                            break
                        eid+=1
                    if len(limit)==0:limit=[sid,eid]
                    break
                sid+=1
            # print(limit)
            if len(limit)>1:
                packets = {}
                cnt = 0
                id = limit[0]
                while id < limit[1]:
                    start = 0
                    end = 0
                    if any(res in self.file_list[id].get('pktType') for res in ['Ping Detected','Ping Initiated']):
                        # print('pd',id)
                        #find Shutdown
                        sd= self.PktMethod.GetPacketDetails(packet='Shutdown',limit=[id,limit[1]],Type = "TesterMsg")

                        if len(sd)>2:
                            # print('sd',sd)
                            #ensure no PD recevied btw PD-SD
                            if self.mode == "TPR":
                                ilPD = self.PktMethod.GetPacketDetails(packet='Ping Detected',limit=[id+1,sd[2]],Type = "TesterMsg")
                            else:
                                ilPD = self.PktMethod.GetPacketDetails(packet='Ping Initiated',limit=[id+1,sd[2]],Type = "TesterMsg")
                            if len(ilPD)>1: id = ilPD[2]
                            #check TestStop recevied before SD
                            ilTS = self.PktMethod.GetPacketDetails(packet='Test_Stop',limit=[id,sd[2]],Type = "TesterMsg")
                            if len(ilTS)>1: sd = ilTS
                            start = id
                            end = sd[2]
                            id = end
                        else:
                            sd= self.PktMethod.GetPacketDetails(packet='Test_Stop',limit=[id,limit[1]],Type = "TesterMsg")
                            if len(sd)>2:
                                # print('ts',sd)
                                #ensure no PD recevied btw PD-SD
                                if self.mode == "TPR":
                                    ilPD = self.PktMethod.GetPacketDetails(packet='Ping Detected',limit=[id+1,sd[2]],Type = "TesterMsg")
                                else:ilPD = self.PktMethod.GetPacketDetails(packet='Ping Initiated',limit=[id+1,sd[2]],Type = "TesterMsg")
                                if len(ilPD)>1: id = ilPD[2]
                                start = id
                                end = sd[2]
                                id=end
                            else:
                                start = id
                                end = limit[1]
                                id=end
                        #consider seq. has length > 3 and ss in flow
                        SS = self.PktMethod.GetPacketDetails(packet='Signal strength',limit=[start,end])
                        # print(SS,start,end)
                        if len(SS)>2:
                            if (end -start) > 4 and len(SS)>1: # Refer Segregation Function in Notes               
                                cnt +=1
                                # print(start,end)
                                index = self.Findflow([start,end]) if self.Product=='MPP' else 1
                                packets[cnt]={"Limit":[start,end],"Flow":index}
                            else: # Eswar 
                                if self.mode=='TPR' and self.Product=='C3' and self.Header['ChapterName'] in ['In_Power_Transfer_Tests']:
                                    if end-start >1:
                                        cnt +=1
                                        packets[cnt]={"Limit":[start,end],"Flow":1}
                        else:
                            #check for ENDpower
                            EP = self.PktMethod.GetPacketDetails(packet='End Power Transfer',limit=[start,end])
                            # print(EP)
                            if len(EP)>2:
                                cnt +=1
                                index = self.Findflow([start,end]) if self.Product=='MPP' else 1
                                packets[cnt]={"Limit":[start,end],"Flow":index}
                            else: # Eswar - to handle C3-TPR ping phase
                                if self.mode=='TPR' and self.Product=='C3'  and self.Header['ChapterName'] in ['Ping_Phase_Tests','Disconnected_Load_Tests']:
                                    if end-start >1:
                                        cnt +=1
                                        packets[cnt]={"Limit":[start,end],"Flow":1}
                                    # if self.TestID in ['TEST_PTX_CPX_PNG_S01_TIM_002']:packets[cnt]={"Limit":[start,end],"Flow":1}
                    else: id+=1
                # print('Packetflow',packets)
                #consider last 2 seq.
                flow1=None
                multiflow1 = []
                flow2=None
                tmpflow1=None
                for seq in packets:
                    if packets[seq]['Flow']!=0:
                        if packets[seq]['Flow']==1 and flow2==None:
                            flow1 = packets[seq]
                            multiflow1.append(packets[seq])
                        elif packets[seq]['Flow']==2 and flow1!=None:
                            if tmpflow1 ==None:
                                flow2 = packets[seq]
                            else:
                                #Ensure the current flow has the execution count else consider the previous flow
                                # print(tmpflow1['Limit'][0],flow2['Limit'][1])
                                if self.mode == "TPR":
                                    # print("limits:")
                                    # print(tmpflow1)
                                    # print(flow2)
                                    # print(packets[seq])
                                    expkt = self.PktMethod.GetPacketDetails(packet="Execution_count_no",limit=tmpflow1['Limit'],Type="TesterMsg") #self.GetPacketDetails(packet="Execution_count_no",limit=[tmpflow1['Limit'][0],flow2['Limit'][1]])
                                    if len(expkt)>2:
                                        flow1=tmpflow1
                                        flow2 = packets[seq]
                                        tmpflow1=None
                                else:
                                    if (packets[seq]['Limit'][1] - packets[seq]['Limit'][0]) >5:
                                        flow1=tmpflow1
                                        flow2 = packets[seq]
                                        tmpflow1=None
                        elif  packets[seq]['Flow']==1 and flow2!=None:
                            tmpflow1=packets[seq]
                
                print({1:flow1,2:flow2})
                if self.Product=='MPP' and self.mode=='TPT' and self.Header['ChapterName'] in ['Pre_power_transfer_test']: return {1:None, 2:{'Limit':[0,len(self.file_list)-1],'Flow':2}}
                if self.Product=="MPP" and self.mode=='TPR':
                    # print("multiflow1:",multiflow1)
                    if multiflow1:
                        flow1 = max(multiflow1, key=lambda x: x['Limit'][1] - x['Limit'][0])
                        # print({1:max(multiflow1, key=lambda x: x['Limit'][1] - x['Limit'][0]),2:flow2})
                        if self.TestID not in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
                            if flow1 is None : self.TCRemarks.append(["128Khz Flow not found for the testcase","Fail"])
                            # print(self.TestCaseName, self.TestID)
                            if self.TestID not in ["MPP_PTX_CPX_NEG_ENTRY_INIT","MPP_PTX_CPX_NEG_ERROR_STATUS_RESET","MPP_PTX_CPX_PNG_DP_LEVEL_ERROR","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC1","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC2","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC3","MPP_PTX_CPX_NEG_ERROR_STATUS_TC2","MPP_PTX_CPX_NEG_ERROR_STATUS_TC1","TSDF002_01_Unique_PTx_Identifier","MPP_PTX_NEG_POW_KEST_SLIDING","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC1","MPP_PTX_CPX_PNG_T_NOPOWER_RESET","MPP_PTX_POW_MAX_GAIN_SWEEP_PROCEDURE","MPP_PTX_POW_Digital_Ping_128kHz_P1","MPP_PTX_POW_Digital_Ping_128kHz_P2","MPP_PTX_POW_Digital_Ping_128kHz_P3","MPP_PTX_POW_Digital_Ping_128kHz_P4","MPP_PTX_CPX_GENCOM_MPP_PRIORITY","MPP_PTX_CPX_NEG_ILL_001","MPP_PTX_CPX_NEG_ILL_002","MPP_PTX_CPX_NEG_ILL_003","MPP_PTX_CPX_NEG_ILL_004","MPP_PTX_CPX_NEG_ILL_005","MPP_PTX_CPX_NEG_ILL_006","MPP_PTX_CPX_NEG_ILL_007","MPP_PTX_CPX_NEG_ILL_008","MPP_PTX_CPX_NEG_ILL_009","MPP_PTX_CPX_NEG_ILL_010","MPP_PTX_CPX_NEG_ILL_011","MPP_PTX_CPX_NEG_ILL_012","MPP_PTX_CPX_NEG_ILL_013","MPP_PTX_CPX_NEG_ILL_014","MPP_PTX_POW_Digital_Ping_360_OV_LPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_NPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_HPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_CPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_CPM_TC2","MPP_PTX_POW_Digital_Ping_360_OV_LPM_TC2","MPP_PTX_POW_Digital_Ping_360_OV_NPM_TC2","MPP_PTX_POW_Digital_Ping_360_OV_HPM_TC2","MPP_PTX_POW_KEst_P1","MPP_PTX_POW_KEst_P2","MPP_PTX_CPX_PNG_RX_IDENTIFICATION_TC3"]:
                                if flow2 is None : self.TCRemarks.append(["360Khz Flow not found for the testcase","Inconclusive"])
                
                return {1:flow1,2:flow2}
        except Exception as e:
            er = traceback.print_exc()
            self.update_TClogs("Exception",f"SegricatePackets {str(e)}")
    #-categorise packets into phase wise , with its responses
    def GetAllPackets(self):
        if self.TestID in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
            self.flows = {1: {'Limit': [0, len(self.file_list)-1], 'Flow': 1}, 2: None}
        # print("flows:",self.flows)
        if self.flows is not None:
            for flwID in self.flows:
               
                if self.flows[flwID] is not None:
                   
                    if flwID not in self.timing_map:self.timing_map[flwID]={}
                    FlowLimit = self.flows[flwID]['Limit']
                    # print("FlowLimit:",FlowLimit)
                    id = FlowLimit[0]
                    if self.TestID not in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
                        while id < FlowLimit[1]:
                            if self.PktMethod.GetPacketType(id)=='Packet':
                                phase = 'General' if self.file_list[id]['description']=='' else self.file_list[id]['description']
                                if phase not in self.timing_map[flwID]:self.timing_map[flwID][phase]={}
                                packet =  self.file_list[id]['pktType']
                                if packet not in self.timing_map[flwID][phase]:self.timing_map[flwID][phase][packet]=[]
                                #check for the response
                                rid = id+1
                                while rid <= FlowLimit[1]:
                                    if self.PktMethod.GetPacketType(rid)=='Response':
                                        self.timing_map[flwID][phase][packet].append([[id,self.file_list[id]['value'],self.file_list[id]['startTime'],self.file_list[id]['stopTime']],[rid,self.file_list[rid]['pktType'],self.file_list[rid]['startTime'],self.file_list[rid]['stopTime']]])
                                        id=rid+1
                                        break
                                    elif self.PktMethod.GetPacketType(rid)=='Packet':
                                        self.timing_map[flwID][phase][packet].append([[id,self.file_list[id]['value'],self.file_list[id]['startTime'],self.file_list[id]['stopTime']]])
                                        id=rid
                                        break
                                    if rid==FlowLimit[1]:
                                        self.timing_map[flwID][phase][packet].append([[id,self.file_list[id]['value'],self.file_list[id]['startTime'],self.file_list[id]['stopTime']]])
                                        id=rid
                                        break
                                    rid+=1
                            else:id+=1
                    #Add General Packets
                    # print("timing_map1:",self.timing_map)
                    self.timing_map[flwID]['General']={}
                    self.timing_map[flwID]['General']['PD']=[[[FlowLimit[0],self.file_list[FlowLimit[0]]['value'],self.file_list[FlowLimit[0]]['startTime'],self.file_list[FlowLimit[0]]['stopTime']]]]
                    self.timing_map[flwID]['General']['SD']=[[[FlowLimit[1],self.file_list[FlowLimit[1]]['value'],self.file_list[FlowLimit[1]]['startTime'],self.file_list[FlowLimit[1]]['stopTime']]]]
                    #Get Freq data
                    res = self.PktMethod.GetPacketDetails(value='FOP:',limit=FlowLimit,Type = "TesterMsg")
                    if len(res)>2:
                        self.timing_map[flwID]['General']['FOP'] =[res[2],self.file_list[res[2]]['value'],res[0],res[1]]
                    #Add Loads
                    self.timing_map[flwID]['Loads'] =[]
                    LoadLimit = [self.timing_map[flwID]['General']['PD'][0][0][0],self.timing_map[flwID]['General']['SD'][0][0][0]]
                    Lid = LoadLimit[0]

                    while Lid < LoadLimit[1]:
                        if 'Set_Load' in self.file_list[Lid]['pktType']:
                            self.timing_map[flwID]['Loads'].append([Lid,self.file_list[Lid]['pktType'],self.file_list[Lid]['startTime'],self.file_list[Lid]['stopTime']])
                        Lid+=1
                    #Add timing checks
                    self.timing_map[flwID]['Timings']=self.TimingChecksGeneral(flwID,FlowLimit)

                    if self.Product == "C3" or self.mode=='TPT' :
                        module_path = f"OfflineValidationModules.{self.Product}{self.mode}.V_{self.Certification.replace('.', '_')}.CTSChecks{self.Product}{self.mode}"
                        try:spec = importlib.util.find_spec(module_path)
                        except ModuleNotFoundError : spec= None
                        if spec is not None:
                            module = importlib.import_module(module_path)
                            CTSChecks= getattr(module, f"CTSChecks_{self.Product}{self.mode}")
                        else:
                            module_path = f"OfflineValidationModules.{self.Product}{self.mode}.Backward.CTSChecks{self.Product}{self.mode}"
                            module = importlib.import_module(module_path)
                            CTSChecks = getattr(module, f"CTSChecks_{self.Product}{self.mode}")
                        self.CTSChecksOBJ=CTSChecks(Header=self.Header,file_list=self.file_list,JapiData=self.JapiData,BackupJson=self.BackupJson,ProjectJson=self.ProjectJson)
                        self.timing_map[flwID]['Measures']= self.MeasuresCheck(flwID,self.flows)

                    else:
                        if self.mode=="TPR":
                            Coil = ""
                            if self.Header['Coil'] == "TPR#MPP1":
                                Coil = "MPPTPR1"
                                module_path = f"OfflineValidationModules.{self.Product}{self.mode}.V_{self.Certification.replace('.', '_')}.MPPTPR1"
                                try:spec = importlib.util.find_spec(module_path)
                                except ModuleNotFoundError : spec= None
                                if spec is not None:
                                    module = importlib.import_module(module_path)
                                    CTSChecks= getattr(module, f"CTSChecks_MPP_TPR1")
                                else:
                                    module_path = f"OfflineValidationModules.{self.Product}{self.mode}.Backward.MPPTPR1"
                                    module = importlib.import_module(module_path)
                                    CTSChecks = getattr(module, f"CTSChecks_MPP_TPR1")
                                
                                # self.CTSChecks_obj1 = CTSChecks_MPP_TPR1(Header=self.Header,file_list=self.file_list,JapiData=self.JapiData,BackupJson=self.BackupJson,ProjectJson=self.ProjectJson)
                                # self.timing_map[flwID]['Measures']= self.CTSChecks_MPPTPR1.MeasuresCheck(flwID,self.flows,self.timing_map)
                            elif self.Header['Coil'] == "TPR#MPP4" or self.Header['Coil'] == "TPR_MPP4":
                                Coil = "MPPTPR4"
                                module_path = f"OfflineValidationModules.{self.Product}{self.mode}.V_{self.Certification.replace('.', '_')}.MPPTPR4"
                                try:spec = importlib.util.find_spec(module_path)
                                except ModuleNotFoundError : spec= None
                                if spec is not None:
                                    module = importlib.import_module(module_path)
                                    CTSChecks= getattr(module, f"CTSChecks_MPP_TPR4")
                                else:
                                    module_path = f"OfflineValidationModules.{self.Product}{self.mode}.Backward.MPPTPR4"
                                    module = importlib.import_module(module_path)
                                    CTSChecks = getattr(module, f"CTSChecks_MPP_TPR4")
                                
                            self.CTSChecksOBJ=CTSChecks(Header=self.Header,file_list=self.file_list,JapiData=self.JapiData,BackupJson=self.BackupJson,ProjectJson=self.ProjectJson)
                            self.timing_map[flwID]['Measures']= self.MeasuresCheck2(flwID,self.flows,Coil)
                            # print("Measures:",self.timing_map[flwID]['Measures'])
                       
                        
                    # if self.TestID not in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
                    self.timing_map[flwID]['Others']= self.GeneralCheck(flwID)
                    # print("Header TC result:",self.Header['TCresult'])
                    # print("Others",self.timing_map[flwID]['Others']["TestIssues_Details"])
                    if self.Product=='MPP' and self.mode=='TPR':
                        for chks in self.timing_map[flwID]['Others']["TestIssues_Details"]:
                            if "Fail" in chks[1]:
                                if "Inconclusive" in self.Header['TCresult']:
                                    self.Header['TCresult']='Inconclusive'
                                    break
                                else: self.Header['TCresult']='Fail'
                                
                            elif "Inconclusive" in chks[1]:
                                self.Header['TCresult']='Inconclusive'
                                break
                                
                        
                    self.PayLoadCheck(flwID)

    
    def MeasuresCheck(self,flwID,flows):
        try:
            AllMeasures={}
            print(self.Header['TestcaseID'])
            if self.Header['TestcaseID'] in self.JCTSData[self.Product][self.mode]:
                if self.Certification in self.JCTSData[self.Product][self.mode][self.Header['TestcaseID']]['Certifications']:
                    CTSJson=self.JCTSData[self.Product][self.mode][self.Header['TestcaseID']]['CTSChecks']
                    AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)   
                else:
                    NotalEnabled=False
                    if self.JCTSData[self.Product][self.mode][self.Header['TestcaseID']][self.Certification].get("Notal",False):
                        for  Notal in self.JCTSData[self.Product][self.mode][self.Header['TestcaseID']][self.Certification]['Notal']:
                            if Notal in self.GetNotals():
                                NotalEnabled=True
                                CTSJson= self.JCTSData[self.Product][self.mode][self.Header['TestcaseID']][self.Certification]['Notal'][Notal]
                                AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)

                    if not NotalEnabled:
                        CTSJson=self.JCTSData[self.Product][self.mode][self.Header['TestcaseID']][self.Certification]['CTS']
                        AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)

            print('Measures',AllMeasures)
            return(AllMeasures)
        except Exception as e:
            traceback.print_exc() 
    

    def MeasuresCheck2(self,flwID,flows,Coil):
        # print("Certification:",self.Certification)
        self.flows = flows
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        try:
            AllMeasures={}
            print("TestcaseID:",self.Header['TestcaseID'])
            if self.Header['TestcaseID'] in self.JCTSData[Coil]:
                notal_executed = False
                # Notal testcases
                if self.JCTSData[Coil][self.Header['TestcaseID']].get("Notal"):
                    if self.JCTSData[Coil][self.Header['TestcaseID']]["Notal"].get(self.Certification):
                        if len(self.JCTSData[Coil][self.Header['TestcaseID']]["Notal"][self.Certification].keys()) >0:
                            for notal in self.JCTSData[Coil][self.Header['TestcaseID']]["Notal"][self.Certification]:
                                if notal in self.GetNotals():
                                    CTSJson= self.JCTSData[Coil][self.Header['TestcaseID']]["Notal"][self.Certification][notal]
                                    AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)
                                    notal_executed = True

                # Normal testcases
                if not notal_executed:
                    
                    # if self.Certification in self.JCTSData[Coil][self.Header['TestcaseID']]['common']['Certifications']:
                    #     CTSJson=self.JCTSData[Coil][self.Header['TestcaseID']]['common']['CTSChecks']
                    #     AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)
                    
                    # if self.JCTSData[Coil][self.Header['TestcaseID']].get(self.Certification):
                    #     CTSJson=self.JCTSData[Coil][self.Header['TestcaseID']][self.Certification]
                    #     common_keys = list(CTSJson.keys())
                    #     CertMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)
                    #     AllMeasures.update(CertMeasures)



                    
                    common_keys = []
                    if self.JCTSData[Coil][self.Header['TestcaseID']].get(self.Certification):
                        CTSJson=self.JCTSData[Coil][self.Header['TestcaseID']][self.Certification]['CTSChecks']
                        common_keys = list(CTSJson.keys())
                        AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)

                    if self.Certification in self.JCTSData[Coil][self.Header['TestcaseID']]['common']['Certifications']:
                        CTSJson=self.JCTSData[Coil][self.Header['TestcaseID']]['common']['CTSChecks']
                        for key in common_keys:
                            CTSJson.pop(key, None)
                        CertMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)
                        AllMeasures.update(CertMeasures)
                             
            else: print("Testcase not defined in json")
            return(AllMeasures)
        except Exception as e:
            traceback.print_exc()


    def GetNotals(self):
        Notals=[]
        Certification= self.Certification if self.Product=='MPP' and self.mode== 'TPR' else str('V_'+self.Certification) 
        for Notal,value in self.BKjsonData["testBkpProjectConfiguration"]["TesterConfigurationModel"]["notal"].items():
            if value['isActive']:
                if Certification in value['appModeDescription']:
                    Notals.append(Notal)
        return Notals



    #-apply all timing checks for the received pacekts with all details
    def TimingChecksGeneral(self,flwID,FlowLimit):
        # print(self.timing_map[flwID])
        try:
            AllTimings={}
            cnt = 1
            EPP=False
            for timeChk in self.JTimeData[self.Product][self.mode]:

                if self.TestID in self.JTimeData[self.Product][self.mode][timeChk]['skip']:continue
                # print(timeChk)
                timeChkSetup = self.JTimeData[self.Product][self.mode][timeChk]
                timeChkList = []
                # print(self.JTimeData[self.Product][self.mode][timeChk][self.TestID])
                tol = self.JTimeData[self.Product][self.mode][timeChk]['default'] if self.TestID not in self.JTimeData[self.Product][self.mode][timeChk] else self.JTimeData[self.Product][self.mode][timeChk][self.TestID] 
                #Update Tolerence specif to Prodct / mode
                if timeChk in ['tintervalCE-CE_PT','tintervalCE-CE_CL'] and EPP and not self.Product=="C3" and not self.mode=="TPR": tol=[0,700]
                if timeChk in ['treceviedRP8-RP8'] and self.Product=="C3" and self.mode=="TPR":
                    if self.Header['Coil']=="TPR#5":tol=[3900,5]
                    elif  self.Header['Coil']=="TPR#6":tol=[2000,5]
                # print(tol)
                AllTimings[f'{timeChk}_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1]) if tol[0]!=0 else str(tol[0])+'-'+str(tol[1])
                AllTimings[f'{timeChk}_res']='NA'
                AllTimings[timeChk]='NA'
                # AllTimings[f'{timeChk}_allres']='NA'
                AllTimings[f'{timeChk}_remark']='NA'
                AllTimings[f'{timeChk}_SEQ'] = cnt
                AllTimings[f'{timeChk}_Details'] = []
                #Checks timing btw any two packets______________________________________________________________________________________________________________________________
                # if timeChk in ['twake',"tintervalCNF-XCE",'tintervalCFG-CE',"tintervalSRQ/EN-CE"]:
                # if timeChk in ['twake',"tintervalSRQ/EN-CE"]:
                valid_list = (['twake', 'tintervalSRQ/EN-CE']if self.Product == 'MPP' else ['twake', 'tintervalCNF-XCE', 'tintervalCFG-CE', 'tintervalSRQ/EN-CE'])
                if timeChk in valid_list:
                    StartPhase=timeChkSetup['PhasePkts']['Start']['Phase']
                    EndPhase=timeChkSetup['PhasePkts']['End']['Phase']
                    StartPacket=timeChkSetup['PhasePkts']['Start']['Packet']
                    EndPacket=timeChkSetup['PhasePkts']['End']['Packet']
                    if  timeChk =='tintervalCFG-CE' and StartPhase in self.timing_map[flwID] and StartPacket in self.timing_map[flwID][StartPhase] and len(self.timing_map[flwID][StartPhase][StartPacket][0])==2 and "ACK" in self.timing_map[flwID][StartPhase][StartPacket][0][1]:
                        EPP=True
                        continue
                    if all(res in self.timing_map[flwID] for res in [StartPhase,EndPhase]):
                        if  StartPacket in self.timing_map[flwID][StartPhase] and EndPacket in self.timing_map[flwID][EndPhase]:                          
                            if  len(timeChkSetup['PhasePkts']['Start']['Value'])==0 or timeChkSetup['PhasePkts']['Start']['Value'][0] in self.timing_map[flwID][StartPhase][StartPacket][len(self.timing_map[flwID][StartPhase][StartPacket])-1][0][1] :
                                AllTimings[timeChk] = str(round((self.timing_map[flwID][EndPhase][EndPacket][0][0][2] - self.timing_map[flwID][StartPhase][StartPacket][0 if timeChk=="tintervalCFG-CE" else len(self.timing_map[flwID][StartPhase][StartPacket])-1][0][2])*1000,2)+timeChkSetup['Preamble'])
                                AllTimings[f'{timeChk}_remark']=f'Measured {timeChk} is {AllTimings[timeChk]} ms, between {StartPacket} @{self.timing_map[flwID][StartPhase][StartPacket][len(self.timing_map[flwID][StartPhase][StartPacket])-1][0][0]} to {EndPacket} @{self.timing_map[flwID][EndPhase][EndPacket][0][0][0]} + {timeChkSetup['Preamble']}.'
                                res= float(AllTimings[timeChk]) >= tol[0]-tol[1]-0.1 and float(AllTimings[timeChk]) <= tol[0]+tol[1]+0.1 if tol[0]!=0 else float(AllTimings[timeChk]) >= tol[0] and float(AllTimings[timeChk]) <= tol[1]+0.1 #0.1 is tolerance
                                AllTimings[f'{timeChk}_Details'].append([f"{AllTimings[f'{timeChk}_remark']} The measured value is {'' if res else 'not'} in limit:{AllTimings[f'{timeChk}_exp']} ms.","Pass" if res else 'Fail'])
                        else:AllTimings[f'{timeChk}_Details'].append([f'All required packets not found to perform the {timeChk}',"Fail"])
                    else:AllTimings[f'{timeChk}_Details'].append([f'All required packets not found to perform the {timeChk}',"Fail"])
                #check for timings btw all packets for mentioned phases_____________________________________________________________________________________________________
               
                elif timeChk in ["tstart","tsilent"]:

                    Limits=str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
                    if timeChk=='tsilent' and self.mode=='TPT': Limits= f'GTE {tol[1]}'
                   
                    id=FlowLimit[0]
                    Pktslist =[]
                    while id < FlowLimit[1]:
                        if not self.file_list[id]['isFWTestermessage']:
                            if self.file_list[id]['description'] not in ['Ping','ID&CFG'] or self.PktMethod.GetPacketType(id)=="Response":break
                            if self.file_list[id]['description'] in ['Ping','ID&CFG']:
                                Pktslist.append([id, self.file_list[id]['value'], self.file_list[id]['startTime'], self.file_list[id]['stopTime']])
                        id+=1
                    
                    if len(Pktslist)>0:
                        id = 0
                        while id < len(Pktslist)-1:
                            res = round((Pktslist[id+1][2]-Pktslist[id][3])*1000,1)+float(timeChkSetup['Preamble'])
                            timeChkList.append(res)
                            if (res < tol[0]-tol[1] or res >tol[0]+tol[1]) if tol[0]!=0 else res < tol[1] if self.mode=='TPT'and timeChk=='tsilent'else res > tol[1]:
                                AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is not in limit: {Limits}ms.","Fail"])
                            else:
                                AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is in limit: {Limits}ms.","Pass"])
                            id+=1
                        AllTimings[timeChk]=';'.join(map(str,timeChkList))

                #check timings btw packet and which has response_____________________________________________________________________________________________________
                elif timeChk in ["tresponse","tresponseAuth","tresponseCNF"]:
                    # print(timeChk)
                    if self.TestID not in ["MPP_PTX_POW_LEGACY_PRX_P1","MPP_PTX_POW_LEGACY_PRX_P2"]:
                        for phase in self.timing_map[flwID]:
                            if phase not in ['General','Loads']:
                                for pkts in self.timing_map[flwID][phase]:
                                    # print(pkts)
                                    stus = False
                                    if timeChk in ["tresponse"]:
                                        if pkts not in timeChkSetup['PhasePkts']['Packet_Exp']:stus=True
                                    elif timeChk in ["tresponseAuth","tresponseCNF"]:
                                        if pkts in timeChkSetup['PhasePkts']['Packet']:stus=True
                                    if stus == True:
                                        pk = self.timing_map[flwID][phase][pkts]
                                        if type(pk) == list:
                                            for pks in pk:
                                                if type(pks) == list:
                                                    if len(pks)>1:
                                                        # print("pks:",pks)
                                                        res = round((pks[1][2] - pks[0][3])*1000,1)
                                                        timeChkList.append(res)
                                                        if (res < tol[0]-tol[1] or res >tol[0]+tol[1]) if tol[0]!=0 else res > tol[1]:
                                                            AllTimings[f'{timeChk}_Details'].append([f"Measured tresponse {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{pks[1][0]}","Fail"])
                                                        else:
                                                            AllTimings[f'{timeChk}_Details'].append([f"Measured tresponse {res} in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{pks[1][0]}","Pass"])
                    AllTimings[timeChk]=';'.join(map(str,timeChkList)) if len(timeChkList)>0  else 'NA'
                    AllTimings[f'{timeChk}_exp'] = str(round(tol[0]-tol[1],2))+'-'+str(round(tol[0]+tol[1],2)) if tol[0]!=0 else str(tol[0])+'-'+str(tol[1])
                    #Keep only failures in sunchecks to save space
                elif timeChk in ["tintervalXCE-XCE","tintervalCE-CE_PT","tintervalCE-CE_CL","treceviedPLA-PLA","treceviedRPM1-RPM1","treceviedRPM2-RPM2","treceviedRPM0-RPM0","treceviedRP8-RP8"]:
                    # print(timeChk)
                    Pktslist =[]
                    for phase in self.timing_map[flwID]:
                        if phase in timeChkSetup['PhasePkts']['Phase']:
                            for pkts in self.timing_map[flwID][phase]:
                                # if any(res in pkts for res in timeChkSetup['PhasePkts']['Packet']):
                                if any(res == pkts for res in timeChkSetup['PhasePkts']['Packet']):
                                    # print(pkts,timeChkSetup['PhasePkts']['Packet'])
                                    for Pkt in self.timing_map[flwID][phase][pkts]:
                                        if len(timeChkSetup['PhasePkts']['Value'])>0:
                                            # print("Pkt[0][1]:",Pkt[0][1])
                                            if any(res in Pkt[0][1] for res in timeChkSetup['PhasePkts']['Value']):
                                                # print(timeChkSetup['PhasePkts']['Value'])
                                                Pktslist.append(Pkt[0])
                                        else:Pktslist.append(Pkt[0])
                    # print("Pktslist:",Pktslist)      
                    if len(Pktslist)>0:
                        id = 0
                        # end = len(Pktslist)-1
                        if self.TestID in ["MPP_PTX_POW_OVP_FAST_RECOVERY_TC_1","MPP_PTX_POW_OVP_FAST_RECOVERY_TC_2"]:
                            end = self.PktMethod.GetPacketDetails(packet=f"Set_Load 400mA",limit=[0,len(self.file_list)-1],Type="TesterMsg")[2]
                        else: end = Pktslist[-1][0] #len(Pktslist)-1



                        while id < len(Pktslist)-1:
                            
                            if Pktslist[id][0] <= end:
                                checkValid = True
                                #for CE packet intervel ignore if any other packets available inbetween
                                if timeChk in ["tintervalXCE-XCE","tintervalCE-CE_PT","tintervalCE-CE_CL"]:
                                    tid = (Pktslist[id][0])+1
                                    while tid < Pktslist[id+1][0]:
                                        if self.PktMethod.GetPacketType(tid) == "Packet":
                                            checkValid=False
                                            break
                                        tid+=1
                                if checkValid == True:
                                    res = round((Pktslist[id+1][2]-Pktslist[id][2])*1000,2)+float(timeChkSetup['Preamble'])
                                    timeChkList.append(res)
                                    if (res < tol[0]-tol[1] or res >tol[0]+tol[1]) if tol[0]!=0 else res > tol[1]:
                                        # FalsetimeChk.append('Fail')
                                        AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is not in limit: {AllTimings[f'{timeChk}_exp']} ms.","Fail"])
                                    else:
                                        # FalsetimeChk.append('Pass')
                                        AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is in limit: {AllTimings[f'{timeChk}_exp']} ms.","Pass"])
                                id+=1
                            else: break

                        # print(timeChk,'FalsetimeChk',FalsetimeChk)
                        # AllTimings[f'{timeChk}_res'] ='NA'
                        # if len(FalsetimeChk)>0:
                            # AllTimings[f'{timeChk}_res'] ='Fail' if 'Fail' in FalsetimeChk  else 'Pass'
                        AllTimings[timeChk]=';'.join(map(str,timeChkList))
                        # AllTimings[f'{timeChk}_remark'] = ';'.join(remarks)
                        # AllTimings[f'{timeChk}_allres'] = ';'.join(FalsetimeChk)
                # #Add the final results
                if len(AllTimings[f'{timeChk}_Details'])>0:
                    AllTimings[f'{timeChk}_res']='Fail' if 'Fail' in [item[1] for item in AllTimings[f'{timeChk}_Details']] else 'Pass'
                    #compress subchecks to keep only pass
                    if timeChk in ['tresponse',"tresponseAuth","treceviedPLA-PLA",'tintervalXCE-XCE','tintervalCE-CE',"tintervalCE-CE_CL","tintervalCE-CE_PT","treceviedRPM1-RPM1","treceviedRPM2-RPM2","treceviedRPM0-RPM0","treceviedRP8-RP8"]:
                        subck = []
                        for chk in AllTimings[f'{timeChk}_Details']:
                            if chk[1] == "Fail":subck.append(chk)
                        AllTimings[f'{timeChk}_Details']=subck if len(subck)>0 else [[f"All the measured {timeChk} are within the Limit: {AllTimings[f'{timeChk}_exp']} mS","Pass"]]
                    cnt+=1
        except Exception as e:
            traceback.print_exc()
        # print(AllTimings)
        return AllTimings

    #- General Checks
    def GeneralCheck(self,flwID):
        try:
            GeneralCheck={}
            seqcnt = 1
            for GenCheck in self.JGenCheckData[self.Product][self.mode]:
                if self.Header['TestcaseName'] not in self.JGenCheckData[self.Product][self.mode][GenCheck]['ExemeptedTC']:
                    if flwID in self.JGenCheckData[self.Product][self.mode][GenCheck]['Default']['flow']:
                        exp = self.JGenCheckData[self.Product][self.mode][GenCheck]['Default']['expected']
                        Flow_limit = self.flows[flwID]['Limit']
                        if GenCheck in ['F1-Fq','F2-Fq']:
                            GeneralCheck[f'{GenCheck}_exp'] = str(exp[0])+'-'+str(exp[1])+' kHz'
                            GeneralCheck[f'{GenCheck}_res'] ='NA'
                            GeneralCheck[f'{GenCheck}_SEQ'] =seqcnt
                            GeneralCheck[GenCheck]="NA"
                            GeneralCheck[f'{GenCheck}_Details'] = []
                            if 'FOP' in self.timing_map[flwID]['General']:
                                res = GeneralMethods.GetFloatFromStr(self.timing_map[flwID]['General']['FOP'][1])
                                GeneralCheck[GenCheck] = res[0]
                                if GeneralCheck[GenCheck] >= exp[0] and GeneralCheck[GenCheck] <= exp[1]:
                                    GeneralCheck[f'{GenCheck}_Details'].append([f"The measured FOP is {GeneralCheck[GenCheck]} kHz at {round(self.timing_map[flwID]['General']['FOP'][2],3)}sec, Limit: [{exp[0]} - {exp[1]}] kHz","Pass"])
                                else:GeneralCheck[f'{GenCheck}_Details'].append([f"The measured FOP is {GeneralCheck[GenCheck]} kHz at {round(self.timing_map[flwID]['General']['FOP'][2],3)}sec, Limit: [{exp[0]} - {exp[1]}] kHz","Fail"])
                            else:GeneralCheck[f'{GenCheck}_Details'].append([f"FOP packet not found","Fail"])
                        elif GenCheck in ['ReserveBitChek']:
                            res =[]
                            val = []
                            id = Flow_limit[0]
                            while id < Flow_limit[1]:
                                if self.file_list[id].get('isTesterPkt') == False and self.file_list[id].get('isFWTestermessage')==False:
                                    #find and check all reserve bits
                                    for d1 in self.file_list[id]['header_Payload']['childelement']:
                                        for d2 in d1['childelement']:
                                            if 'Reserved' in d2['sDecodedValue']:
                                                val.append(d2['sRawData'])
                                                if d2['sRawData'] != exp:
                                                    res.append([str(self.file_list[id]['pktType'])+'@index='+str(id)+':'+str(d2['sDecodedValue'])+str(d2['sRawData']),"Fail"])
                                                else:res.append([str(self.file_list[id]['pktType'])+'@index='+str(id)+':'+str(d2['sDecodedValue'])+str(d2['sRawData']),"Pass"])
                                id+=1
                            GeneralCheck[f'{GenCheck}_SEQ'] =seqcnt
                            GeneralCheck['ReserveBitChek']=','.join(val) #if len(val)>0 else 'No Mismatch'
                            GeneralCheck['ReserveBitChek_exp']='Reserved='+str(exp)
                            GeneralCheck['ReserveBitChek_Details'] = res
                            # GeneralCheck['ReserveBitChek_res']='Pass' if len(res)==0 else 'Fail'
                            # GeneralCheck['ReserveBitChek_remark']=','.join(res)
                        elif GenCheck in ['TestIssues']:
                            GeneralCheck[f'{GenCheck}'] = "Testcase issues"
                            GeneralCheck[f'{GenCheck}_exp'] = "Testcase issues"
                            GeneralCheck[f'{GenCheck}_SEQ'] = seqcnt
                            if len(self.TCRemarks)>0:
                                GeneralCheck[f'{GenCheck}_Details'] = self.TCRemarks
                            else:GeneralCheck[f'{GenCheck}_Details']=[["The received packet sequence was proper","Pass"]]
                        #Add the final results
                        if len(GeneralCheck[f'{GenCheck}_Details'])>0:
                            GeneralCheck[f'{GenCheck}_res']='Fail' if 'Fail' in [item[1] for item in GeneralCheck[f'{GenCheck}_Details']] else 'Pass'
                            #compress subchecks to keep only pass
                            if GenCheck in ['ReserveBitChek']:
                                subck = []
                                for chk in GeneralCheck[f'{GenCheck}_Details']:
                                    if chk[1] == "Fail":subck.append(chk)
                                GeneralCheck[f'{GenCheck}_Details']=subck if len(subck)>0 else [["All the received Reserved bit values are proper","Pass"]]
                            seqcnt+=1
            # print(GeneralCheck)
            return GeneralCheck
        except Exception as e:
            traceback.print_exc()
 
    #- PayLoad Checks
    def PayLoadCheck(self,flwID):
        try:
            
            if self.Header['UID'] not in self.GeneralChecks:self.GeneralChecks[self.Header['UID']]={}
            if self.Header['TestcaseName'] not in self.GeneralChecks[self.Header['UID']]:self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']]={}
            if flwID not in self.GeneralChecks:self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID]={}
            FlowLimit = self.flows[flwID]['Limit']
            id = FlowLimit[0]
            while id < FlowLimit[1]:
                Type=self.PktMethod.GetPacketType(id)
                if Type in ['Packet', 'Response']:
                    phase = 'General' if self.file_list[id]['description']=='' else self.file_list[id]['description']
                    if phase not in self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID]:self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase]={}
                    # print(phase)
                    packet =  self.file_list[id]['pktType']
                    if packet in["Get Request","General Request","DSR"]:packet+=" "+self.file_list[id]['value'].replace('{','').replace('}','')
                    elif packet in ["SRQ [0x20] "]:packet="Specific Request"+" "+self.file_list[id]['value'].replace('{','').replace('}','').split(':')[0]
                    elif packet in ["FOD Status"]: packet+=" "+self.file_list[id]['value'].replace('{','').replace('}','').split(':')[0]
                    elif packet in['SADC','ADC']:packet+=" "+self.file_list[id]['value'].replace('{','').replace('}','').split(':')[0]
                    # print(f'{packet} @{Type}')
                    try:
                        
                        #     print("packet:",packet)
                        if f'{packet} @{Type}' not in self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase]:
                            self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']={}
                            if 'PayLoadCheck' not  in self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']:
                                self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']['PayLoadCheck']=[]
                                try:
                                    if len(self.JPayLoadCheckData[self.Product][self.mode][str(flwID)][phase][f'{packet} @{Type}']['PayLoadCheck']) > 0:
                                        for PacketDetails in self.JPayLoadCheckData[self.Product][self.mode][str(flwID)][phase][f'{packet} @{Type}']['PayLoadCheck']:
                                            # print("Name:",PacketDetails['Name'])
                                            expected = PacketDetails.get("Exp", []) 
                                            comp=PacketDetails.get("comp", "EQL")
                                            CompType=PacketDetails.get("Type", "DEC")
                                            count=0
                                            while count < len(PacketDetails['ExemeptedTC']):
                                                if self.Header['TestcaseID'] in PacketDetails['ExemeptedTC'][count]['TestCase']:
                                                    expected=PacketDetails['ExemeptedTC'][count].get('Exp',[])
                                                    comp=PacketDetails['ExemeptedTC'][count].get("comp", "EQL")
                                                    CompType=PacketDetails['ExemeptedTC'][count].get("Type", "DEC")
                                                    break
                                                count+=1

                                            for payload in self.PktMethod.GetGeneralPayloadDetails(name=PacketDetails.get("Name"),index=id,Byte=PacketDetails.get("Byte"),Bit=PacketDetails.get("Bit")):
                                                # print("payload:",payload)
                                                # print("sDecodedValue:",payload.get('sDecodedValue'))
                                                raw_data = payload.get('sRawData')
                                                # print("sDecodedValue:",payload.get('sDecodedValue'), payload.get('sDecodedValue') in ["g_coil_TX","Alpha_FM","Alpha_FM_DC"])

                                                if payload.get('sDecodedValue') in ["g_coil_TX","g_coil_T","g_coil_R","g_coil_RX","Alpha_FM","Alpha_FM_DC"]:
                                                    # print("Entered:",payload.get('sDescription'))
                                                    raw_data = payload.get('sDescription').split("(")[1].split(")")[0]
                                                    # print("raw_data:",raw_data)

                                                if raw_data:
                                                    result, actual_val = self.PktMethod.compare_hex_to_expected(raw_data, expected, comp,CompType)
                                                    status = "PASS" if result else "FAIL" 
                                                    Expected= ''
                                                    if  comp in ["BTW"] : Expected=f'Range of {str(expected).replace('{','(').replace('}',')')}'
                                                    elif comp in ['IN']: Expected =f'Must be only either {str(expected).replace('{','(').replace('}',')')}'
                                                    elif comp in ['ANY']: Expected =f'Should be any value'
                                                    else:Expected=actual_val
                                                    # Expected=f'Should be in {expected}' if status=='FAIL' or PacketDetails.get("comp", "EQL") in ["BTW","IN","ANY"] else actual_val
                                                    self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']['PayLoadCheck'].append({'CheckName': PacketDetails.get("Name"), 'Byte': PacketDetails.get("Byte"),'Bit': PacketDetails.get("Bit"),'Expected': {Expected},'Received': actual_val,'Result': status })
                                                    self.SQLConn.ExecutebyQuery("INSERT INTO PayLoadDetails (UID, SEQID, Type, Phase, PacketID, Packet, HeaderName, CheckName, Byte, Bit, ExpValue, RecValue, ChecksResult, HeaderResult) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (self.Header['UID'], flwID, 'PayLoad', phase, id, f"{packet} @{Type}", None, PacketDetails.get('Name'), PacketDetails.get('Byte'), PacketDetails.get('Bit'), str(Expected), actual_val, status, None))
                                    else: self.SQLConn.ExecutebyQuery( "INSERT INTO PayLoadDetails (UID, SEQID, Type, Phase, PacketID, Packet, HeaderName, CheckName, Byte, Bit, ExpValue, RecValue, ChecksResult, HeaderResult) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (self.Header['UID'], flwID, 'PayLoad', phase, id, f"{packet} @{Type}", None, '--', '--', '--', '--', '--', '--', None))
                                except Exception as e: e
                                    # print("PayLoadCheck",e)
                                
                            if 'HeaderCheck' not in self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']:
                                self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']['HeaderCheck']=[]
                                try:
                                    headers = self.file_list[id].get('header_Payload', {})
                                    ReceivedHeader=headers.get('sFieldType', None)
                                    if ReceivedHeader is not None:
                                        HeaderName=self.JPayLoadCheckData[self.Product][self.mode][str(flwID)][phase][f'{packet} @{Type}']['HeaderCheck'][0]['HeaderName']
                                        
                                        if f'{packet} @{Type}' in ["ACK @Response" ,"ATN @Response","NAK @Response","ND @Response", "MPP ACK @Response","MPP:ACK @Response"] and self.Product=='MPP' and self.mode =='TPT':
                                            ReceivedHeader=ReceivedHeader.split(':')[1].split()[-1]
                                        else:ReceivedHeader=ReceivedHeader.split(':')[1].split()[0]
                                        if HeaderName==ReceivedHeader: status = "PASS" 
                                        else: status="FAIL"
                                        self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']['HeaderCheck'].append({'HeaderName': HeaderName,'Result': status })
                                    if  self.GeneralChecks[self.Header['UID']][self.Header['TestcaseName']][flwID][phase][f'{packet} @{Type}']['HeaderCheck'][0]['Result']=='PASS':
                                        self.SQLConn.ExecutebyQuery("UPDATE PayLoadDetails SET HeaderResult = ?, HeaderName = ? ""WHERE UID = ? AND SEQID = ? AND Type = 'PayLoad' AND Phase = ? " "AND PacketID = ? AND Packet = ?", ('PASS', HeaderName, self.Header['UID'], flwID, phase, id, f"{packet} @{Type}"))
                                    else: self.SQLConn.ExecutebyQuery( "UPDATE PayLoadDetails SET HeaderResult = ?, HeaderName = ? " " WHERE UID = ? AND SEQID = ? AND Type = 'PayLoad' AND Phase = ? " "AND PacketID = ? AND Packet = ?",('FAIL', HeaderName, self.Header['UID'], flwID, phase, id, f"{packet} @{Type}"))
                                except Exception as e:e
                                    # print("PayLoadCheck",e)         
                    except Exception as e:e
                        # print("PayLoadCheck",e)       
                id+=1
            return True
        except Exception as e:
            traceback.print_exc()

    #- Push Results to JSON
    def UpdateToJsonReport(self):
        self.FinalRepData.append({'Header':self.Header,'SeqResults':self.timing_map})
        #Sorting TBD -- Not req
        self.FinalRep.update_file(self.FinalRepData)
        

###Support Functions ####################################################################################################################
    #-Get Run time of the testcase, returns start time and end in nanoseconds,
    def GetRunTime(self):
        TcStartAPI = APIOperations(url=self.JapiData[self.Product][self.mode]['GetWaveformStartTime'],retype='json')
        TCstartTime = TcStartAPI.GetRequest()
        TcStopAPI = APIOperations(url=self.JapiData[self.Product][self.mode]['GetWaveformStopTime'],retype='json')
        TCstopTime = TcStopAPI.GetRequest()
        return[TCstartTime,TCstopTime/100000000]
    #-Create log releated to a testcase validation steps. update same into debug logfile
    def update_TClogs(self,logtype,log):
        # print(log)
        dt_object = datetime.fromtimestamp(datetime.now().timestamp())
        self.TClogs.append([str(dt_object),logtype,log])
 
    #- Get software side high level results
    def GetJSONTCData(self,TestID,BackupJson,retunData):
        try:
            BKjson = JsonOperations(BackupJson)
            BKjsonData = BKjson.read_file()
            for TCdata in BKjsonData['testBkpTestResultsandPath']:
                if TCdata is not None:
                    if TCdata['testcaseDetails']['m_TestId'] == TestID:
                        if retunData == "TCresult":
                            return TCdata['testinformation']['TestResult']
                        elif retunData == "TCcoil":
                            return TCdata['testinformation']['TesterConfiguration']['CoilUsed']
            return 'NA'
        except Exception as e:
            print("GetJSONTCData error:",e)
    #- Run time of the testcase 
    def UpdateTestRunTimings(self,TCname,JSONvalues):
        try:
            for TCdata in JSONvalues['TestingScope']:
                if TCdata is not None:
                    if TCdata['TestName'] == TCname:
                        self.Header['TestedTime_start']= TCdata['TestStartTime']
                        self.Header['TestedTime_end']= TCdata['TestEndTime']
                        stime = [int(num) for num in self.Header['TestedTime_start'].split('T')[1].split('+')[0].replace('.',':').split(':')]
                        etime = [int(num) for num in self.Header['TestedTime_end'].split('T')[1].split('+')[0].replace('.',':').split(':')]
                        st = (((stime[0]*1000)*60)*60)+((stime[1]*1000)*60)+(stime[2]*1000)+stime[3]
                        et = (((etime[0]*1000)*60)*60)+((etime[1]*1000)*60)+(etime[2]*1000)+etime[3]
                        self.Header['TestedTime'] =abs(st-et)
                        break
        except Exception as e:
            traceback.print_exc()
    #- General method to retun values from backupjson file for a testcase.
    def GetTCValuesfromBackUpJSON(self,KeyToFind="_testID"):
        BKjson = JsonOperations(self.BackupJson)
        self.BKjsonData = BKjson.read_file()
        for TCdata in self.BKjsonData['testBkpTestResultsandPath']:
            if TCdata['testcaseDetails']['m_DisplayName'] == self.TestCaseName:
                res = self.GetValuefromKey(TCdata,KeyToFind)
                return res
    #Get value from matching key of dict
    def GetValuefromKey(self,TCdata,KeyToFind):
        for key, value in TCdata.items():
            if key == KeyToFind:
                return value
            elif isinstance(value, dict):
                # Recursively search in nested dictionaries
                result = self.GetValuefromKey(value, KeyToFind)
                if result is not None:
                    return result
        return None  
    #- Idetify flow for MPP
    def Findflow(self,limit):
        id = limit[0]
        index = 1
        while id<limit[1]:
            if 'Identification' in self.file_list[id].get('pktType'):
                index=1
            if 'Specific Request' in self.file_list[id].get('pktType') and 'Frequency Selection: 360 Khz' in self.file_list[id].get('value'):
                index = 1
                break
            if self.EPRC_pkt in self.file_list[id].get('pktType'):
                index = 2
                break
            elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' in self.file_list[id].get('value'):
                index = 1
                break
            elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' not in self.file_list[id].get('value'):
                index = 2
                break
            elif 'FOP:' in  self.file_list[id].get('value'):
                if float(self.file_list[id].get('value').split(':')[1].split(' ')[0]) >300:
                    index =2
                    break
                else:
                    index=1
                    break
            elif '128' in self.file_list[id].get('value'):
                index = 1
                break
            elif '360' in self.file_list[id].get('value'):
                index = 2
                break
            id+=1
        return index
    #- Find the Testcase index in group TC mode
    def GetTCindexfromGroupRun(self):
        
        JBkup = JsonOperations(self.BackupJson)
        JBkupData =JBkup.read_file()
        # For the Loaded Trace File, get the TcId's  through API 
        SWResult = APIOperations(url=self.JapiData[self.Product][self.mode]['GetWaveFormTestResult'],retype='json')
        SwResultJson = SWResult.GetRequest()
        mTestId=[]
        for data in SwResultJson[0].get("children",[]):
            for child in data['children']:
                for sub in child['children']:
                    if "Couldn't capture test start assertion message" not in sub['displayString']:
                        mTestId.append(sub['testParentId'])  
                    break       
        if len(self.SubTClist)==len(mTestId): return mTestId.index(self.TestID)   
        return 0

    


# obj = TestValidation(TestID="MPP_PRX_FOD_BEFOREPOWER_DEVICEDET_Q_DEF_P1",TestCaseName="9.1 MPP.PTX.POW.GUARANTEED_POWER.P1",
# ProjectJson=r"D:\C3 TPT Reports\MPP TPT\GXL_231_023_V231_300426_144431\V231_GRL_C3_FinalReport.json",
# BackupJson = r"D:\C3 TPT Reports\MPP TPT\GXL_231_023_V231_300426_144431\V231_Final_TestBackup.gproj",
# TracePath=r"C:\Users\GRL\Downloads\Apple_1_V22_240425_132541\Run4\9_1_P4\9_1_P4.grltrace")