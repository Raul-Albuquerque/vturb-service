from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ReportResponse(BaseModel):
    report_title: str
    generated_at: datetime
    count: Optional[int] = None
    status: Optional[int] = None
    data: Optional[Any] = None
    message: Optional[str] = None
