"""基于正则/规则的 JD 预解析器

采用宽松匹配策略，不依赖特定 JD 格式，
尽力从各种来源的文本中提取结构化字段。
"""

import re
from src.core.models import JobDescription
from src.parsers.base import BaseParser


class RegexParser(BaseParser):
    """使用正则表达式提取 JD 中的结构化字段（格式无关）"""

    # ── 段落标题关键词 → 归一化名称 ──
    _SECTION_ALIASES: dict[str, list[str]] = {
        "responsibilities": ["职位描述", "工作职责", "岗位职责", "职责描述", "主要职责", "工作内容", "岗位描述"],
        "requirements": ["职位要求", "任职要求", "岗位要求", "任职资格", "基本要求", "招聘要求", "必备条件"],
        "preferred": ["加分项", "优先条件", "加分条件", "优先考虑", "加分技能", "附加条件"],
        "other": ["能力与特质", "综合素质", "面向对象", "其他要求", "备注"],
    }

    def parse(self, text: str, filename: str) -> JobDescription:
        jd = JobDescription(source_file=filename)
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

        self._extract_title(jd, lines, text)
        self._extract_location(jd, text)
        self._extract_education(jd, text)
        self._extract_experience(jd, text)
        self._extract_employment_type(jd, text)
        self._extract_headcount(jd, text)
        self._extract_publish_date(jd, text)
        self._extract_department(jd, text)
        self._extract_job_category(jd, text)
        self._extract_target_group(jd, text)
        self._extract_sections(jd, text)

        return jd

    # ── 职位名称（取第一行，清洗后缀噪声）──
    def _extract_title(self, jd: JobDescription, lines: list[str], text: str) -> None:
        if not lines:
            return
        title = lines[0]
        # 去掉常见后缀噪声
        title = re.sub(r"(全职|兼职|实习|急招|热招)\s*$", "", title).strip()
        # 有些 JD 第一行是 "岗位名称：xxx"
        m = re.match(r"(?:岗位|职位)\s*(?:名称)?\s*[:：]\s*(.+)", title)
        if m:
            title = m.group(1).strip()
        jd.job_title = title

    # ── 工作地点 ──
    def _extract_location(self, jd: JobDescription, text: str) -> None:
        patterns = [
            # "全职 / 广州市 / ..."
            r"(?:全职|兼职|实习)\s*/\s*([^\s/]+?(?:市|省|区|县))\s*/",
            # "工作地点：xxx" 或 "地点：xxx"
            r"(?:工作地[点址]|地\s*[点址]|工作城市|城\s*市)\s*[:：]\s*(.+?)(?:\n|$)",
            # 独立短行匹配中国城市名
            r"(?:^|\n)\s*((?:北京|上海|广州|深圳|杭州|成都|武汉|南京|西安|重庆|"
            r"苏州|天津|长沙|郑州|东莞|青岛|合肥|佛山|宁波|昆明|"
            r"厦门|大连|福州|无锡|珠海|贵阳|海口|三亚|拉萨)(?:市)?)\s*(?:\n|$)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                jd.location = m.group(1).strip()
                return

    # ── 学历要求 ──
    def _extract_education(self, jd: JobDescription, text: str) -> None:
        patterns = [
            r"学历\s*(?:要求)?\s*[:：]?\s*\n?\s*(博士|硕士|本科|大专|不限)",
            r"(博士|硕士研究生|硕士|本科|大专)及以上\s*(?:学历|学位)",
            r"学历\s*[:：]?\s*(博士|硕士|本科|大专|不限)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                edu = m.group(1)
                if edu == "硕士研究生":
                    edu = "硕士"
                jd.education = edu
                return

    # ── 工作年限 ──
    def _extract_experience(self, jd: JobDescription, text: str) -> None:
        patterns = [
            r"工作年限\s*[:：]?\s*\n?\s*(.+?)(?:\n|$)",
            r"(\d+[-~～至]\d+)\s*年.*?(?:工作|开发|相关|项目)?经验",
            r"(\d+)\s*年以上.*?(?:工作|开发|相关|项目)?经验",
            r"经验\s*(?:要求)?\s*[:：]\s*(.+?)(?:\n|$)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                exp = m.group(1).strip()
                # 统一格式 "3-5年" / "3年以上" / "不限"
                if re.match(r"\d+[-~～至]\d+$", exp):
                    exp = re.sub(r"[-~～至]", "-", exp) + "年"
                elif re.match(r"\d+$", exp):
                    # 纯数字 → 推断后缀
                    if "年以上" in text[m.start():m.end() + 10]:
                        exp += "年以上"
                    else:
                        exp += "年"
                jd.experience = exp
                return

    # ── 招聘类型 ──
    def _extract_employment_type(self, jd: JobDescription, text: str) -> None:
        m = re.search(r"(全职|兼职|实习)", text[:200])  # 通常在文档开头
        if m:
            jd.employment_type = m.group(1)

    # ── 招聘人数 ──
    def _extract_headcount(self, jd: JobDescription, text: str) -> None:
        m = re.search(r"(\d+)\s*人", text[:300])
        if m:
            jd.headcount = int(m.group(1))

    # ── 发布日期 ──
    def _extract_publish_date(self, jd: JobDescription, text: str) -> None:
        m = re.search(r"(\d{4}-\d{2}-\d{2})\s*发布", text)
        if m:
            jd.publish_date = m.group(1)

    # ── 所属部门 ──
    def _extract_department(self, jd: JobDescription, text: str) -> None:
        m = re.search(r"所属部门\s*[:：]?\s*\n?\s*(.+?)(?:\n|$)", text)
        if m:
            jd.department = m.group(1).strip()

    # ── 职位类别 ──
    def _extract_job_category(self, jd: JobDescription, text: str) -> None:
        patterns = [
            # "技术-前端及客户端开发-web前端开发" 格式
            r"/\s*(技术.+?)\s*/",
            # "程序&技术类" 等短分类
            r"(?:^|\n)\s*(.+?[类别])\s*(?:\n|$)",
            r"(?:职位|岗位)\s*(?:类别|分类)\s*[:：]\s*(.+?)(?:\n|$)",
        ]
        for p in patterns:
            m = re.search(p, text[:500])
            if m:
                cat = m.group(1).strip()
                # 排除误匹配（太长或包含无关内容）
                if len(cat) <= 30 and "要求" not in cat:
                    jd.job_category = cat
                    return

    # ── 面向对象 ──
    def _extract_target_group(self, jd: JobDescription, text: str) -> None:
        m = re.search(r"(?:面向对象|招聘类型|招聘对象)\s*[:：]?\s*\n?\s*((?:常规)?社招|校招|实习)", text)
        if m:
            jd.target_group = m.group(1)

    # ── 段落内容提取 ──
    def _extract_sections(self, jd: JobDescription, text: str) -> None:
        sections = self._split_sections(text)

        if "responsibilities" in sections:
            jd.responsibilities = self._parse_list_items(sections["responsibilities"])
        if "requirements" in sections:
            jd.raw_requirements = self._parse_list_items(sections["requirements"])

    def _split_sections(self, text: str) -> dict[str, str]:
        """按段落标题分割文本（格式无关版本）"""
        # 收集所有可能的标题关键词
        header_to_section: dict[str, str] = {}
        all_keywords: list[str] = []
        for section_name, keywords in self._SECTION_ALIASES.items():
            for kw in keywords:
                header_to_section[kw] = section_name
                all_keywords.append(re.escape(kw))

        # 匹配段落标题：行首（可选标记如【】）+ 关键词 + 可选冒号
        keywords_re = "|".join(all_keywords)
        pattern = re.compile(
            rf"(?:^|\n)\s*(?:【[^】]*】\s*)?({keywords_re})\s*[:：]?\s*\n",
            re.MULTILINE,
        )

        matches = list(pattern.finditer(text))
        sections: dict[str, str] = {}

        for i, m in enumerate(matches):
            header = m.group(1)
            section_name = header_to_section.get(header, "other")
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            # 如果同一 section 出现多次，拼接内容
            if section_name in sections:
                sections[section_name] += "\n" + content
            else:
                sections[section_name] = content

        return sections

    @staticmethod
    def _parse_list_items(text: str) -> list[str]:
        """将段落文本解析为条目列表（支持多种列表格式）"""
        items: list[str] = []
        current = ""

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # 跳过子标题（如【核心技能】、【AI 开发能力】）
            if re.match(r"^【.+】$", line):
                continue
            # 检测列表项开头：数字. / 数字、/ 数字) / - / · / * 等
            if re.match(r"^(\d+[\.\、\)\）]|[-·•\*])\s*", line):
                if current:
                    items.append(current)
                current = re.sub(r"^(\d+[\.\、\)\）]|[-·•\*])\s*", "", line)
            else:
                if current:
                    current += line
                else:
                    current = line

        if current:
            items.append(current)

        return items
