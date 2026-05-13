import json
from typing import Any, Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from llm_module import generate_structured_data, extract_requirement_from_code
from kb_module import get_enhanced_context
from evaluation_module import evaluate_result
from mangum import Mangum  # 新增：导入Serverless适配器

# 数据库知识库相关模块
try:
    from database import Base, engine, SessionLocal
    from knowledge_models import KnowledgeModule
    from seed_common_knowledge import seed_common_knowledge
    DATABASE_AVAILABLE = True
except Exception:
    Base = None
    engine = None
    SessionLocal = None
    KnowledgeModule = None
    DATABASE_AVAILABLE = False

# 用户故事相关代码生成模块
try:
    from code_module import generate_related_code
    CODE_GENERATION_AVAILABLE = True
except Exception:
    generate_related_code = None
    CODE_GENERATION_AVAILABLE = False

app = FastAPI(
    title="智能用户故事生成系统",
    description="基于大语言模型与数据库知识库的需求解析、用户故事生成、任务拆解、代码生成与实验评估系统",
    version="2.0.0",
    root_path="/api"  # 新增：匹配EdgeOne反向代理路径前缀
)

# 配置CORS（通过EdgeOne反向代理后可直接注释掉，彻底避免跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 移除：静态文件挂载（前端单独部署到EdgeOne）
# app.mount("/", StaticFiles(directory="dist", html=True), name="static")

class RequirementRequest(BaseModel):
    requirement: str = Field(..., description="单条自然语言需求文本")

class BatchRequirementRequest(BaseModel):
    requirements: List[str] = Field(..., description="多条自然语言需求文本列表")

class CodeRequirementRequest(BaseModel):
    code: str = Field(..., description="代码文本（支持多语言，建议单段完整代码）")

class KnowledgeModuleRequest(BaseModel):
    module_name: str = Field(..., description="知识模块名称")
    category: str = Field("通用软件模块", description="模块分类")
    aliases: List[str] = Field(default_factory=list, description="模块别名")
    required_elements: List[str] = Field(default_factory=list, description="必选要素")
    preconditions: List[str] = Field(default_factory=list, description="前置条件")
    exception_scenarios: List[str] = Field(default_factory=list, description="异常场景")
    typical_tasks: List[str] = Field(default_factory=list, description="典型任务")
    security_constraints: str = Field("", description="安全约束")
    description: str = Field("", description="模块说明")

class CodeGenerateRequest(BaseModel):
    requirement: str = Field("", description="原始自然语言需求")
    story: str = Field(..., description="选中的用户故事")
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="该用户故事对应的任务列表")

def success_response(data: Any, message: str = "操作成功") -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data
    }

def error_response(message: str = "操作失败", data: Any = None) -> Dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": data
    }

def dumps_list(value: List[str]) -> str:
    return json.dumps(value or [], ensure_ascii=False)

def loads_list(value: str) -> List[str]:
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []

def knowledge_row_to_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": row.id,
        "module_name": row.module_name,
        "category": row.category,
        "aliases": loads_list(row.aliases),
        "required_elements": loads_list(row.required_elements),
        "preconditions": loads_list(row.preconditions),
        "exception_scenarios": loads_list(row.exception_scenarios),
        "typical_tasks": loads_list(row.typical_tasks),
        "security_constraints": row.security_constraints or "",
        "description": row.description or "",
        "is_builtin": row.is_builtin
    }

@app.on_event("startup")
def startup_event():
    """系统启动时初始化数据库表结构"""
    if DATABASE_AVAILABLE:
        Base.metadata.create_all(bind=engine)

@app.get("/health")
def health_check():
    return success_response(
        {
            "service": "智能用户故事生成系统后端",
            "status": "running",
            "database_available": DATABASE_AVAILABLE,
            "code_generation_available": CODE_GENERATION_AVAILABLE
        },
        "服务运行正常"
    )

@app.get("/knowledge_modules")
def list_knowledge_modules():
    if not DATABASE_AVAILABLE:
        return error_response("数据库知识库模块未启用，请检查 database.py、knowledge_models.py 和 seed_common_knowledge.py")
    db = SessionLocal()
    try:
        rows = db.query(KnowledgeModule).order_by(KnowledgeModule.id.asc()).all()
        modules = [knowledge_row_to_dict(row) for row in rows]
        return success_response(
            {
                "total": len(modules),
                "modules": modules
            },
            "知识库模块查询成功"
        )
    finally:
        db.close()

@app.post("/knowledge_modules")
def create_knowledge_module(req: KnowledgeModuleRequest):
    if not DATABASE_AVAILABLE:
        return error_response("数据库知识库模块未启用，请检查 database.py、knowledge_models.py 和 seed_common_knowledge.py")
    module_name = req.module_name.strip()
    if not module_name:
        return error_response("模块名称不能为空")
    db = SessionLocal()
    try:
        exists = db.query(KnowledgeModule).filter(
            KnowledgeModule.module_name == module_name
        ).first()
        if exists:
            return error_response("该知识模块已存在")
        module = KnowledgeModule(
            module_name=module_name,
            category=req.category.strip() or "通用软件模块",
            aliases=dumps_list(req.aliases),
            required_elements=dumps_list(req.required_elements),
            preconditions=dumps_list(req.preconditions),
            exception_scenarios=dumps_list(req.exception_scenarios),
            typical_tasks=dumps_list(req.typical_tasks),
            security_constraints=req.security_constraints.strip(),
            description=req.description.strip(),
            is_builtin=False
        )
        db.add(module)
        db.commit()
        db.refresh(module)
        return success_response(
            knowledge_row_to_dict(module),
            "知识库模块新增成功"
        )
    finally:
        db.close()

