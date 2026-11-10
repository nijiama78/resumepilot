"""简历分析引擎。

两条路径：
1. 配置了 LLM_API_KEY 时，优先调用大模型（OpenAI 兼容接口）分析；
2. 未配置或调用失败时，回退到内置规则引擎（ATS 启发式评分），
   保证应用在没有 API Key 的情况下也能完整运行。
"""
import json
import re

from .config import settings

# 技术关键词库：用于 JD 匹配维度的计算
TECH_KEYWORDS = [
    # 语言
    "python", "java", "golang", "go", "c++", "c#", "javascript", "typescript",
    "rust", "php", "ruby", "swift", "kotlin",
    # 前端
    "react", "vue", "angular", "next.js", "nuxt", "vite", "webpack",
    "html", "css", "tailwind", "element", "antd",
    # 后端 / 框架
    "node", "express", "nestjs", "fastapi", "django", "flask", "spring",
    "springboot", "spring boot", "mybatis", "gin",
    # 数据 / 存储
    "mysql", "postgresql", "oracle", "sqlserver", "redis", "mongodb",
    "elasticsearch", "kafka", "rabbitmq", "sqlite",
    # 运维 / 云
    "docker", "kubernetes", "k8s", "linux", "nginx", "git", "ci/cd",
    "aws", "azure", "gcp", "阿里云", "腾讯云",
    # 计算机基础 / AI
    "算法", "数据结构", "操作系统", "计算机网络", "设计模式",
    "机器学习", "深度学习", "nlp", "cv", "llm", "rag", "agent",
    "微服务", "分布式", "高并发", "性能优化", "前端", "后端", "全栈",
]

ACTION_VERBS = [
    "负责", "主导", "设计", "实现", "开发", "搭建", "构建", "优化",
    "改进", "提升", "降低", "减少", "完成", "交付", "推动", "独立",
    "从零", "落地", "重构", "封装", "维护", "管理",
]

WEAK_WORDS = ["参与", "了解", "熟悉", "协助", "做过", "用过"]


def _grade(score: int) -> str:
    if score >= 85:
        return "优秀"
    if score >= 70:
        return "良好"
    if score >= 55:
        return "一般"
    return "需要较大改进"


