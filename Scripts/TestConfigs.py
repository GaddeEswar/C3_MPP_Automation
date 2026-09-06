"""
TestConfigs module for C3 and MPP Automation.
Defines GeneralConfig and TestCaseConfig data models with type annotations.
"""

from typing import List, Any, Union,Dict
from Scripts.Enums import Enums


class GeneralConfig:
    """
     Created Bydefault variables and assigned defaults when opening the application
     Updated based on selection changes in GUI
    """
    Product: str = Enums.Product.MPP
    Mode: str = Enums.Mode.TPT
    Switch: str = Enums.Switch.OFFLINE
    Transmitter: str = ""
    potentialPower: Union[int, float, str] = 0
    QiID: str = ""
    Certification: str = ""
    PowerProfile: str = ""
    ProjectName: str = ""
    Run: int = 0
    DUTName: str = ""
    DUTID: str = ""
    DUTSL: str = ""
    DBStatus: str = "NotUpdated"
    CTSVersion: str = ""

class BoardConfig:

    SWVersion: str = ""
    FWVersion: str = ""
    HWVersion: str = ""
    BoardNo: str = ""
    BoardModel: str = ""

class TesterConfigurationModel:

    testlabmanager: str = ""
    testLab: str = ""
    testlablocation: str = ""
    testEngineer: str = ""
    phonenumber: str = ""
    email: str = ""
    remarksComments: str = ""
    
class TestCaseConfig:

    UID: str = ""
    TestcaseID: str = ""
    TestcaseName: str = ""
    ChapterName:str = ""
    Coil: str = ""
    AutomationResult: str = Enums.TestResult.NOT_RUN
    SoftwareResult: str = Enums.TestResult.NOT_RUN
    TestStartTime: str = ""
    TestEndTime: str = ""
    ValidatedTime: str = ""
    Remarks: List[Any] = []
    Results: List[Any] = []
    ProjectJson: str = ""
    TracePath: str = ""
    BackupJson: str = ""
    FileList: List[dict] = []
    Flows:dict |None = None
    FlowLimit:list=[]


    


