"""
TestConfigs module for C3 and MPP Automation.
Defines GeneralConfig and TestCaseConfig data models with type annotations.
"""

from typing import Optional,Union,Any
from Models.Enums import Enums
from dataclasses import dataclass,field


class GeneralConfig:
    """
     Created Bydefault variables and assigned defaults when opening the application
     Updated based on selection changes in GUI
    """
    Product: str = Enums.Product.MPP
    Mode: str = Enums.Mode.TPT
    Switch: str = Enums.Switch.OFFLINE
    DBStatus: str = "NotUpdated"
    

class ProjectConfiguration:
   
    ProjectName: str = ""
    Certification: str = ""
    PowerProfile: str = ""
    potentialPower: Union[int, float, str] = 0
    Transmitter :str = ""
    DUTName: str = ""
    DUTID: str = ""
    DUTSL: str = ""
    QiID: str = ""
    CTSVersion: str = ""
    ProjectJson: str = ""
    BackupJson: str = ""
    PRjsonData: dict = {}
    BKjsonData: dict = {}
    Run :int=0


    # Board and Software details
    SWVersion: str = ""
    FWVersion: str = ""
    HWVersion: str = ""
    BoardNo: str = ""
    BoardModel: str = ""

    #user details
    testlabmanager: str = ""
    testLab: str = ""
    testlablocation: str = ""
    testEngineer: str = ""
    phonenumber: str = ""
    email: str = ""
    remarksComments: str = ""
 
@dataclass
class TestCaseConfig:
    
    UID: str = ""
    TestcaseID: str = ""
    TestcaseName: str = ""
    ChapterName: str = ""
    Coil: str = ""
    AutomationResult: str = Enums.TestResult.NOT_RUN
    SoftwareResult: str = Enums.TestResult.NOT_RUN
    STestStartTime: str = ""
    STestEndTime: str = ""
    SValidatedTime: str = ""
    Remarks: list[Any] = field(default_factory=list)
    Results: list[Any] = field(default_factory=list)
    TracePath: str = ""
    file_list: list[dict] = field(default_factory=list)
    Flows: dict[str, Any] | None = None
    Flow_limit: list[dict[str, Any]] = field(default_factory=list)
    timing_map:dict = field(default_factory=dict)
    PayLoadChecks:dict=field(default_factory=dict)
    TCLogs=[]

class TestObjects:

    """
        Store ALL the TestObjects references here
        Using these references we can access any object in the application
    """
    
    TestCaseConfig :TestCaseConfig = TestCaseConfig()
    SQLConn=None
    PktMethod=None
    PlotMethod=None
    
    


