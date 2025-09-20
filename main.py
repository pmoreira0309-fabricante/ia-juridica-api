import os
from fastapi import FastAPI, Header, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

API_KEY = os.getenv("API_BEARER", "changeme")
app = FastAPI(title="IA Jurídica Trabalhista – API", version="1.0.0")

class Case(BaseModel):
    id: str
    title: str
    matter: Optional[str] = "Direito do Trabalho"
    notes: Optional[str] = None

class DocumentInput(BaseModel):
    type: str = Field(..., pattern="^(peticao_inicial|contestacao|sentenca|ed|ro|acordao|rr|airr|ai|edtst|rext|ap|outro)$")
    filename: Optional[str] = None
    content: str
    encoding: Optional[str] = Field(default="plain", pattern="^(plain|base64)$")

class AnalysisRequest(BaseModel):
    format: Optional[str] = Field(default="markdown", pattern="^(markdown|json)$")
    includeCitations: Optional[bool] = True
    sections: Optional[List[str]] = ["resumo","pedidos_decisoes","fundamentos","analise_critica","recomendacoes"]

class StrategyRequest(BaseModel):
    goal: Optional[str] = None
    deadline: Optional[str] = None
    constraints: Optional[str] = None

class NormaPesquisaRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = ["CLT","CF","SÚMULA_TST","OJ_TST"]
    limit: Optional[int] = 10

class Citation(BaseModel):
    source: str
    identifier: str
    excerpt: Optional[str] = None
    url: Optional[str] = None

class AnalysisResponse(BaseModel):
    caseId: str
    format: str
    output: str
    citations: Optional[List[Citation]] = None

class StrategyResponse(BaseModel):
    caseId: str
    roadmap: str
    risks: List[str] = []
    chances: Optional[str] = None

class SearchResponse(BaseModel):
    items: List[Citation] = []

DB_CASES: Dict[str, Case] = {}
DB_DOCS: Dict[str, List[DocumentInput]] = {}

def check_auth(auth: Optional[str]):
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token ausente")
    token = auth.split(" ", 1)[1].strip()
    if token != API_KEY:
        raise HTTPException(status_code=403, detail="Token inválido")

@app.post("/cases", response_model=Case, status_code=201)
def create_case(payload: dict, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    title = payload.get("title")
    if not title:
        raise HTTPException(400, "title é obrigatório")
    case_id = f"caso_{len(DB_CASES)+1}"
    c = Case(id=case_id, title=title, notes=payload.get("notes"))
    DB_CASES[case_id] = c
    DB_DOCS[case_id] = []
    return c

@app.post("/cases/{caseId}/documents")
def add_documents(caseId: str = Path(...), payload: dict = None, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if caseId not in DB_CASES:
        raise HTTPException(404, "Caso não encontrado")
    docs = [DocumentInput(**d) for d in payload.get("documents", [])]
    DB_DOCS[caseId].extend(docs)
    return {"message": f"{len(docs)} documento(s) anexado(s) ao {caseId}"}

@app.get("/cases/{caseId}", response_model=Case)
def get_case(caseId: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if caseId not in DB_CASES:
        raise HTTPException(404, "Caso não encontrado")
    return DB_CASES[caseId]

@app.post("/cases/{caseId}/analyze", response_model=AnalysisResponse)
def analyze_case(caseId: str, req: AnalysisRequest = AnalysisRequest(), authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if caseId not in DB_CASES:
        raise HTTPException(404, "Caso não encontrado")
    md = (
        "## 1. Resumo Executivo\n"
        "Sentença parcialmente procedente. Horas extras deferidas; insalubridade indeferida.\n\n"
        "## 2. Pedidos x Decisões\n"
        "| Pedido | Resultado | Fundamento |\n|---|---|---|\n"
        "| Horas extras | Parcial | Art. 7º, XVI CF; Art. 59 CLT; Súmula 85/TST |\n"
        "| Insalubridade | Improcedente | Art. 195 CLT |\n\n"
        "## 3. Fundamentos\n- **Art. 59, CLT**...\n- **Súmula 85/TST**...\n\n"
        "## 4. Análise Crítica\nPonto fraco: perícia não requerida oportunamente.\n\n"
        "## 5. Recomendações\nRO com tese de cerceamento (art. 5º, LV, CF) + prequestionar art. 818 CLT."
    )
    citations = [
        Citation(source="CLT", identifier="Art. 59", url="https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm#art59"),
        Citation(source="SÚMULA_TST", identifier="Súmula 85", url="https://www.tst.jus.br/jurisprudencia/sumulas")
    ]
    return AnalysisResponse(caseId=caseId, format=req.format, output=md, citations=citations)

@app.post("/cases/{caseId}/strategy", response_model=StrategyResponse)
def strategy_case(caseId: str, req: StrategyRequest, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if caseId not in DB_CASES:
        raise HTTPException(404, "Caso não encontrado")
    roadmap = (
        "1) RO (art. 5º, LV, CF)\n"
        "2) Prequestionar art. 818 CLT e 373 CPC\n"
        "3) RR c/ transcendência se mantida negativa de perícia"
    )
    return StrategyResponse(caseId=caseId, roadmap=roadmap, risks=["preclusão da perícia"], chances="média-alta")

@app.post("/research/normas", response_model=SearchResponse)
def search_normas(req: NormaPesquisaRequest, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    items = [
        Citation(source="CLT", identifier="Art. 461", excerpt="Sendo idêntica a função...", url="https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm#art461"),
        Citation(source="SÚMULA_TST", identifier="Súmula 6", excerpt="Equiparação salarial...", url="https://www.tst.jus.br/jurisprudencia/sumulas")
    ][: req.limit]
    return SearchResponse(items=items)
