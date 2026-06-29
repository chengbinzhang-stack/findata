from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import date
from enum import Enum


class Quarter(str, Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


class DocumentType(str, Enum):
    EARNINGS_CALL_TRANSCRIPT = "EarningsCallTranscript"
    INVESTOR_PRESENTATION = "InvestorPresentation"
    FINANCIAL_RESULTS = "FinancialResults"
    EARNINGS_CALL_AUDIO = "EarningsCallAudio"


class CompanyInfo(BaseModel):
    company_name: str
    bse_scrip_code: str


class DocumentUrl(BaseModel):
    url: Optional[str] = None
    event_date: Optional[date] = None


class SubmitRequest(BaseModel):
    company_name: str
    bse_scrip_code: str
    fy: str
    quarter: Quarter
    earnings_transcript_url: Optional[str] = None
    earnings_transcript_date: Optional[date] = None
    investor_presentation_url: Optional[str] = None
    investor_presentation_date: Optional[date] = None
    financial_results_url: Optional[str] = None
    financial_results_date: Optional[date] = None
    earnings_audio_url: Optional[str] = None
    earnings_audio_date: Optional[date] = None


class TaskStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadTask(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    files: dict[str, dict] = {}


class ValidateUrlResponse(BaseModel):
    valid: bool
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None