from Models.TestConfigs import ProjectConfiguration
import sys
sys.path.append('Scripts')
import importlib
import traceback
import uuid
# import zipfile
from MainModule import JsonOperations,APIOperations,GeneralMethods
from Models.Enums import Enums
from Models.TestConfigs import *
from Models.JsonConfig import JsonConfig
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from datetime import datetime,date
import traceback
#offline validation , packet
class TestValidation():
    
    def __init__(self):

        """
           Store the TestCaseConfig reference object in Test Variable
           Use Global JsonConfig class to acess json data
           Update File_list data to TestCaseConfig class to access to gloabally through out the Project

        """
        # TODO : Implement Enums for Packets 
        self.Test=TestObjects.TestCaseConfig
        self.stability=None
        if ProjectConfiguration.Certification in ["2.0.1","2.1.0","2.2.1","2.3.0"]:
            self.EPRC_pkt = "Extended_Power_Receiver_Capabilities"
        else:
            self.EPRC_pkt = "Extended Power Receiver Capabilities"

        #Global Vars
        self.JCTSData = JsonConfig.read_file(JsonConfig.CTS_PATH)
        self.Header = {}
        #_start validation___________________________________________________________________
        self.TCRemarks = []
        self.update_TClogs("General",f"Validation started for : {self.Test.TestcaseID}")
        self.UpdateHeaderInfo()
        #Get Packets___________________________________________________________________________
        self.PktAPI = APIOperations(url=JsonConfig.JapiData[GeneralConfig.Product][GeneralConfig.Mode]['GetCCLinePackets'],retype='json')
        self.file_list = self.PktAPI.GetRequest()
        self.Test.file_list=self.file_list
        #Define the offline validation module 
        self.PktMethod = PacketMethods()
        self.PlotMethod = PlotMethods()
        TestObjects.PktMethod = self.PktMethod
        TestObjects.PlotMethod = self.PlotMethod

        # print(self.Header)
        self.Test.Flows = self.SegricatePackets()
        # If the Test Contains TWO Trace files then add the TC in List and store the final Limts in Json
        if self.Test.TestcaseID in ["CMAG001_01_Magnetic_Cover_Presence_Check"]:  
            self.TestResultsjson = JsonOperations("json/TestResults.json")
            self.TestData = self.TestResultsjson.read_file()
            if self.Test.TestcaseID in self.TestData['FileList_Data'].keys():
                temp=self.file_list
                self.file_list = self.TestData['FileList_Data'][self.Test.TestcaseID]['Json']
                self.PktMethod.file_list=self.file_list
                self.TestData['FileList_Data'][self.Test.TestcaseID]['flows']=self.SegricatePackets()
                self.TestResultsjson.update_file(self.TestData)
                self.file_list =self.PktMethod.file_list= temp
               
        self.stability = self.Test.Flows
        # print(self.Test.Flows)
        self.GetAllPackets()   
        self.Header['TCresult']=self.Test.AutomationResult 
        self.UpdateToJsonReport() 


        # print(Test.timing_map)
        # print(self.TimingChecksGeneral())
        # print(self.Header)
