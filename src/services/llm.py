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
    
    DEFAULT_COOLDOWN_SECONDS = 300  # 默认5分钟冷却
    
    def __init__(self, config: LLMConfig):
        self.config = config
        # 用户冷却记录: {user_id: datetime}
        self._cooldowns: dict[str, datetime] = {}
        # 可调整的冷却时间
        self._cooldown_seconds: int = self.DEFAULT_COOLDOWN_SECONDS
    
    @property
    def cooldown_seconds(self) -> int:
        """获取当前冷却时间（秒）"""
        return self._cooldown_seconds
    
    @cooldown_seconds.setter
    def cooldown_seconds(self, value: int):
        """设置冷却时间（秒）"""
        self._cooldown_seconds = max(0, value)  # 不允许负数
    
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
        self._cooldowns[user_id] = datetime.now() + timedelta(seconds=self._cooldown_seconds)
    
    def clear_cooldown(self, user_id: str):
        """清除用户冷却（管理员用）"""
        self._cooldowns.pop(user_id, None)
    
    def clear_all_cooldowns(self):
        """清除所有用户的冷却（管理员用）"""
        self._cooldowns.clear()
    
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
        credit_rating = char_info.get("credit_rating", 0)
        
        # 属性
        attributes = char_info.get("attributes", {})
        attr_desc = self._describe_attributes(attributes)
        
        # 技能
        skills = char_info.get("skills", {})
        skill_desc = self._describe_skills(skills)
        
        # 背景故事元素
        backstory = char_info.get("backstory", {})
        
        # 生活水平
        living_level, living_desc = self._describe_credit_rating(credit_rating)
        
        # 构建提示词
        base_prompt = self.config.prompt or self._default_prompt(living_level, living_desc)
        
        # 年代信息
        era_info = f"- 年代: {era}" if era else ""
        
        prompt = f"""{base_prompt}

## 角色基本信息
- 姓名: {name}
- 年龄: {age}
- 性别: {gender}
- 国籍: {nationality}
- 职业: {occupation}
- 生活水平: {living_level}（信用评级{credit_rating}）- {living_desc}
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
    
    def _default_prompt(
        self, 
        living_level: str = "",
        living_desc: str = ""
    ) -> str:
        """默认提示词"""
        extra_requirements = ""
        
        # 生活水平要求
        if living_level:
            extra_requirements += f"""
