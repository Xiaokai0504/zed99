import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import json
from typing import Any, Dict, List
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from llm_module import generate_structured_data, extract_requirement_from_code
from kb_module import get_enhanced_context
from evaluation_module import evaluate_result
from mangum import Mangum

# 代码生成模块（可选，保留）
try:
    from code_module import generate_related_code
    CODE_GENERATION_AVAILABLE = True
except Exception:
    generate_related_code = None
    CODE_GENERATION_AVAILABLE = False

app = FastAPI(
    title="智能用户故事生成系统（无数据库版）",
    description="基于大语言模型的需求解析、用户故事生成、任务拆解、代码生成与实验评估系统",
    version="2.0.0"
)

api_router = APIRouter()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequirementRequest(BaseModel):
    requirement: str = Field(..., description="单条自然语言需求文本")

class BatchRequirementRequest(BaseModel):
    requirements: List[str] = Field(..., description="多条自然语言需求文本列表")

class CodeRequirementRequest(BaseModel):
    code: str = Field(..., description="代码文本（支持多语言，建议单段完整代码）")

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

@api_router.get("/health")
def health_check():
    return success_response(
        {
            "service": "智能用户故事生成系统后端",
            "status": "running",
            "database_available": False,
            "code_generation_available": CODE_GENERATION_AVAILABLE
        },
        "服务运行正常"
    )

@api_router.post("/preview_context")
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

@api_router.post("/generate_story")
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

@api_router.post("/generate_batch")
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

@api_router.post("/generate_and_evaluate")
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

@api_router.post("/generate_story_from_code")
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

@api_router.post("/generate_code")
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

app.include_router(api_router)
app.include_router(api_router, prefix="/api")

# CloudBase云函数入口
def handler(event, context):
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
    return handler(event, context)