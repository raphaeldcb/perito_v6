from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import ToolCreate, ToolRead, ToolUpdate
from app.models import Tool, User
from app.services import get_db
from app.middleware import get_current_user

router = APIRouter()


@router.get("", response_model=list[ToolRead])
async def list_tools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tools accessible to current user (public + user roles)"""
    if current_user:
        tools = db.query(Tool).filter(
            (Tool.access_level == "public") |
            (Tool.access_level == "user") |
            (Tool.access_level == current_user.role.name)
        ).filter(Tool.is_active).all()
    else:
        tools = db.query(Tool).filter(
            Tool.access_level == "public",
            Tool.is_active
        ).all()
    return tools


@router.get("/{tool_id}", response_model=ToolRead)
async def get_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if tool.access_level == "public" or (current_user and tool.access_level in ["user", current_user.role.name]):
        return tool

    raise HTTPException(status_code=403, detail="Not authorized")


@router.post("", response_model=ToolRead)
async def create_tool(
    tool_data: ToolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create tools")

    if db.query(Tool).filter(Tool.name == tool_data.name).first():
        raise HTTPException(status_code=400, detail="Tool name already exists")

    new_tool = Tool(**tool_data.dict())
    db.add(new_tool)
    db.commit()
    db.refresh(new_tool)
    return new_tool


@router.patch("/{tool_id}", response_model=ToolRead)
async def update_tool(
    tool_id: int,
    tool_data: ToolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update tools")

    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    for key, value in tool_data.dict(exclude_unset=True).items():
        setattr(tool, key, value)

    db.commit()
    db.refresh(tool)
    return tool


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete tools")

    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    db.delete(tool)
    db.commit()
    return {"message": "Tool deleted"}