@app.post("/preview_context")
def preview_context(req: RequirementRequest):
    requirement = req.requirement.strip()
    if not requirement:
        return error_response("需求文本不能为空")
    try:
        context = get_enhanced_context(requirement)
        return success_response(
            {
                "requirement": requirement,
                "knowledge_context": context
            },
            "知识增强上下文获取成功"
        )
    except Exception as e:
        return error_response(f"知识增强处理异常: {str(e)}")

@app.post("/generate_story")
def generate_story_endpoint(req: RequirementRequest):
    requirement = req.requirement.strip()
    if not requirement:
        return error_response("需求文本不能为空")
    try:
        context = get_enhanced_context(requirement)
        result = generate_structured_data(requirement, context)
        if result.get("error"):
            return error_response(
                message=result["error"],
                data={
                    "requirement": requirement,
                    "knowledge_context": context,
                    "result": result
                }
            )
        return success_response(
            {
                "requirement": requirement,
                "knowledge_context": context,
                "result": result
            },
            "用户故事与任务拆解生成成功"
        )
    except Exception as e:
        return error_response(f"后端处理异常: {str(e)}")

@app.post("/generate_batch")
def generate_batch_endpoint(req: BatchRequirementRequest):
    requirements = [
        item.strip()
        for item in req.requirements
        if item and item.strip()
    ]
    if not requirements:
        return error_response("批量需求文本不能为空")
    batch_results = []
    for index, requirement in enumerate(requirements, start=1):
        try:
            context = get_enhanced_context(requirement)
            result = generate_structured_data(requirement, context)
            is_success = not bool(result.get("error"))
            batch_results.append(
                {
                    "index": index,
                    "requirement": requirement,
                    "knowledge_context": context,
                    "result": result,
                    "success": is_success,
                    "error": result.get("error", "")
                }
            )
        except Exception as e:
            batch_results.append(
                {
                    "index": index,
                    "requirement": requirement,
                    "knowledge_context": "",
                    "result": None,
                    "success": False,
                    "error": f"第{index}条需求处理异常: {str(e)}"
                }
            )
    success_count = sum(1 for item in batch_results if item["success"])
    fail_count = len(batch_results) - success_count
    return success_response(
        {
            "total": len(batch_results),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": batch_results
        },
        "批量用户故事生成完成"
    )

@app.post("/generate_and_evaluate")
def generate_and_evaluate(req: RequirementRequest):
    requirement = req.requirement.strip()
    if not requirement:
        return error_response("需求文本不能为空")
    try:
        context = get_enhanced_context(requirement)
        result = generate_structured_data(requirement, context)
        if result.get("error"):
            return error_response(
                message=result["error"],
                data={
                    "requirement": requirement,
                    "knowledge_context": context,
                    "result": result,
                    "evaluation": None
                }
            )
        evaluation = evaluate_result(result)
        return success_response(
            {
                "requirement": requirement,
                "knowledge_context": context,
                "result": result,
                "evaluation": evaluation
            },
            "生成与评估完成"
        )
    except Exception as e:
        return error_response(f"后端处理异常: {str(e)}")

@app.post("/generate_story_from_code")
def generate_story_from_code(req: CodeRequirementRequest):
    code = req.code.strip()
    if not code:
        return error_response("代码文本不能为空")
    try:
        extracted_req = extract_requirement_from_code(code)
        if not extracted_req:
            return error_response("未能从代码中提取到有效需求描述")
        context = get_enhanced_context(extracted_req)
        result = generate_structured_data(extracted_req, context)
        if result.get("error"):
            return error_response(
                message=result["error"],
                data={
                    "extracted_requirement": extracted_req,
                    "knowledge_context": context,
                    "result": result,
                    "evaluation": None
                }
            )
        evaluation = evaluate_result(result)
        return success_response(
            {
                "extracted_requirement": extracted_req,
                "knowledge_context": context,
                "result": result,
                "evaluation": evaluation
            },
            "代码成功解析并生成用户故事"
        )
    except Exception as e:
        return error_response(f"代码分析异常: {str(e)}")

@app.post("/generate_code")
def generate_code_endpoint(req: CodeGenerateRequest):
    if not CODE_GENERATION_AVAILABLE:
        return error_response("代码生成模块未启用，请检查 code_module.py 是否存在并能正常导入")
    story = req.story.strip()
    if not story:
        return error_response("用户故事不能为空")
    try:
        code_result = generate_related_code(
            requirement=req.requirement.strip(),
            story=story,
            tasks=req.tasks
        )
        if code_result.get("error"):
            return error_response(
                message=code_result["error"],
                data={
                    "story": story,
                    "tasks": req.tasks,
                    "code_result": code_result
                }
            )
        return success_response(
            {
                "story": story,
                "tasks": req.tasks,
                "code_result": code_result
            },
            "相关代码生成成功"
        )
    except Exception as e:
        return error_response(f"代码生成接口异常: {str(e)}")

# 新增：CloudBase云函数入口
handler = Mangum(app)