from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.api.schemas import ChatInput, EventInput
from app.memory.database import MemoryDatabase
from app.services.event_planner import EventRequest, create_event_plan

router = APIRouter()
database = MemoryDatabase()

def _row_event(row):
    return dict(row) if row else None

@router.post("/events", status_code=201)
def create_event(payload: EventInput):
    data = payload.model_dump()
    user_id = data.pop("user_id")
    request = EventRequest(**data)
    try:
        create_event_plan(request)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with database.connection() as conn:
            cur = conn.execute("""INSERT INTO planned_events(user_id,name,event_type,event_date,location,guest_count,budget,food_preference,decoration_style,general_preferences,additional_requirements,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (user_id,request.name,request.event_type,request.event_date.isoformat(),request.location,request.guest_count,request.budget,request.food_preference,request.decoration_style,request.preferences,request.additional_requirements,now))
            return {"event_id":cur.lastrowid,"user_id":user_id,**data,"created_at":now}
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@router.get("/events")
def list_events(user_id: str = "local-user", limit: int = Query(50, ge=1, le=100)):
    with database.connection() as conn:
        rows=conn.execute("SELECT * FROM planned_events WHERE user_id=? ORDER BY id DESC LIMIT ?",(user_id,limit)).fetchall()
    return [dict(row) for row in rows]

@router.get("/events/{event_id}")
def get_event(event_id:int):
    with database.connection() as conn: row=conn.execute("SELECT * FROM planned_events WHERE id=?",(event_id,)).fetchone()
    if row is None: raise HTTPException(404,"Event not found")
    return dict(row)

@router.put("/events/{event_id}")
def update_event(event_id:int,payload:EventInput):
    data=payload.model_dump(); user_id=data.pop("user_id")
    request=EventRequest(**data)
    try: create_event_plan(request)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    with database.connection() as conn:
        cur=conn.execute("""UPDATE planned_events SET name=?,event_type=?,event_date=?,location=?,guest_count=?,budget=?,food_preference=?,decoration_style=?,general_preferences=?,additional_requirements=? WHERE id=? AND user_id=?""",(request.name,request.event_type,request.event_date.isoformat(),request.location,request.guest_count,request.budget,request.food_preference,request.decoration_style,request.preferences,request.additional_requirements,event_id,user_id))
        if not cur.rowcount: raise HTTPException(404,"Event not found")
    return {"event_id":event_id,"user_id":user_id,**data}

@router.delete("/events/{event_id}",status_code=204)
def delete_event(event_id:int,user_id:str="local-user"):
    with database.connection() as conn: cur=conn.execute("DELETE FROM planned_events WHERE id=? AND user_id=?",(event_id,user_id))
    if not cur.rowcount: raise HTTPException(404,"Event not found")

@router.post("/events/{event_id}/plan")
def plan_event(event_id:int):
    event=get_event(event_id)
    req=EventRequest(name=event['name'],event_type=event['event_type'],event_date=date.fromisoformat(event['event_date']),location=event['location'],guest_count=event['guest_count'],budget=event['budget'],preferences=event['general_preferences'],food_preference=event['food_preference'],decoration_style=event['decoration_style'])
    plan=create_event_plan(req)
    return {"summary":plan.final_summary,"budget":[x.__dict__ for x in plan.budget],"schedule":[x.__dict__ for x in plan.schedule],"venues":[x.__dict__ for x in plan.venues]}

@router.post("/documents/upload",status_code=201)
async def upload_document(file:UploadFile=File(...)):
    from app.rag.document_loader import extract_text_bytes
    from app.rag.chunking import split_text
    from app.rag.vector_store import EventVectorStore
    if not file.filename: raise HTTPException(400,"Filename is required")
    try:
        text=extract_text_bytes(Path(file.filename).name,await file.read())
        count=EventVectorStore().add_document(file.filename,split_text(text))
        return {"filename":file.filename,"chunks_indexed":count}
    except (ValueError,RuntimeError) as exc: raise HTTPException(422,str(exc)) from exc

@router.post("/chat")
def chat(payload:ChatInput):
    from app.rag.retriever import answer_from_documents
    try:
        answer,sources=answer_from_documents(payload.question)
        return {"answer":answer,"sources":sorted({x['source'] for x in sources})}
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
