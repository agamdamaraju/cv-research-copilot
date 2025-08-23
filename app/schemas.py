from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class IngestResponse(BaseModel):
    doc_id: str
    pages: int

class AskRequest(BaseModel):
    doc_id: str
    question: str

class AskResponse(BaseModel):
    answer: str  # contains [p:##] citations

class ExtractRequest(BaseModel):
    doc_id: str

class Metric(BaseModel):
    dataset: str
    metric: str
    value: float
    page: int = Field(ge=1)

class PaperJSON(BaseModel):
    title: str
    tasks: List[str] = []
    methods: List[dict] = []
    datasets: List[dict] = []
    metrics: List[Metric] = []
    ablations: List[dict] = []

class ExtractResponse(BaseModel):
    data: PaperJSON