### Main Functions #######################################################################################################################
    #To Fetch headers of Testcase from various sources.
    def UpdateHeaderInfo(self):
        try:
            now = datetime.now()
            timestamp = now.strftime("%d%m%Y_%H%M%S")
            self.Test.UID = str(uuid.uuid1())
            self.Test.ChapterName = self.GetTCValuesfromBackUpJSON("_chapter")
            self.Test.Coil = self.GetJSONTCData(self.Test.TestcaseID, ProjectConfiguration.BackupJson, "TCcoil")
            ProjectConfiguration.Transmitter = JsonConfig.JQIData[GeneralConfig.Product][GeneralConfig.Mode]['transmitterType']
            ProjectConfiguration.potentialPower = JsonConfig.JQIData[GeneralConfig.Product][GeneralConfig.Mode]['potentialPower']

            if 'TestToolInfo' in ProjectConfiguration.PRjsonData:
                ProjectConfiguration.SWVersion = ProjectConfiguration.PRjsonData['TestToolInfo']['SoftwareVersion']
                ProjectConfiguration.FWVersion = ProjectConfiguration.PRjsonData['TestToolInfo']['FirmwareVersion']
                ProjectConfiguration.HWVersion = ProjectConfiguration.PRjsonData['TestToolInfo']['HardwareVersion']
                ProjectConfiguration.BoardNo = ProjectConfiguration.PRjsonData['TestToolInfo']['SerialNumber']
            elif 'TestPlatformInfo' in ProjectConfiguration.PRjsonData:
                ProjectConfiguration.SWVersion = ProjectConfiguration.PRjsonData['TestPlatformInfo']['SoftwareVersion']
                ProjectConfiguration.FWVersion = ProjectConfiguration.PRjsonData['TestPlatformInfo']['FirmwareVersion']
                ProjectConfiguration.HWVersion = ProjectConfiguration.PRjsonData['TestPlatformInfo']['HardwareVersion']
                ProjectConfiguration.BoardNo = ProjectConfiguration.PRjsonData['TestPlatformInfo']['SerialNumber']

            ProjectConfiguration.BoardModel = f"{GeneralConfig.Product}_{GeneralConfig.Mode}"
            ProjectConfiguration.QiID = ProjectConfiguration.PRjsonData['DutInfo']['QiId']
            ProjectConfiguration.Certification = ProjectConfiguration.PRjsonData['TestExecutionDetails']['SpecVersion']
            
            pathlist = self.Test.TracePath.split("\\")
            ProjectConfiguration.ProjectName = pathlist[len(pathlist)-4]
            ProjectConfiguration.Run = pathlist[len(pathlist)-3]

            """ Update Software TestTimings of a Particular Testcase """
            self.UpdateTestRunTimings(self.Test.TestcaseID, ProjectConfiguration.PRjsonData)

            GeneralConfig.DUTName = ProjectConfiguration.PRjsonData['DutInfo']['BrandName']
            GeneralConfig.DUTID = ProjectConfiguration.PRjsonData['DutInfo']['ProductName']
            GeneralConfig.DUTSL = ProjectConfiguration.PRjsonData.get('TestToolInfo', {}).get('SerialNumber', '') or ProjectConfiguration.PRjsonData.get('TestPlatformInfo', {}).get('SerialNumber', '')
            
            ProjectConfiguration.testLab = ProjectConfiguration.PRjsonData['TestLab']['LabName']
            ProjectConfiguration.testEngineer = ProjectConfiguration.PRjsonData['TestLab']['TestEngineer']
            JsonConfig.JQIData[GeneralConfig.Product][GeneralConfig.Mode]['testLab'] = ProjectConfiguration.testLab
            JsonConfig.JQIData[GeneralConfig.Product][GeneralConfig.Mode]['testEngineer'] = ProjectConfiguration.testEngineer
            
            self.Test.SoftwareResult = self.GetJSONTCData(self.Test.TestcaseID, ProjectConfiguration.BackupJson, "TCresult")

            # Update HeaderInfo to Results
            self.Header['UID'] = self.Test.UID
            self.Header['TestcaseID'] = self.Test.TestcaseID
            self.Header['TestcaseName']= self.Test.TestcaseName
            self.Header['ChapterName']=self.Test.ChapterName
            self.Header['Transmitter']=ProjectConfiguration.Transmitter
            self.Header['potentialPower']=ProjectConfiguration.potentialPower
            self.Header['Coil'] = self.Test.Coil
            self.Header['SWVersion'] = ProjectConfiguration.SWVersion
            self.Header['FWVersion'] = ProjectConfiguration.FWVersion
            self.Header['HWVersion'] = ProjectConfiguration.HWVersion
            self.Header['BoardNo'] = ProjectConfiguration.BoardNo
            self.Header['QiID'] = ProjectConfiguration.QiID
            self.Header['BoardModel'] = ProjectConfiguration.BoardModel
            self.Header['Certification'] = ProjectConfiguration.Certification
            self.Header['CapturePath'] = self.Test.TracePath
            self.Header['ProjectName'] = ProjectConfiguration.ProjectName
            self.Header['Run'] = ProjectConfiguration.Run
            #TBD 
            self.Header['TestedTime_start']=self.Test.STestStartTime
            self.Header['TestedTime_end']=self.Test.STestEndTime
            self.Header['ValidatedTime']=self.Test.SValidatedTime
            self.Header['DUTName']= ProjectConfiguration.DUTName
            self.Header['DUTID']= ProjectConfiguration.DUTID
            self.Header['DUTSL']= ProjectConfiguration.DUTSL
            self.Header['TestLab']=ProjectConfiguration.testLab
            self.Header['Engineer']=ProjectConfiguration.testEngineer
            self.Header['TCresult']=self.Test.AutomationResult
            self.Header['SWresult'] = self.Test.SoftwareResult
            self.Header['Product'] = GeneralConfig.Product
            self.Header['Mode'] = GeneralConfig.Mode
            self.Header['Certification']=ProjectConfiguration.Certification
            
           
           
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
            if self.Test.TestcaseID in ['TEST_PTX_CPX_PNG_S01_TIM_002']:
                return  {1:{"Limit":[0,len(self.file_list)-1],"Flow":1},2:None}
            # if self.Test.TestcaseID in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
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
                if all(rs in self.file_list[sid].get('value') for rs in ['Test_Started']) if GeneralConfig.Mode == Enums.Mode.TPR else  all(rs in self.file_list[sid].get('pktType') for rs in ['Test_Started']):
                    eid = sid+1
                    # print(eid)
                    while eid < TCLimit[1]-1:
                        if all(rs in self.file_list[eid].get('value') for rs in ['Test_Stop']) if GeneralConfig.Mode == Enums.Mode.TPR else all(rs in self.file_list[eid].get('pktType') for rs in ['Test_Stop']): 
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
                            if GeneralConfig.Mode == Enums.Mode.TPR:
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
                                if GeneralConfig.Mode == Enums.Mode.TPR:
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
                                index = self.Findflow([start,end]) if GeneralConfig.Product == Enums.Product.MPP else 1
                                packets[cnt]={"Limit":[start,end],"Flow":index}
                            else: # Eswar 
                                if GeneralConfig.Mode == Enums.Mode.TPR and GeneralConfig.Product == Enums.Product.C3 and (self.Test.ChapterName in ['In_Power_Transfer_Tests'] or self.Test.TestcaseID in ['TEST_PTX_CPX_PNG_S01_TIM_001','TEST_PTX_CPX_PNG_S01_SIG_001']):
                                    if end-start >1:
                                        cnt +=1
                                        packets[cnt]={"Limit":[start,end],"Flow":1}
                        else:
                            #check for ENDpower
                            EP = self.PktMethod.GetPacketDetails(packet='End Power Transfer',limit=[start,end])
                            # print(EP)
                            if len(EP)>2:
                                cnt +=1
                                index = self.Findflow([start,end]) if GeneralConfig.Product == Enums.Product.MPP else 1
                                packets[cnt]={"Limit":[start,end],"Flow":index}
                            else: # Eswar - to handle C3-TPR ping phase
                                if GeneralConfig.Mode == Enums.Mode.TPR and GeneralConfig.Product == Enums.Product.C3  and self.Test.ChapterName in ['Ping_Phase_Tests','Disconnected_Load_Tests']:
                                    if end-start >1:
                                        cnt +=1
                                        packets[cnt]={"Limit":[start,end],"Flow":1}
                                    # if self.Test.TestcaseID in ['TEST_PTX_CPX_PNG_S01_TIM_002']:packets[cnt]={"Limit":[start,end],"Flow":1}
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
                                if GeneralConfig.Mode == Enums.Mode.TPR:
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
                if GeneralConfig.Product == Enums.Product.MPP and GeneralConfig.Mode == Enums.Mode.TPT and self.Test.ChapterName in ['Pre_power_transfer_test']: return {1:None, 2:{'Limit':[0,len(self.file_list)-1],'Flow':2}}
                if GeneralConfig.Product == Enums.Product.MPP and GeneralConfig.Mode == Enums.Mode.TPR:
                    # print("multiflow1:",multiflow1)
                    if multiflow1:
                        flow1 = max(multiflow1, key=lambda x: x['Limit'][1] - x['Limit'][0])
                        # print({1:max(multiflow1, key=lambda x: x['Limit'][1] - x['Limit'][0]),2:flow2})
                        if self.Test.TestcaseID not in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
                            if flow1 is None : self.TCRemarks.append(["128Khz Flow not found for the testcase",Enums.TestResult.FAIL])
                            # print(self.TestCaseName, self.Test.TestcaseID)
                            if self.Test.TestcaseID not in ["MPP_PTX_CPX_NEG_ENTRY_INIT","MPP_PTX_CPX_NEG_ERROR_STATUS_RESET","MPP_PTX_CPX_PNG_DP_LEVEL_ERROR","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC1","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC2","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC3","MPP_PTX_CPX_NEG_ERROR_STATUS_TC2","MPP_PTX_CPX_NEG_ERROR_STATUS_TC1","TSDF002_01_Unique_PTx_Identifier","MPP_PTX_NEG_POW_KEST_SLIDING","MPP_PTX_CPX_NEG_MODECAP_MODEXCAP_TC1","MPP_PTX_CPX_PNG_T_NOPOWER_RESET","MPP_PTX_POW_MAX_GAIN_SWEEP_PROCEDURE","MPP_PTX_POW_Digital_Ping_128kHz_P1","MPP_PTX_POW_Digital_Ping_128kHz_P2","MPP_PTX_POW_Digital_Ping_128kHz_P3","MPP_PTX_POW_Digital_Ping_128kHz_P4","MPP_PTX_CPX_GENCOM_MPP_PRIORITY","MPP_PTX_CPX_NEG_ILL_001","MPP_PTX_CPX_NEG_ILL_002","MPP_PTX_CPX_NEG_ILL_003","MPP_PTX_CPX_NEG_ILL_004","MPP_PTX_CPX_NEG_ILL_005","MPP_PTX_CPX_NEG_ILL_006","MPP_PTX_CPX_NEG_ILL_007","MPP_PTX_CPX_NEG_ILL_008","MPP_PTX_CPX_NEG_ILL_009","MPP_PTX_CPX_NEG_ILL_010","MPP_PTX_CPX_NEG_ILL_011","MPP_PTX_CPX_NEG_ILL_012","MPP_PTX_CPX_NEG_ILL_013","MPP_PTX_CPX_NEG_ILL_014","MPP_PTX_POW_Digital_Ping_360_OV_LPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_NPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_HPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_CPM_TC1","MPP_PTX_POW_Digital_Ping_360_OV_CPM_TC2","MPP_PTX_POW_Digital_Ping_360_OV_LPM_TC2","MPP_PTX_POW_Digital_Ping_360_OV_NPM_TC2","MPP_PTX_POW_Digital_Ping_360_OV_HPM_TC2","MPP_PTX_POW_KEst_P1","MPP_PTX_POW_KEst_P2","MPP_PTX_CPX_PNG_RX_IDENTIFICATION_TC3"]:
                                if flow2 is None : self.TCRemarks.append(["360Khz Flow not found for the testcase",Enums.TestResult.INCONCLUSIVE])
                
                return {1:flow1,2:flow2}
        except Exception as e:
            er = traceback.print_exc()
            self.update_TClogs("Exception",f"SegricatePackets {str(e)}")
    #-categorise packets into phase wise , with its responses
    def GetAllPackets(self):
        if self.Test.TestcaseID in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
            self.Test.Flows = {1: {'Limit': [0, len(self.file_list)-1], 'Flow': 1}, 2: None}
        # print("flows:",self.Test.Flows)
        if self.Test.Flows is not None:
            for flwID in self.Test.Flows:
               
                if self.Test.Flows[flwID] is not None:
                   
                    if flwID not in self.Test.timing_map:self.Test.timing_map[flwID]={}
                    self.Test.FlowLimit =self.Test.Flow_limit= self.Test.Flows[flwID]['Limit']
                    # print("self.Test.FlowLimit:",self.Test.FlowLimit)
                    id = self.Test.FlowLimit[0]
                    if self.Test.TestcaseID not in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
                        while id < self.Test.FlowLimit[1]:
                            if self.PktMethod.GetPacketType(id)=='Packet':
                                phase = 'General' if self.file_list[id]['description']=='' else self.file_list[id]['description']
                                if phase not in self.Test.timing_map[flwID]:self.Test.timing_map[flwID][phase]={}
                                packet =  self.file_list[id]['pktType']
                                if packet not in self.Test.timing_map[flwID][phase]:self.Test.timing_map[flwID][phase][packet]=[]
                                #check for the response
                                rid = id+1
                                while rid <= self.Test.FlowLimit[1]:
                                    if self.PktMethod.GetPacketType(rid)=='Response':
                                        self.Test.timing_map[flwID][phase][packet].append([[id,self.file_list[id]['value'],self.file_list[id]['startTime'],self.file_list[id]['stopTime']],[rid,self.file_list[rid]['pktType'],self.file_list[rid]['startTime'],self.file_list[rid]['stopTime']]])
                                        id=rid+1
                                        break
                                    elif self.PktMethod.GetPacketType(rid)=='Packet':
                                        self.Test.timing_map[flwID][phase][packet].append([[id,self.file_list[id]['value'],self.file_list[id]['startTime'],self.file_list[id]['stopTime']]])
                                        id=rid
                                        break
                                    if rid==self.Test.FlowLimit[1]:
                                        self.Test.timing_map[flwID][phase][packet].append([[id,self.file_list[id]['value'],self.file_list[id]['startTime'],self.file_list[id]['stopTime']]])
                                        id=rid
                                        break
                                    rid+=1
                            else:id+=1
                    #Add General Packets
                    # print("timing_map1:",Test.timing_map)
                    self.Test.timing_map[flwID]['General']={}
                    self.Test.timing_map[flwID]['General']['PD']=[[[self.Test.FlowLimit[0],self.file_list[self.Test.FlowLimit[0]]['value'],self.file_list[self.Test.FlowLimit[0]]['startTime'],self.file_list[self.Test.FlowLimit[0]]['stopTime']]]]
                    self.Test.timing_map[flwID]['General']['SD']=[[[self.Test.FlowLimit[1],self.file_list[self.Test.FlowLimit[1]]['value'],self.file_list[self.Test.FlowLimit[1]]['startTime'],self.file_list[self.Test.FlowLimit[1]]['stopTime']]]]
                    #Get Freq data
                    res = self.PktMethod.GetPacketDetails(value='FOP:',limit=self.Test.FlowLimit,Type = "TesterMsg")
                    if len(res)>2:
                        self.Test.timing_map[flwID]['General']['FOP'] =[res[2],self.file_list[res[2]]['value'],res[0],res[1]]
                    #Add Loads
                    self.Test.timing_map[flwID]['Loads'] =[]
                    LoadLimit = [self.Test.timing_map[flwID]['General']['PD'][0][0][0],self.Test.timing_map[flwID]['General']['SD'][0][0][0]]
                    Lid = LoadLimit[0]

                    while Lid < LoadLimit[1]:
                        if 'Set_Load' in self.file_list[Lid]['pktType']:
                            self.Test.timing_map[flwID]['Loads'].append([Lid,self.file_list[Lid]['pktType'],self.file_list[Lid]['startTime'],self.file_list[Lid]['stopTime']])
                        Lid+=1
                    #Add timing checks
                    self.Test.timing_map[flwID]['Timings']=self.TimingChecksGeneral(flwID,self.Test.FlowLimit)

                    if GeneralConfig.Product == Enums.Product.C3 or GeneralConfig.Mode == Enums.Mode.TPT:
                        module_path = f"OfflineValidationModules.{GeneralConfig.Product}{GeneralConfig.Mode}.V_{ProjectConfiguration.Certification.replace('.', '_')}.CTSChecks{GeneralConfig.Product}{GeneralConfig.Mode}"
                        try:spec = importlib.util.find_spec(module_path)
                        except ModuleNotFoundError : spec= None
                        if spec is not None:
                            module = importlib.import_module(module_path)
                            self.CTSClass = getattr(module, f"CTSChecks_{GeneralConfig.Product}{GeneralConfig.Mode}")()
                        else:
                            module_path = f"OfflineValidationModules.{GeneralConfig.Product}{GeneralConfig.Mode}.Backward.CTSChecks{GeneralConfig.Product}{GeneralConfig.Mode}"
                            module = importlib.import_module(module_path)
                            self.CTSClass = getattr(module, f"CTSChecks_{GeneralConfig.Product}{GeneralConfig.Mode}")()
                        self.Test.timing_map[flwID]['Measures']= self.MeasuresCheck(flwID,self.Test.Flows)

                    else:
                        if GeneralConfig.Mode == Enums.Mode.TPR:
                            Coil = ""
                            if  self.Test.Coil == "TPR#MPP1":
                                Coil = "MPPTPR1"
                                module_path = f"OfflineValidationModules.{GeneralConfig.Product}{GeneralConfig.Mode}.V_{ProjectConfiguration.Certification.replace('.', '_')}.MPPTPR1"
                                try:spec = importlib.util.find_spec(module_path)
                                except ModuleNotFoundError : spec= None
                                if spec is not None:
                                    module = importlib.import_module(module_path)
                                    CTSChecks= getattr(module, f"CTSChecks_MPP_TPR1")
                                else:
                                    module_path = f"OfflineValidationModules.{GeneralConfig.Product}{GeneralConfig.Mode}.Backward.MPPTPR1"
                                    module = importlib.import_module(module_path)
                                    CTSChecks = getattr(module, f"CTSChecks_MPP_TPR1")
                                
                                # self.CTSChecks_obj1 = CTSChecks_MPP_TPR1(Header=self.Header,file_list=self.file_list,JapiData=JsonConfig.JapiData,BackupJson=ProjectConfiguration.BackupJson,ProjectJson=self.Test.ProjectJson)
                                # Test.timing_map[flwID]['Measures']= self.CTSChecks_MPPTPR1.MeasuresCheck(flwID,self.Test.Flows,Test.timing_map)
                            elif  self.Test.Coil == "TPR#MPP4" or  self.Test.Coil == "TPR_MPP4":
                                Coil = "MPPTPR4"
                                module_path = f"OfflineValidationModules.{GeneralConfig.Product}{GeneralConfig.Mode}.V_{ProjectConfiguration.Certification.replace('.', '_')}.MPPTPR4"
                                try:spec = importlib.util.find_spec(module_path)
                                except ModuleNotFoundError : spec= None
                                if spec is not None:
                                    module = importlib.import_module(module_path)
                                    CTSChecks= getattr(module, f"CTSChecks_MPP_TPR4")
                                else:
                                    module_path = f"OfflineValidationModules.{GeneralConfig.Product}{GeneralConfig.Mode}.Backward.MPPTPR4"
                                    module = importlib.import_module(module_path)
                                    CTSChecks = getattr(module, f"CTSChecks_MPP_TPR4")
                                
                            self.CTSChecksOBJ=CTSChecks(Header=self.Header,file_list=self.file_list,JapiData=JsonConfig.JapiData,BackupJson=ProjectConfiguration.BackupJson,ProjectJson=ProjectConfiguration.ProjectJson)
                            self.Test.timing_map[flwID]['Measures']= self.MeasuresCheck2(flwID,self.Test.Flows,Coil)
                            # print("Measures:",Test.timing_map[flwID]['Measures'])
                       
                        
                    # if self.Test.TestcaseID not in ["MPP_PTX_CPX_PNG_T_NOPOWER"]:
                    self.Test.timing_map[flwID]['Others']= self.GeneralCheck(flwID)
                    # print("Header TC result:",self.Test.AutomationResult)
                    # print("Others",Test.timing_map[flwID]['Others']["TestIssues_Details"])
                    if GeneralConfig.Product == Enums.Product.MPP and GeneralConfig.Mode == Enums.Mode.TPR:
                        for chks in self.Test.timing_map[flwID]['Others']["TestIssues_Details"]:
                            if Enums.TestResult.FAIL in chks[1]:
                                if Enums.TestResult.INCONCLUSIVE in self.Test.AutomationResult:
                                    self.Test.AutomationResult=Enums.TestResult.INCONCLUSIVE
                                    break
                                else: self.Test.AutomationResult=Enums.TestResult.FAIL
                                
                            elif Enums.TestResult.INCONCLUSIVE in chks[1]:
                                self.Test.AutomationResult=Enums.TestResult.INCONCLUSIVE
                                break
                                
                        
                    self.PayLoadCheck(flwID)

    
    def MeasuresCheck(self,flwID,flows):
        try:
            AllMeasures={}
            print(self.Test.TestcaseID)
            if self.Test.TestcaseID in self.JCTSData[GeneralConfig.Product][GeneralConfig.Mode]:
                if ProjectConfiguration.Certification in self.JCTSData[GeneralConfig.Product][GeneralConfig.Mode][self.Test.TestcaseID]['Certifications']:
                    CTSJson=self.JCTSData[GeneralConfig.Product][GeneralConfig.Mode][self.Test.TestcaseID]['CTSChecks']
                    AllMeasures=self.CTSClass.CTSChecks(flwID,flows,CTSJson)   
                else:
                    NotalEnabled=False
                    if self.JCTSData[GeneralConfig.Product][GeneralConfig.Mode][self.Test.TestcaseID][ProjectConfiguration.Certification].get("Notal",False):
                        for  Notal in self.JCTSData[GeneralConfig.Product][GeneralConfig.Mode][self.Test.TestcaseID][ProjectConfiguration.Certification]['Notal']:
                            if Notal in self.GetNotals():
                                NotalEnabled=True
                                CTSJson= self.JCTSData[GeneralConfig.Product][GeneralConfig.Mode][self.Test.TestcaseID][ProjectConfiguration.Certification]['Notal'][Notal]
                                AllMeasures=self.CTSClass.CTSChecks(flwID,flows,CTSJson)

                    if not NotalEnabled:
                        CTSJson=self.JCTSData[GeneralConfig.Product][GeneralConfig.Mode][self.Test.TestcaseID][ProjectConfiguration.Certification]['CTS']
                        AllMeasures=self.CTSClass.CTSChecks(flwID,flows,CTSJson)

            print('Measures',AllMeasures)
            return(AllMeasures)
        except Exception as e:
            traceback.print_exc() 
    

    def MeasuresCheck2(self,flwID,flows,Coil):
        # print("Certification:",ProjectConfiguration.Certification)
        self.Test.Flows = flows
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',JsonConfig.JapiData)
        try:
            AllMeasures={}
            print("TestcaseID:",self.Test.TestcaseID)
            if self.Test.TestcaseID in self.JCTSData[Coil]:
                notal_executed = False
                # Notal testcases
                if self.JCTSData[Coil][self.Test.TestcaseID].get("Notal"):
                    if self.JCTSData[Coil][self.Test.TestcaseID]["Notal"].get(ProjectConfiguration.Certification):
                        if len(self.JCTSData[Coil][self.Test.TestcaseID]["Notal"][ProjectConfiguration.Certification].keys()) >0:
                            for notal in self.JCTSData[Coil][self.Test.TestcaseID]["Notal"][ProjectConfiguration.Certification]:
                                if notal in self.GetNotals():
                                    CTSJson= self.JCTSData[Coil][self.Test.TestcaseID]["Notal"][ProjectConfiguration.Certification][notal]
                                    AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)
                                    notal_executed = True

                # Normal testcases
                if not notal_executed:
                    
                    # if ProjectConfiguration.Certification in self.JCTSData[Coil][self.Test.TestcaseID]['common']['Certifications']:
                    #     CTSJson=self.JCTSData[Coil][self.Test.TestcaseID]['common']['CTSChecks']
                    #     AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)
                    
                    # if self.JCTSData[Coil][self.Test.TestcaseID].get(ProjectConfiguration.Certification):
                    #     CTSJson=self.JCTSData[Coil][self.Test.TestcaseID][ProjectConfiguration.Certification]
                    #     common_keys = list(CTSJson.keys())
                    #     CertMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)
                    #     AllMeasures.update(CertMeasures)



                    
                    common_keys = []
                    if self.JCTSData[Coil][self.Test.TestcaseID].get(ProjectConfiguration.Certification):
                        CTSJson=self.JCTSData[Coil][self.Test.TestcaseID][ProjectConfiguration.Certification]['CTSChecks']
                        common_keys = list(CTSJson.keys())
                        AllMeasures=self.CTSChecksOBJ.CTSChecks(flwID,flows,CTSJson)

                    if ProjectConfiguration.Certification in self.JCTSData[Coil][self.Test.TestcaseID]['common']['Certifications']:
                        CTSJson=self.JCTSData[Coil][self.Test.TestcaseID]['common']['CTSChecks']
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
        Certification= ProjectConfiguration.Certification if GeneralConfig.Product == Enums.Product.MPP and GeneralConfig.Mode == Enums.Mode.TPR else str('V_'+ProjectConfiguration.Certification) 
        for Notal,value in ProjectConfiguration.BKjsonData["testBkpProjectConfiguration"]["TesterConfigurationModel"]["notal"].items():
            if value['isActive']:
                if Certification in value['appModeDescription']:
                    Notals.append(Notal)
        return Notals



    #-apply all timing checks for the received pacekts with all details
    def TimingChecksGeneral(self,flwID,FlowLimit):
        # print(Test.timing_map[flwID])
        try:
            AllTimings={}
            cnt = 1
            EPP=False
            for timeChk in JsonConfig.JTimeData[GeneralConfig.Product][GeneralConfig.Mode]:

                if self.Test.TestcaseID in JsonConfig.JTimeData[GeneralConfig.Product][GeneralConfig.Mode][timeChk]['skip']:continue
                # print(timeChk)
                timeChkSetup = JsonConfig.JTimeData[GeneralConfig.Product][GeneralConfig.Mode][timeChk]
                timeChkList = []
                # print(JsonConfig.JTimeData[GeneralConfig.Product][GeneralConfig.Mode][timeChk][self.Test.TestcaseID])
                tol = JsonConfig.JTimeData[GeneralConfig.Product][GeneralConfig.Mode][timeChk]['default'] if self.Test.TestcaseID not in JsonConfig.JTimeData[GeneralConfig.Product][GeneralConfig.Mode][timeChk] else JsonConfig.JTimeData[GeneralConfig.Product][GeneralConfig.Mode][timeChk][self.Test.TestcaseID] 
                #Update Tolerence specif to Prodct / mode
                if timeChk in ['tintervalCE-CE_PT','tintervalCE-CE_CL'] and EPP and GeneralConfig.Product != Enums.Product.C3 and GeneralConfig.Mode != Enums.Mode.TPR: tol=[0,700]
                if timeChk in ['treceviedRP8-RP8'] and GeneralConfig.Product == Enums.Product.C3 and GeneralConfig.Mode == Enums.Mode.TPR:
                    if  self.Test.Coil=="TPR#5":tol=[3900,5]
                    elif   self.Test.Coil=="TPR#6":tol=[2000,5]
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
                valid_list = (['twake', 'tintervalSRQ/EN-CE'] if GeneralConfig.Product == Enums.Product.MPP else ['twake', 'tintervalCNF-XCE', 'tintervalCFG-CE', 'tintervalSRQ/EN-CE'])
                if timeChk in valid_list:
                    StartPhase=timeChkSetup['PhasePkts']['Start']['Phase']
                    EndPhase=timeChkSetup['PhasePkts']['End']['Phase']
                    StartPacket=timeChkSetup['PhasePkts']['Start']['Packet']
                    EndPacket=timeChkSetup['PhasePkts']['End']['Packet']
                    if  timeChk =='tintervalCFG-CE' and StartPhase in self.Test.timing_map[flwID] and StartPacket in self.Test.timing_map[flwID][StartPhase] and len(self.Test.timing_map[flwID][StartPhase][StartPacket][0])==2 and "ACK" in self.Test.timing_map[flwID][StartPhase][StartPacket][0][1]:
                        EPP=True
                        continue
                    if all(res in self.Test.timing_map[flwID] for res in [StartPhase,EndPhase]):
                        if  StartPacket in self.Test.timing_map[flwID][StartPhase] and EndPacket in self.Test.timing_map[flwID][EndPhase]:                          
                            if  len(timeChkSetup['PhasePkts']['Start']['Value'])==0 or timeChkSetup['PhasePkts']['Start']['Value'][0] in self.Test.timing_map[flwID][StartPhase][StartPacket][len(self.Test.timing_map[flwID][StartPhase][StartPacket])-1][0][1] :
                                AllTimings[timeChk] = str(round((self.Test.timing_map[flwID][EndPhase][EndPacket][0][0][2] - self.Test.timing_map[flwID][StartPhase][StartPacket][0 if timeChk=="tintervalCFG-CE" else len(self.Test.timing_map[flwID][StartPhase][StartPacket])-1][0][2])*1000,2)+timeChkSetup['Preamble'])
                                AllTimings[f'{timeChk}_remark']=f'Measured {timeChk} is {AllTimings[timeChk]} ms, between {StartPacket} @{self.Test.timing_map[flwID][StartPhase][StartPacket][len(self.Test.timing_map[flwID][StartPhase][StartPacket])-1][0][0]} to {EndPacket} @{self.Test.timing_map[flwID][EndPhase][EndPacket][0][0][0]} + {timeChkSetup['Preamble']}.'
                                res= float(AllTimings[timeChk]) >= tol[0]-tol[1]-0.1 and float(AllTimings[timeChk]) <= tol[0]+tol[1]+0.1 if tol[0]!=0 else float(AllTimings[timeChk]) >= tol[0] and float(AllTimings[timeChk]) <= tol[1]+0.1 #0.1 is tolerance
                                AllTimings[f'{timeChk}_Details'].append([f"{AllTimings[f'{timeChk}_remark']} The measured value is {'' if res else 'not'} in limit:{AllTimings[f'{timeChk}_exp']} ms.",Enums.TestResult.PASS if res else Enums.TestResult.FAIL])
                        else:AllTimings[f'{timeChk}_Details'].append([f'All required packets not found to perform the {timeChk}',Enums.TestResult.FAIL])
                    else:AllTimings[f'{timeChk}_Details'].append([f'All required packets not found to perform the {timeChk}',Enums.TestResult.FAIL])
                #check for timings btw all packets for mentioned phases_____________________________________________________________________________________________________
               
                elif timeChk in ["tstart","tsilent"]:

                    Limits=str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
                    if timeChk=='tsilent' and GeneralConfig.Mode == Enums.Mode.TPT: Limits= f'GTE {tol[1]}'
                   
                    id=self.Test.FlowLimit[0]
                    Pktslist =[]
                    while id < self.Test.FlowLimit[1]:
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
                            if (res < tol[0]-tol[1] or res >tol[0]+tol[1]) if tol[0]!=0 else res < tol[1] if GeneralConfig.Mode == Enums.Mode.TPT and timeChk=='tsilent' else res > tol[1]:
                                AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is not in limit: {Limits}ms.",Enums.TestResult.FAIL])
                            else:
                                AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is in limit: {Limits}ms.",Enums.TestResult.PASS])
                            id+=1
                        AllTimings[timeChk]=';'.join(map(str,timeChkList))

                #check timings btw packet and which has response_____________________________________________________________________________________________________
                elif timeChk in ["tresponse","tresponseAuth","tresponseCNF"]:
                    # print(timeChk)
                    if self.Test.TestcaseID not in ["MPP_PTX_POW_LEGACY_PRX_P1","MPP_PTX_POW_LEGACY_PRX_P2"]:
                        for phase in self.Test.timing_map[flwID]:
                            if phase not in ['General','Loads']:
                                for pkts in self.Test.timing_map[flwID][phase]:
                                    # print(pkts)
                                    stus = False
                                    if timeChk in ["tresponse"]:
                                        if pkts not in timeChkSetup['PhasePkts']['Packet_Exp']:stus=True
                                    elif timeChk in ["tresponseAuth","tresponseCNF"]:
                                        if pkts in timeChkSetup['PhasePkts']['Packet']:stus=True
                                    if stus == True:
                                        pk = self.Test.timing_map[flwID][phase][pkts]
                                        if type(pk) == list:
                                            for pks in pk:
                                                if type(pks) == list:
                                                    if len(pks)>1:
                                                        # print("pks:",pks)
                                                        res = round((pks[1][2] - pks[0][3])*1000,1)
                                                        timeChkList.append(res)
                                                        if (res < tol[0]-tol[1] or res >tol[0]+tol[1]) if tol[0]!=0 else res > tol[1]:
                                                            AllTimings[f'{timeChk}_Details'].append([f"Measured tresponse {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{pks[1][0]}",Enums.TestResult.FAIL])
                                                        else:
                                                            AllTimings[f'{timeChk}_Details'].append([f"Measured tresponse {res} in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{pks[1][0]}",Enums.TestResult.PASS])
                    AllTimings[timeChk]=';'.join(map(str,timeChkList)) if len(timeChkList)>0  else 'NA'
                    AllTimings[f'{timeChk}_exp'] = str(round(tol[0]-tol[1],2))+'-'+str(round(tol[0]+tol[1],2)) if tol[0]!=0 else str(tol[0])+'-'+str(tol[1])
                    #Keep only failures in sunchecks to save space
                elif timeChk in ["tintervalXCE-XCE","tintervalCE-CE_PT","tintervalCE-CE_CL","treceviedPLA-PLA","treceviedRPM1-RPM1","treceviedRPM2-RPM2","treceviedRPM0-RPM0","treceviedRP8-RP8"]:
                    # print(timeChk)
                    Pktslist =[]
                    for phase in self.Test.timing_map[flwID]:
                        if phase in timeChkSetup['PhasePkts']['Phase']:
                            for pkts in self.Test.timing_map[flwID][phase]:
                                # if any(res in pkts for res in timeChkSetup['PhasePkts']['Packet']):
                                if any(res == pkts for res in timeChkSetup['PhasePkts']['Packet']):
                                    # print(pkts,timeChkSetup['PhasePkts']['Packet'])
                                    for Pkt in self.Test.timing_map[flwID][phase][pkts]:
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
                        if self.Test.TestcaseID in ["MPP_PTX_POW_OVP_FAST_RECOVERY_TC_1","MPP_PTX_POW_OVP_FAST_RECOVERY_TC_2"]:
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
                                        AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is not in limit: {AllTimings[f'{timeChk}_exp']} ms.",Enums.TestResult.FAIL])
                                    else:
                                        # FalsetimeChk.append('Pass')
                                        AllTimings[f'{timeChk}_Details'].append([f"Measured {timeChk}={res} between {self.file_list[Pktslist[id][0]]['pktType']}_{self.file_list[Pktslist[id][0]]['value']} at index {Pktslist[id][0]} and {self.file_list[Pktslist[id+1][0]]['pktType']}_{self.file_list[Pktslist[id+1][0]]['value']} at index {Pktslist[id+1][0]} is in limit: {AllTimings[f'{timeChk}_exp']} ms.",Enums.TestResult.PASS])
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
                    AllTimings[f'{timeChk}_res']=Enums.TestResult.FAIL if Enums.TestResult.FAIL in [item[1] for item in AllTimings[f'{timeChk}_Details']] else Enums.TestResult.PASS
                    #compress subchecks to keep only pass
                    if timeChk in ['tresponse',"tresponseAuth","treceviedPLA-PLA",'tintervalXCE-XCE','tintervalCE-CE',"tintervalCE-CE_CL","tintervalCE-CE_PT","treceviedRPM1-RPM1","treceviedRPM2-RPM2","treceviedRPM0-RPM0","treceviedRP8-RP8"]:
                        subck = []
                        for chk in AllTimings[f'{timeChk}_Details']:
                            if chk[1] == Enums.TestResult.FAIL:subck.append(chk)
                        AllTimings[f'{timeChk}_Details']=subck if len(subck)>0 else [[f"All the measured {timeChk} are within the Limit: {AllTimings[f'{timeChk}_exp']} mS",Enums.TestResult.PASS]]
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
            for GenCheck in JsonConfig.JGenCheckData[GeneralConfig.Product][GeneralConfig.Mode]:
                if self.Test.TestcaseName not in JsonConfig.JGenCheckData[GeneralConfig.Product][GeneralConfig.Mode][GenCheck]['ExemeptedTC']:
                    if flwID in JsonConfig.JGenCheckData[GeneralConfig.Product][GeneralConfig.Mode][GenCheck]['Default']['flow']:
                        exp = JsonConfig.JGenCheckData[GeneralConfig.Product][GeneralConfig.Mode][GenCheck]['Default']['expected']
                        Flow_limit = self.Test.Flows[flwID]['Limit']
                        if GenCheck in ['F1-Fq','F2-Fq']:
                            GeneralCheck[f'{GenCheck}_exp'] = str(exp[0])+'-'+str(exp[1])+' kHz'
                            GeneralCheck[f'{GenCheck}_res'] ='NA'
                            GeneralCheck[f'{GenCheck}_SEQ'] =seqcnt
                            GeneralCheck[GenCheck]="NA"
                            GeneralCheck[f'{GenCheck}_Details'] = []
                            if 'FOP' in self.Test.timing_map[flwID]['General']:
                                res = GeneralMethods.GetFloatFromStr(self.Test.timing_map[flwID]['General']['FOP'][1])
                                GeneralCheck[GenCheck] = res[0]
                                if GeneralCheck[GenCheck] >= exp[0] and GeneralCheck[GenCheck] <= exp[1]:
                                    GeneralCheck[f'{GenCheck}_Details'].append([f"The measured FOP is {GeneralCheck[GenCheck]} kHz at {round(self.Test.timing_map[flwID]['General']['FOP'][2],3)}sec, Limit: [{exp[0]} - {exp[1]}] kHz",Enums.TestResult.PASS])
                                else:GeneralCheck[f'{GenCheck}_Details'].append([f"The measured FOP is {GeneralCheck[GenCheck]} kHz at {round(self.Test.timing_map[flwID]['General']['FOP'][2],3)}sec, Limit: [{exp[0]} - {exp[1]}] kHz",Enums.TestResult.FAIL])
                            else:GeneralCheck[f'{GenCheck}_Details'].append([f"FOP packet not found",Enums.TestResult.FAIL])
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
                                                    res.append([str(self.file_list[id]['pktType'])+'@index='+str(id)+':'+str(d2['sDecodedValue'])+str(d2['sRawData']),Enums.TestResult.FAIL])
                                                else:res.append([str(self.file_list[id]['pktType'])+'@index='+str(id)+':'+str(d2['sDecodedValue'])+str(d2['sRawData']),Enums.TestResult.PASS])
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
                            else:GeneralCheck[f'{GenCheck}_Details']=[["The received packet sequence was proper",Enums.TestResult.PASS]]
                        #Add the final results
                        if len(GeneralCheck[f'{GenCheck}_Details'])>0:
                            GeneralCheck[f'{GenCheck}_res']=Enums.TestResult.FAIL if Enums.TestResult.FAIL in [item[1] for item in GeneralCheck[f'{GenCheck}_Details']] else Enums.TestResult.PASS
                            #compress subchecks to keep only pass
                            if GenCheck in ['ReserveBitChek']:
                                subck = []
                                for chk in GeneralCheck[f'{GenCheck}_Details']:
                                    if chk[1] == Enums.TestResult.FAIL:subck.append(chk)
                                GeneralCheck[f'{GenCheck}_Details']=subck if len(subck)>0 else [["All the received Reserved bit values are proper",Enums.TestResult.PASS]]
                            seqcnt+=1
            # print(GeneralCheck)
            return GeneralCheck
        except Exception as e:
            traceback.print_exc()
 
    #- PayLoad Checks
    def PayLoadCheck(self,flwID):
        try:
            
            if self.Test.UID not in self.Test.PayLoadChecks:self.Test.PayLoadChecks[self.Test.UID]={}
            if self.Test.TestcaseName not in self.Test.PayLoadChecks[self.Test.UID]:self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName]={}
            if flwID not in self.Test.PayLoadChecks:self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID]={}
            self.Test.FlowLimit = self.Test.Flows[flwID]['Limit']
            id = self.Test.FlowLimit[0]
            while id < self.Test.FlowLimit[1]:
                Type=self.PktMethod.GetPacketType(id)
                if Type in ['Packet', 'Response']:
                    phase = 'General' if self.file_list[id]['description']=='' else self.file_list[id]['description']
                    if phase not in self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID]:self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase]={}
                    # print(phase)
                    packet =  self.file_list[id]['pktType']
                    if packet in["Get Request","General Request","DSR"]:packet+=" "+self.file_list[id]['value'].replace('{','').replace('}','')
                    elif packet in ["SRQ [0x20] "]:packet="Specific Request"+" "+self.file_list[id]['value'].replace('{','').replace('}','').split(':')[0]
                    elif packet in ["FOD Status"]: packet+=" "+self.file_list[id]['value'].replace('{','').replace('}','').split(':')[0]
                    elif packet in['SADC','ADC']:packet+=" "+self.file_list[id]['value'].replace('{','').replace('}','').split(':')[0]
                    # print(f'{packet} @{Type}')
                    try:
                        
                        #     print("packet:",packet)
                        if f'{packet} @{Type}' not in self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase]:
                            self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']={}
                            if 'PayLoadCheck' not  in self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']:
                                self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']['PayLoadCheck']=[]
                                try:
                                    if len(JsonConfig.JPayLoadCheckData[GeneralConfig.Product][GeneralConfig.Mode][str(flwID)][phase][f'{packet} @{Type}']['PayLoadCheck']) > 0:
                                        for PacketDetails in JsonConfig.JPayLoadCheckData[GeneralConfig.Product][GeneralConfig.Mode][str(flwID)][phase][f'{packet} @{Type}']['PayLoadCheck']:
                                            # print("Name:",PacketDetails['Name'])
                                            expected = PacketDetails.get("Exp", []) 
                                            comp=PacketDetails.get("comp", "EQL")
                                            CompType=PacketDetails.get("Type", "DEC")
                                            count=0
                                            while count < len(PacketDetails['ExemeptedTC']):
                                                if self.Test.TestcaseID in PacketDetails['ExemeptedTC'][count]['TestCase']:
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
                                                    self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']['PayLoadCheck'].append({'CheckName': PacketDetails.get("Name"), 'Byte': PacketDetails.get("Byte"),'Bit': PacketDetails.get("Bit"),'Expected': {Expected},'Received': actual_val,'Result': status })
                                                    TestObjects.SQLConn.ExecutebyQuery("INSERT INTO PayLoadDetails (UID, SEQID, Type, Phase, PacketID, Packet, HeaderName, CheckName, Byte, Bit, ExpValue, RecValue, ChecksResult, HeaderResult) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (self.Test.UID, flwID, 'PayLoad', phase, id, f"{packet} @{Type}", None, PacketDetails.get('Name'), PacketDetails.get('Byte'), PacketDetails.get('Bit'), str(Expected), actual_val, status, None))
                                    else: TestObjects.SQLConn.ExecutebyQuery( "INSERT INTO PayLoadDetails (UID, SEQID, Type, Phase, PacketID, Packet, HeaderName, CheckName, Byte, Bit, ExpValue, RecValue, ChecksResult, HeaderResult) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (self.Test.UID, flwID, 'PayLoad', phase, id, f"{packet} @{Type}", None, '--', '--', '--', '--', '--', '--', None))
                                except Exception as e: e
                                    # print("PayLoadCheck",e)
                                
                            if 'HeaderCheck' not in self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']:
                                self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']['HeaderCheck']=[]
                                try:
                                    headers = self.file_list[id].get('header_Payload', {})
                                    ReceivedHeader=headers.get('sFieldType', None)
                                    if ReceivedHeader is not None:
                                        HeaderName=JsonConfig.JPayLoadCheckData[GeneralConfig.Product][GeneralConfig.Mode][str(flwID)][phase][f'{packet} @{Type}']['HeaderCheck'][0]['HeaderName']
                                        
                                        if f'{packet} @{Type}' in ["ACK @Response" ,"ATN @Response","NAK @Response","ND @Response", "MPP ACK @Response","MPP:ACK @Response"] and GeneralConfig.Product == Enums.Product.MPP and GeneralConfig.Mode == Enums.Mode.TPT:
                                            ReceivedHeader=ReceivedHeader.split(':')[1].split()[-1]
                                        else:ReceivedHeader=ReceivedHeader.split(':')[1].split()[0]
                                        if HeaderName==ReceivedHeader: status = "PASS" 
                                        else: status="FAIL"
                                        self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']['HeaderCheck'].append({'HeaderName': HeaderName,'Result': status })
                                    if  self.Test.PayLoadChecks[self.Test.UID][self.Test.TestcaseName][flwID][phase][f'{packet} @{Type}']['HeaderCheck'][0]['Result']=='PASS':
                                        TestObjects.SQLConn.ExecutebyQuery("UPDATE PayLoadDetails SET HeaderResult = ?, HeaderName = ? ""WHERE UID = ? AND SEQID = ? AND Type = 'PayLoad' AND Phase = ? " "AND PacketID = ? AND Packet = ?", ('PASS', HeaderName, self.Test.UID, flwID, phase, id, f"{packet} @{Type}"))
                                    else: TestObjects.SQLConn.ExecutebyQuery( "UPDATE PayLoadDetails SET HeaderResult = ?, HeaderName = ? " " WHERE UID = ? AND SEQID = ? AND Type = 'PayLoad' AND Phase = ? " "AND PacketID = ? AND Packet = ?",('FAIL', HeaderName, self.Test.UID, flwID, phase, id, f"{packet} @{Type}"))
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
        FinalRepData = JsonConfig.read_file(JsonConfig.JTCPData['test_config_data']['Report_path'])
        FinalRepData.append({'Header':self.Header,'SeqResults':self.Test.timing_map})
        #Sorting TBD -- Not req
        JsonConfig.write_file(JsonConfig.JTCPData['test_config_data']['Report_path'],FinalRepData)
        

###Support Functions ####################################################################################################################
    #-Get Run time of the testcase, returns start time and end in nanoseconds,
    def GetRunTime(self):
        TcStartAPI = APIOperations(url=JsonConfig.JapiData[GeneralConfig.Product][GeneralConfig.Mode]['GetWaveformStartTime'],retype='json')
        TCstartTime = TcStartAPI.GetRequest()
        TcStopAPI = APIOperations(url=JsonConfig.JapiData[GeneralConfig.Product][GeneralConfig.Mode]['GetWaveformStopTime'],retype='json')
        TCstopTime = TcStopAPI.GetRequest()
        return[TCstartTime,TCstopTime/100000000]
    #-Create log releated to a testcase validation steps. update same into debug logfile
    def update_TClogs(self,logtype,log):
        # print(log)
        dt_object = datetime.fromtimestamp(datetime.now().timestamp())
        self.Test.TCLogs.append([str(dt_object),logtype,log])
 
    #- Get software side high level results
    def GetJSONTCData(self,TestID=None,BackupJson=None,retunData=""):
        try:
           
            for TCdata in ProjectConfiguration.BKjsonData['testBkpTestResultsandPath']:
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
                        self.Test.STestStartTime = TCdata['TestStartTime']
                        self.Test.STestEndTime = TCdata['TestEndTime']
                        stime = [int(num) for num in self.Test.STestStartTime.split('T')[1].split('+')[0].replace('.',':').split(':')]
                        etime = [int(num) for num in self.Test.STestEndTime.split('T')[1].split('+')[0].replace('.',':').split(':')]
                        st = (((stime[0]*1000)*60)*60)+((stime[1]*1000)*60)+(stime[2]*1000)+stime[3]
                        et = (((etime[0]*1000)*60)*60)+((etime[1]*1000)*60)+(etime[2]*1000)+etime[3]
                        self.Test.SValidatedTime =abs(st-et)
                        break
        except Exception as e:
            traceback.print_exc()
    #- General method to retun values from backupjson file for a testcase.
    def GetTCValuesfromBackUpJSON(self,KeyToFind="_testID"):
       
        for TCdata in ProjectConfiguration.BKjsonData['testBkpTestResultsandPath']:
            if TCdata['testcaseDetails']['m_DisplayName'] ==  self.Test.TestcaseName:
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
        
        # For the Loaded Trace File, get the TcId's  through API 
        SWResult = APIOperations(url=JsonConfig.JapiData[GeneralConfig.Product][GeneralConfig.Mode]['GetWaveFormTestResult'],retype='json')
        SwResultJson = SWResult.GetRequest()
        mTestId=[]
        for data in SwResultJson[0].get("children",[]):
            for child in data['children']:
                for sub in child['children']:
                    if "Couldn't capture test start assertion message" not in sub['displayString']:
                        mTestId.append(sub['testParentId'])  
                    break       
        if len(self.SubTClist)==len(mTestId): return mTestId.index(self.Test.TestcaseID)   
        return 0


    


# obj = TestValidation(TestID="MPP_PRX_FOD_BEFOREPOWER_DEVICEDET_Q_DEF_P1",TestCaseName="9.1 MPP.PTX.POW.GUARANTEED_POWER.P1",
# ProjectJson=r"D:\C3 TPT Reports\MPP TPT\GXL_231_023_V231_300426_144431\V231_GRL_C3_FinalReport.json",
# BackupJson = r"D:\C3 TPT Reports\MPP TPT\GXL_231_023_V231_300426_144431\V231_Final_TestBackup.gproj",
# TracePath=r"C:\Users\GRL\Downloads\Apple_1_V22_240425_132541\Run4\9_1_P4\9_1_P4.grltrace")