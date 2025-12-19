"""LLM 服务模块"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
from loguru import logger


@dataclass
class LLMConfig:
    """LLM 配置"""
    enabled: bool = False
    api_url: str = ""
    api_token: str = ""
    model: str = ""
    prompt: str = ""
    timeout: int = 60


@dataclass
class LLMResponse:
    """LLM 响应"""
    success: bool
    content: str = ""
    error: str = ""


class LLMService:
    """
    LLM 服务
    
    提供与 LLM API 的交互功能，支持冷却时间控制
    """
    
    COOLDOWN_SECONDS = 300  # 5分钟冷却
    
    def __init__(self, config: LLMConfig):
        self.config = config
        # 用户冷却记录: {user_id: datetime}
        self._cooldowns: dict[str, datetime] = {}
    
    @property
    def enabled(self) -> bool:
        """服务是否启用"""
        return self.config.enabled and bool(self.config.api_url)
    
    def get_cooldown_remaining(self, user_id: str) -> int:
        """
        获取用户剩余冷却时间（秒）
        
        Returns:
            剩余秒数，0表示无冷却
        """
        if user_id not in self._cooldowns:
            return 0
        
        expire_time = self._cooldowns[user_id]
        now = datetime.now()
        
        if now >= expire_time:
            del self._cooldowns[user_id]
            return 0
        
        return int((expire_time - now).total_seconds())
    
    def is_on_cooldown(self, user_id: str) -> bool:
        """检查用户是否在冷却中"""
        return self.get_cooldown_remaining(user_id) > 0
    
    def set_cooldown(self, user_id: str):
        """设置用户冷却"""
        self._cooldowns[user_id] = datetime.now() + timedelta(seconds=self.COOLDOWN_SECONDS)
    
    def clear_cooldown(self, user_id: str):
        """清除用户冷却（管理员用）"""
        self._cooldowns.pop(user_id, None)
    
    async def generate(self, prompt: str, user_id: str) -> LLMResponse:
        """
        调用 LLM 生成内容
        
        Args:
            prompt: 提示词
            user_id: 用户ID（用于冷却控制）
        
        Returns:
            LLMResponse
        """
        if not self.enabled:
            return LLMResponse(success=False, error="LLM 服务未启用")
        
        # 检查冷却
        remaining = self.get_cooldown_remaining(user_id)
        if remaining > 0:
            minutes = remaining // 60
            seconds = remaining % 60
            return LLMResponse(
                success=False, 
                error=f"请求冷却中，请等待 {minutes}分{seconds}秒"
            )
        
        # 设置冷却（无论成功失败）
        self.set_cooldown(user_id)
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.config.api_token}"
                }
                
                payload = {
                    "model": self.config.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False
                }
                
                # 构建完整URL，避免重复路径
                api_url = self.config.api_url.rstrip("/")
                if not api_url.endswith("/chat/completions"):
                    api_url = f"{api_url}/chat/completions"
                
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"LLM API 错误: {response.status_code} - {response.text}")
                    return LLMResponse(
                        success=False, 
                        error=f"API 请求失败: {response.status_code}"
                    )
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not content:
                    return LLMResponse(success=False, error="API 返回内容为空")
                
                logger.info(f"LLM 生成成功: user={user_id}, length={len(content)}")
                return LLMResponse(success=True, content=content)
                
        except httpx.TimeoutException:
            logger.error(f"LLM API 超时: user={user_id}")
            return LLMResponse(success=False, error="请求超时，请稍后重试")
        except Exception as e:
            logger.error(f"LLM API 异常: {e}")
            return LLMResponse(success=False, error=f"请求异常: {str(e)}")
    
    def build_backstory_prompt(self, char_info: dict) -> str:
        """
        构建角色背景故事生成的提示词
        
        Args:
            char_info: 角色信息字典
        
        Returns:
            完整的提示词
        """
        # 基础信息
        name = char_info.get("name", "未知")
        age = char_info.get("age", "未知")
        gender = char_info.get("gender", "未知")
        nationality = char_info.get("nationality", "未知")
        occupation = char_info.get("occupation", "未知")
        era = char_info.get("era", "")
        
        # 属性
        attributes = char_info.get("attributes", {})
        attr_desc = self._describe_attributes(attributes)
        
        # 技能
        skills = char_info.get("skills", {})
        skill_desc = self._describe_skills(skills)
        
        # 背景故事元素
        backstory = char_info.get("backstory", {})
        
        # 构建提示词
        base_prompt = self.config.prompt or self._default_prompt()
        
        # 年代信息
        era_info = f"- 年代: {era}" if era else ""
        
        prompt = f"""{base_prompt}

