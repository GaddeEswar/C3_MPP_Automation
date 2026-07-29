SELECT Header.TestcaseName, Header.SWresult,Header.TCresult as AutomationResult,
ChecksHeader.SEQID,ChecksHeader.CheckSEQ,ChecksHeader.Description,
ChecksDetails.Remarks,ChecksDetails.Result
from Header
LEFT JOIN ChecksHeader on Header.UID = ChecksHeader.UID
Left JOIN ChecksDetails on ChecksHeader.UID = ChecksDetails.UID and ChecksHeader.Description = ChecksDetails.Description
WHERE ChecksHeader.Type="Measures" and Header.SWVersion="2.220.0.20"
ORDER by Header.TestcaseName,ChecksHeader.SEQID