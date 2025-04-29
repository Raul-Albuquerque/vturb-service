from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel


class ReportResponse(BaseModel):
    report_title: str
    generated_at: datetime
    count: int
    data: List[Dict[str, Any]]
    status: int
