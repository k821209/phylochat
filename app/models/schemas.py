from pydantic import BaseModel


class TreeUploadResponse(BaseModel):
    tree_id: int
    session_id: int
    filename: str
    tip_count: int


class TreeData(BaseModel):
    tree_id: int
    newick: str
    tree_json: dict


class ChatRequest(BaseModel):
    session_id: int
    tree_id: int
    message: str


class ChatResponse(BaseModel):
    message_id: int
    role: str
    content: str
    r_code: str | None = None
    render_url: str | None = None


class RenderRequest(BaseModel):
    tree_id: int
    r_code: str


class RenderResponse(BaseModel):
    render_url: str
    r_code: str


class ExportRequest(BaseModel):
    tree_id: int
    format: str = "png"
    dpi: int = 300