## 角色基本信息
- 姓名: {name}
- 年龄: {age}
- 性别: {gender}
- 国籍: {nationality}
- 职业: {occupation}
{era_info}

## 属性特点
{attr_desc}

## 技能特长
{skill_desc}

## 背景故事要素
- 形象描述: {backstory.get('appearance', '未填写')}
- 思想与信念: {backstory.get('ideology', '未填写')}
- 重要之人: {backstory.get('significant_people', '未填写')}
- 意义非凡之地: {backstory.get('meaningful_locations', '未填写')}
- 宝贵之物: {backstory.get('treasured_possessions', '未填写')}
- 特质: {backstory.get('traits', '未填写')}
- 伤口和伤疤: {backstory.get('injuries', '未填写')}
- 恐惧症和躁狂症: {backstory.get('phobias', '未填写')}

请根据以上信息，生成一段详细的角色背景故事。"""
        
        return prompt
    
    def _default_prompt(self) -> str:
        """默认提示词"""
        return """你是一个克苏鲁的呼唤(COC)跑团游戏的角色背景故事生成器。
请根据提供的角色信息，生成一段合理、有趣且符合COC世界观的详细背景故事。

要求：
1. 根据角色年龄生成符合人生阶段的故事（年轻人侧重成长经历，中年人侧重职业发展，老年人侧重人生阅历）
2. 自然地融入角色的技能特长，但绝对不要在文中标注技能数值或百分比
3. 解释角色如何获得其职业和能力
4. 描述与重要之人的关系
5. 说明角色的性格特点形成原因
6. 如有伤疤或恐惧症，解释其来源
7. 保持符合设定年代的时代感
8. 字数在500-800字之间
9. 使用流畅的叙事文风，避免列表式描述"""
    
    def _describe_attributes(self, attrs: dict) -> str:
        """描述属性特点"""
        descriptions = []
        
        attr_names = {
            "STR": "力量", "CON": "体质", "SIZ": "体型",
            "DEX": "敏捷", "APP": "外貌", "INT": "智力",
            "POW": "意志", "EDU": "教育", "LUK": "幸运"
        }
        
        for key, name in attr_names.items():
            value = attrs.get(key, 50)
            if value < 20:
                descriptions.append(f"- {name}({value}): 明显缺陷")
            elif value >= 90:
                descriptions.append(f"- {name}({value}): 接近人类极限")
            elif value >= 75:
                descriptions.append(f"- {name}({value}): 非常出色")
            elif value >= 60:
                descriptions.append(f"- {name}({value}): 高于平均")
            elif value < 40:
                descriptions.append(f"- {name}({value}): 低于平均")
        
        return "\n".join(descriptions) if descriptions else "属性均为普通水平"
    
    def _describe_skills(self, skills: dict) -> str:
        """描述技能特长"""
        descriptions = []
        
        for skill, value in skills.items():
            if value >= 90:
                descriptions.append(f"- {skill}({value}): 大师级")
            elif value >= 75:
                descriptions.append(f"- {skill}({value}): 专家级")
            elif value >= 50:
                descriptions.append(f"- {skill}({value}): 职业级")
            elif value >= 20:
                descriptions.append(f"- {skill}({value}): 业余水平")
        
        # 只返回较高技能
        high_skills = [d for d in descriptions if "大师" in d or "专家" in d or "职业" in d]
        return "\n".join(high_skills[:10]) if high_skills else "无特别突出的技能"


# 全局实例（延迟初始化）
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    global _llm_service
    if _llm_service is None:
        from ..config import settings
        config = LLMConfig(
            enabled=settings.llm_service,
            api_url=settings.llm_api_url,
            api_token=settings.llm_api_token,
            model=settings.llm_model,
            prompt=settings.llm_prompt,
        )
        _llm_service = LLMService(config)
    return _llm_service


def init_llm_service(config: LLMConfig) -> LLMService:
    """初始化 LLM 服务（用于自定义配置）"""
    global _llm_service
    _llm_service = LLMService(config)
    return _llm_service