10. 【重要】角色的生活水平是"{living_level}"：{living_desc}
    - 必须在故事中体现这种经济状况
    - 角色的居住环境、衣着打扮、社交圈子都应符合这一生活水平
    - 可以描述角色如何获得或失去财富，或如何在这种经济条件下生活"""
        
        return f"""你是一个克苏鲁的呼唤(COC)跑团游戏的角色背景故事生成器。
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
9. 使用流畅的叙事文风，避免列表式描述{extra_requirements}"""
    
    def _describe_attributes(self, attrs: dict) -> str:
        """描述属性特点，使用COC规则书的详细描述"""
        descriptions = []
        
        # 属性详细描述参考表
        attr_refs = {
            "STR": {
                "name": "力量",
                "levels": [
                    (0, "衰弱，没法站起来至端起一杯茶"),
                    (15, "弱者，虚弱"),
                    (50, "普通人水平"),
                    (90, "你见过的力气最大的人"),
                    (99, "世界水平（奥赛举重冠军）"),
                    (140, "超越人类之力（例如大猩猩）"),
                    (200, "怪物之力")
                ]
            },
            "CON": {
                "name": "体质",
                "levels": [
                    (0, "死亡"),
                    (1, "体弱多病，易感染疾病，可能在没有帮助的情况下无法活下去"),
                    (15, "身体虚弱，易受疾病，易感到疼痛"),
                    (50, "普通人水平"),
                    (90, "不惧寒冷，强壮而精神"),
                    (99, "钢铁之躯，能够承受巨大的疼痛"),
                    (140, "超越人类之体格（大象）"),
                    (200, "怪物之体，免疫大部分地球疾病")
                ]
            },
            "SIZ": {
                "name": "体型",
                "levels": [
                    (0, "没人知道他去了哪"),
                    (1, "婴儿（1~10斤）"),
                    (15, "孩童或身体瘦小的成人（15kg）"),
                    (65, "普通人类体型（中等身高和体重约75kg）"),
                    (80, "非常高，强健的体格或非常胖（110kg）"),
                    (99, "某方面已经是超大号了（150kg）"),
                    (150, "马或牛（436kg）"),
                    (180, "有记录的最重的人类（634kg）"),
                    (200, "872kg")
                ]
            },
            "DEX": {
                "name": "敏捷",
                "levels": [
                    (0, "没有协调无法行动"),
                    (15, "缓慢笨拙难以行动自如"),
                    (50, "普通人水平"),
                    (90, "高超而灵活，可以达成超凡的技艺（例如伟大的舞者）"),
                    (99, "世界级运动员，人类极限"),
                    (120, "超越人类之敏捷"),
                    (200, "闪电之速，可以在人类反应过来之前完成系列动作")
                ]
            },
            "APP": {
                "name": "外貌",
                "levels": [
                    (0, "如此的难看，他人会对你投以恐惧、厌恶和怜悯"),
                    (15, "丑，估计是因为受伤事故或先天如此"),
                    (50, "普通人水平"),
                    (90, "你见过的最漂亮的人，有着天然的吸引力"),
                    (99, "魅力和话的巅峰（超级名模或世界影星），人类极限")
                ]
            },
            "INT": {
                "name": "智力",
                "levels": [
                    (0, "没有智商，无法理解周遭的世界"),
                    (15, "学得很慢，只能理解最常用的数字或阅读学前级的书"),
                    (50, "普通人水平"),
                    (90, "超凡之脑，可以理解多门语言或法则"),
                    (99, "天才（爱因斯坦、达芬奇、特斯拉等），人类极限"),
                    (140, "超越人类之智"),
                    (210, "怪物之智，可以理解并操作多重次元")
                ]
            },
            "POW": {
                "name": "意志",
                "levels": [
                    (0, "弱者的心，没有意志力，没有魔法潜能"),
                    (15, "意志力弱，经常成为智力或高意志人士的人的玩物"),
                    (50, "普通人"),
                    (90, "坚强的心，对沟通不可视之物和魔法有着高潜质"),
                    (99, "人类极限"),
                    (100, "钢铁之心，与灵能领域和不可视世界有强烈的链接"),
                    (140, "超越人类，在上层异界存在"),
                    (210, "怪物的魔法潜质和力量，超越凡人之理解力")
                ]
            },
            "EDU": {
                "name": "教育",
                "levels": [
                    (0, "新生儿"),
                    (15, "任何方面都没有受过教育"),
                    (60, "高中毕业"),
                    (70, "大学毕业"),
                    (80, "研究生毕业"),
                    (90, "博士学位，教授"),
                    (96, "某研究领域的世界级权威")
                ]
            },
            "LUK": {
                "name": "幸运",
                "levels": [
                    (0, "霉运缠身"),
                    (15, "运气很差"),
                    (50, "普通人水平"),
                    (90, "运气极好，常有好事发生"),
                    (99, "天选之人，人类极限")
                ]
            }
        }
        
        for key, ref in attr_refs.items():
            value = attrs.get(key, 50)
            name = ref["name"]
            levels = ref["levels"]
            
            # 找到最接近的描述级别
            desc = "普通人水平"
            for threshold, level_desc in reversed(levels):
                if value >= threshold:
                    desc = level_desc
                    break
            
            # 只记录非普通水平的属性
            if "普通" not in desc:
                descriptions.append(f"- {name}({value}): {desc}")
        
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

    def _describe_credit_rating(self, credit_rating: int) -> tuple[str, str]:
        """
        描述信用评级对应的生活水平
        
        Args:
            credit_rating: 信用评级技能值
        
        Returns:
            (生活水平名称, 详细描述)
        """
        if credit_rating == 0:
            return ("身无分文", "没有任何财产和收入，可能是流浪汉、乞丐或被社会抛弃的人。居无定所，食不果腹。")
        elif credit_rating <= 9:
            return ("拮据", "生活困难，勉强维持基本生存。可能住在贫民窟或廉价公寓，经常为下一顿饭发愁。")
        elif credit_rating <= 49:
            return ("标准", "普通的中产阶级生活水平。有稳定的住所和收入，能够满足基本生活需求，偶尔有些小奢侈。")
        elif credit_rating <= 89:
            return ("小康", "生活富足，属于上层中产或下层富人。拥有舒适的住宅、体面的衣着，可以享受较高品质的生活。")
        elif credit_rating <= 98:
            return ("富裕", "非常富有，属于社会上层。拥有豪宅、仆人、名车，可以随意挥霍，在社交圈中有一定地位。")
        else:  # 99
            return ("富豪", "极度富有，属于社会顶层的富豪阶级。拥有巨额财富、多处房产、私人游艇或飞机，是社会名流。")

    def build_polish_backstory_prompt(self, char_info: dict) -> str:
        """
        构建润色背景故事要素的提示词（结构化输出）
        
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
        credit_rating = char_info.get("credit_rating", 0)
        
        # 属性
        attributes = char_info.get("attributes", {})
        attr_desc = self._describe_attributes(attributes)
        
        # 技能
        skills = char_info.get("skills", {})
        skill_desc = self._describe_skills(skills)
        
        # 背景故事元素
        backstory = char_info.get("backstory", {})
        
        # 生活水平
        living_level, living_desc = self._describe_credit_rating(credit_rating)
        
        # 年代信息
        era_info = f"- 年代: {era}" if era else ""
        
        # 生活水平要求
        extra_requirements = f"""
7. 【重要】角色的生活水平是"{living_level}"：{living_desc}
   - "形象描述"应体现这种经济状况（衣着、气质等）
   - "意义非凡之地"和"宝贵之物"应与生活水平相符"""
        
        prompt = f"""你是一个克苏鲁的呼唤(COC)跑团游戏的角色背景故事润色器。
请根据提供的角色信息，润色并扩展背景故事的各个要素。

## 角色基本信息
- 姓名: {name}
- 年龄: {age}
- 性别: {gender}
- 国籍: {nationality}
- 职业: {occupation}
- 生活水平: {living_level}（信用评级{credit_rating}）
{era_info}

## 属性特点
{attr_desc}

## 技能特长
{skill_desc}

## 当前背景故事要素（需要润色）
- 形象描述: {backstory.get('appearance', '未填写')}
- 思想与信念: {backstory.get('ideology', '未填写')}
- 重要之人: {backstory.get('significant_people', '未填写')}
- 意义非凡之地: {backstory.get('meaningful_locations', '未填写')}
- 宝贵之物: {backstory.get('treasured_possessions', '未填写')}
- 特质: {backstory.get('traits', '未填写')}
- 伤口和伤疤: {backstory.get('injuries', '未填写')}
- 恐惧症和躁狂症: {backstory.get('phobias', '未填写')}

## 要求
1. 根据角色属性和技能，润色每个背景故事要素
2. 如果某项"未填写"，请根据角色信息创造合理的内容
3. 如果某项已有内容，请在保留原意的基础上扩展润色
4. 每项内容控制在50-150字之间
5. 保持符合COC世界观和设定年代的风格
6. 不要在文中标注任何数值{extra_requirements}

## 输出格式（严格按照JSON格式输出）
请严格按照以下JSON格式输出，不要添加任何其他内容：
```json
{{
  "appearance": "润色后的形象描述",
  "ideology": "润色后的思想与信念",
  "significant_people": "润色后的重要之人",
  "meaningful_locations": "润色后的意义非凡之地",
  "treasured_possessions": "润色后的宝贵之物",
  "traits": "润色后的特质",
  "injuries": "润色后的伤口和伤疤（如无则写'无'）",
  "phobias": "润色后的恐惧症和躁狂症（如无则写'无'）"
}}
```"""
        
        return prompt

    def parse_polish_response(self, content: str) -> dict:
        """
        解析润色响应的JSON内容
        
        Args:
            content: LLM返回的内容
        
        Returns:
            解析后的字典，失败返回空字典
        """
        import json
        import re
        
        try:
            # 尝试直接解析
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取花括号内容
        brace_match = re.search(r'\{[\s\S]*\}', content)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"无法解析润色响应: {content[:200]}...")
        return {}


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