def analyze_with_rules(resume_text: str, job_description: str) -> dict:
    """基于 ATS 筛选逻辑的启发式评分（无 LLM 时兜底）。"""
    text = resume_text.lower()
    suggestions: list[str] = []
    dimensions: dict[str, dict] = {}

    # 1. 联系方式完整度（10 分）
    has_email = bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text))
    has_phone = bool(re.search(r"1[3-9]\d{9}", text))
    contact_score = (5 if has_email else 0) + (5 if has_phone else 0)
    dimensions["contact"] = {"label": "联系方式完整度", "score": contact_score, "max": 10}
    if not has_email:
        suggestions.append("未检测到邮箱地址，HR 无法联系你——这是硬性扣分项")
    if not has_phone:
        suggestions.append("未检测到手机号，建议在简历顶部补充联系方式")

    # 2. 内容充实度 / 篇幅（15 分）
    length = len(resume_text)
    if 500 <= length <= 5000:
        length_score = 15
    elif 300 <= length < 500:
        length_score = 9
        suggestions.append("简历内容偏少（可能缺少项目/实习经历的展开描述）")
    elif length > 5000:
        length_score = 9
        suggestions.append("简历篇幅过长，建议压缩到 1-2 页，突出核心经历")
    else:
        length_score = 4
        suggestions.append("简历内容过少，需要补充教育背景、项目经历等模块")
    dimensions["length"] = {"label": "内容充实度", "score": length_score, "max": 15}

    # 3. 量化成果（20 分）
    numbers = re.findall(r"\d+\s*%|\d+\s*万|\d+\s*千|\d+\s*\+|\d+\.\d+", text)
    if len(numbers) >= 5:
        quant_score = 20
    elif len(numbers) >= 3:
        quant_score = 15
        suggestions.append("有一定量化数据，但还可以更多：性能提升、用户量、成本降低都是好素材")
    elif len(numbers) >= 1:
        quant_score = 8
        suggestions.append("量化成果不足。把'提升了性能'改成'接口响应时间从 800ms 降到 200ms'这类具体数字")
    else:
        quant_score = 2
        suggestions.append("完全没有量化数据——这是简历最常见的问题，每条经历尽量给出数字成果")
    dimensions["quantification"] = {
        "label": "量化成果",
        "score": quant_score,
        "max": 20,
        "detail": f"检测到 {len(numbers)} 处量化数据",
    }

    # 4. 岗位关键词匹配（40 分）
    jd_lower = job_description.lower()
    jd_keywords = [k for k in TECH_KEYWORDS if k in jd_lower]
    if jd_keywords:
        matched = [k for k in jd_keywords if k in text]
        missing = [k for k in jd_keywords if k not in text]
        ratio = len(matched) / len(jd_keywords)
        jd_score = round(ratio * 40)
        if missing:
            suggestions.append(
                f"岗位 JD 要求但简历未体现的关键词：{'、'.join(missing[:8])}"
                f"{'等' if len(missing) > 8 else ''}——如确实掌握请补充到技能或项目描述中"
            )
    else:
        # 未提供 JD：检查简历自身技术关键词密度
        resume_keywords = [k for k in TECH_KEYWORDS if k in text]
        matched, missing = resume_keywords, []
        jd_score = min(28, 4 * len(resume_keywords))
        if len(resume_keywords) < 6:
            suggestions.append("技术关键词偏少，建议在技能栏明确列出技术栈（如 Python、FastAPI、MySQL）")
    dimensions["jd_match"] = {
        "label": "岗位关键词匹配",
        "score": jd_score,
        "max": 40,
        "detail": f"匹配 {len(matched)} 个关键词",
    }

    # 5. 行为动词与弱词（15 分）
    verb_hits = sum(1 for v in ACTION_VERBS if v in text)
    weak_hits = sum(1 for w in WEAK_WORDS if w in text)
    verb_score = min(15, verb_hits * 3)
    dimensions["action_verbs"] = {
        "label": "行为动词使用",
        "score": verb_score,
        "max": 15,
        "detail": f"强动词 {verb_hits} 个 / 弱词 {weak_hits} 个",
    }
    if weak_hits > verb_hits:
        suggestions.append("弱词（参与/了解/熟悉）过多，把'参与开发'改为'负责 XX 模块的开发与上线'")
    if verb_hits == 0:
        suggestions.append("缺少行为动词（主导/设计/实现/优化），经历描述无法体现你的主动性和产出")

    total = sum(d["score"] for d in dimensions.values())
    summary = (
        f"简历整体质量「{_grade(total)}」（{total}/100）。"
        f"关键词匹配 {len(matched)} 个，量化数据 {len(numbers)} 处，"
        f"{'与目标岗位匹配度较好' if jd_keywords and total >= 60 else '仍有明显提升空间'}。"
    )
    return {
        "score": total,
        "summary": summary,
        "dimensions": dimensions,
        "suggestions": suggestions,
        "matched_keywords": matched[:20],
        "missing_keywords": missing[:20],
    }


def analyze_with_llm(resume_text: str, job_description: str) -> dict:
    """调用 OpenAI 兼容接口进行 AI 分析。失败时抛异常，由调用方回退规则引擎。"""
    import httpx

    prompt = f"""你是一位资深 HR 和技术面试官。请分析下面的简历{f'，并与目标岗位 JD 对比' if job_description else ''}。

要求：以 JSON 返回，结构如下：
{{"score": 0-100 的总分, "summary": "一句话总体评价",
"dimensions": {{"contact": {{"label": "联系方式完整度", "score": 0-10, "max": 10}},
"length": {{"label": "内容充实度", "score": 0-15, "max": 15}},
"quantification": {{"label": "量化成果", "score": 0-20, "max": 20}},
"jd_match": {{"label": "岗位关键词匹配", "score": 0-40, "max": 40}},
"action_verbs": {{"label": "行为动词使用", "score": 0-15, "max": 15}}}},
"suggestions": ["最多5条具体可执行的修改建议"],
"matched_keywords": ["匹配到的关键词"], "missing_keywords": ["缺失的关键词"]}}

### 简历内容
{resume_text[:6000]}

### 岗位 JD
{job_description[:3000] if job_description else '（未提供）'}
"""
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            json={
                "model": settings.LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    result = json.loads(content)
    # 保证引擎输出包含必需字段
    result.setdefault("matched_keywords", [])
    result.setdefault("missing_keywords", [])
    result.setdefault("suggestions", [])
    result.setdefault("dimensions", {})
    return result


def analyze(resume_text: str, job_description: str) -> tuple[dict, str]:
    """统一入口：返回 (结果 dict, 引擎名)。"""
    if settings.LLM_API_KEY:
        try:
            return analyze_with_llm(resume_text, job_description), "llm"
        except Exception:
            pass  # 任何 LLM 失败都静默回退规则引擎，保证可用性
    return analyze_with_rules(resume_text, job_description), "rule"
