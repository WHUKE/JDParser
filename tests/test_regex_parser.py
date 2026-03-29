"""regex_parser 模块测试"""

import pytest
from src.core.models import JobDescription
from src.parsers.regex_parser import RegexParser


@pytest.fixture
def parser():
    return RegexParser()


# ── 完整 JD 解析 ──


class TestRegexParserFullParse:
    """测试完整 JD 文本解析"""

    SAMPLE_JD = """\
前端开发工程师
技术
全职
负责华为云服务控制台前端开发，设计并实现前端框架与UI组件库，搭建前端工程化体系。

岗位描述
1、负责华为云控制台（Console）前端开发，涉及计算、网络、存储、安全、PaaS等业务模块；
2、设计并实现华为云前端框架、UI组件库，提升用户体验和研发效率；
3、搭建前端工程化体系，实现项目初始化、构建、发布、运维的DevOps支撑；

岗位要求
1、本科及以上学历，计算机、软件、通信、电子信息等相关专业；
2、熟练掌握HTML5、CSS3、JavaScript（ES5/ES6）等前端基础；
3、熟悉Vue、React或Angular中任意一种前端框架；

加分项
1、有大型Web应用、移动端H5、响应式开发经验；
2、对前端安全、XSS防护、性能优化有深入认识；

工作地点
北京、上海、深圳、杭州
"""

    def test_job_title(self, parser):
        jd = parser.parse(self.SAMPLE_JD, "test_01.txt")
        assert jd.job_title == "前端开发工程师"

    def test_source_file(self, parser):
        jd = parser.parse(self.SAMPLE_JD, "test_01.txt")
        assert jd.source_file == "test_01.txt"

    def test_employment_type(self, parser):
        jd = parser.parse(self.SAMPLE_JD, "test_01.txt")
        assert jd.employment_type == "全职"

    def test_education(self, parser):
        jd = parser.parse(self.SAMPLE_JD, "test_01.txt")
        assert jd.education == "本科"

    def test_location(self, parser):
        """注意：当前正则解析器对 '工作地点\\n城市列表' 格式支持有限，
        此处验证的是带标签格式能被正确提取"""
        text = self.SAMPLE_JD.replace("工作地点\n北京、上海、深圳、杭州",
                                       "工作地点：北京、上海、深圳、杭州")
        jd = parser.parse(text, "test_01.txt")
        assert jd.location is not None
        assert "北京" in jd.location

    def test_responsibilities_extracted(self, parser):
        jd = parser.parse(self.SAMPLE_JD, "test_01.txt")
        assert len(jd.responsibilities) >= 2

    def test_raw_requirements_extracted(self, parser):
        jd = parser.parse(self.SAMPLE_JD, "test_01.txt")
        assert len(jd.raw_requirements) >= 2


# ── 职位名称 ──


class TestExtractTitle:
    """测试职位名称提取"""

    def test_first_line(self, parser):
        jd = parser.parse("后端开发工程师\n其他内容", "t.txt")
        assert jd.job_title == "后端开发工程师"

    def test_strip_suffix_noise(self, parser):
        jd = parser.parse("后端开发工程师 全职\n内容", "t.txt")
        assert jd.job_title == "后端开发工程师"

    def test_strip_suffix_intern(self, parser):
        jd = parser.parse("数据分析师 实习\n内容", "t.txt")
        assert jd.job_title == "数据分析师"

    def test_prefixed_format(self, parser):
        jd = parser.parse("岗位名称：高级Java工程师\n内容", "t.txt")
        assert jd.job_title == "高级Java工程师"

    def test_empty_text(self, parser):
        jd = parser.parse("", "t.txt")
        assert jd.job_title is None


# ── 学历提取 ──


class TestExtractEducation:
    """测试学历提取"""

    def test_bachelor(self, parser):
        jd = parser.parse("职位\n本科及以上学历", "t.txt")
        assert jd.education == "本科"

    def test_master(self, parser):
        jd = parser.parse("职位\n硕士及以上学历", "t.txt")
        assert jd.education == "硕士"

    def test_master_graduate(self, parser):
        jd = parser.parse("职位\n硕士研究生及以上学历", "t.txt")
        assert jd.education == "硕士"

    def test_doctor(self, parser):
        jd = parser.parse("职位\n博士及以上学历", "t.txt")
        assert jd.education == "博士"

    def test_college(self, parser):
        jd = parser.parse("职位\n大专及以上学历", "t.txt")
        assert jd.education == "大专"

    def test_not_required(self, parser):
        jd = parser.parse("职位\n学历：不限", "t.txt")
        assert jd.education == "不限"

    def test_no_education(self, parser):
        jd = parser.parse("职位\n无学历要求描述", "t.txt")
        assert jd.education is None


# ── 工作年限 ──


class TestExtractExperience:
    """测试工作年限提取"""

    def test_range_format(self, parser):
        jd = parser.parse("职位\n3-5年工作经验", "t.txt")
        assert jd.experience == "3-5年"

    def test_above_format(self, parser):
        jd = parser.parse("职位\n3年以上工作经验", "t.txt")
        assert jd.experience == "3年以上"

    def test_tilde_range(self, parser):
        jd = parser.parse("职位\n3~5年开发经验", "t.txt")
        assert jd.experience == "3-5年"

    def test_no_experience(self, parser):
        jd = parser.parse("这是一个职位描述\n没有提到经验", "t.txt")
        assert jd.experience is None


# ── 工作地点 ──


class TestExtractLocation:
    """测试工作地点提取"""

    def test_labeled_location(self, parser):
        jd = parser.parse("职位\n工作地点：北京\n其他", "t.txt")
        assert jd.location == "北京"

    def test_slash_format(self, parser):
        jd = parser.parse("全职 / 广州市 / 某部门\n其他", "t.txt")
        assert "广州" in jd.location

    def test_standalone_city(self, parser):
        jd = parser.parse("职位\n杭州\n其他内容", "t.txt")
        assert jd.location == "杭州"

    def test_no_location(self, parser):
        jd = parser.parse("职位\n没有城市信息", "t.txt")
        assert jd.location is None


# ── 招聘类型 ──


class TestExtractEmploymentType:
    """测试招聘类型提取"""

    def test_fulltime(self, parser):
        jd = parser.parse("后端工程师\n全职\n内容", "t.txt")
        assert jd.employment_type == "全职"

    def test_parttime(self, parser):
        jd = parser.parse("后端工程师\n兼职\n内容", "t.txt")
        assert jd.employment_type == "兼职"

    def test_intern(self, parser):
        jd = parser.parse("后端工程师\n实习\n内容", "t.txt")
        assert jd.employment_type == "实习"


# ── 段落解析 ──


class TestExtractSections:
    """测试段落内容提取"""

    def test_responsibilities_section(self, parser):
        text = "职位\n\n工作职责\n1、开发核心模块\n2、维护系统稳定\n\n岗位要求\n1、本科学历\n"
        jd = parser.parse(text, "t.txt")
        assert len(jd.responsibilities) == 2
        assert "开发核心模块" in jd.responsibilities[0]

    def test_requirements_section(self, parser):
        text = "职位\n\n岗位要求\n1、本科学历\n2、3年经验\n"
        jd = parser.parse(text, "t.txt")
        assert len(jd.raw_requirements) == 2

    def test_multiple_list_formats(self, parser):
        text = "职位\n\n工作职责\n- 开发接口\n- 编写文档\n- 代码审查\n"
        jd = parser.parse(text, "t.txt")
        assert len(jd.responsibilities) == 3

    def test_dot_list_format(self, parser):
        text = "职位\n\n工作职责\n1. 开发接口\n2. 编写文档\n"
        jd = parser.parse(text, "t.txt")
        assert len(jd.responsibilities) >= 2

    def test_bullet_list_format(self, parser):
        text = "职位\n\n工作职责\n· 开发接口\n· 编写文档\n"
        jd = parser.parse(text, "t.txt")
        assert len(jd.responsibilities) >= 2


# ── _parse_list_items 单元测试 ──


class TestParseListItems:
    """测试列表解析静态方法"""

    def test_numbered_chinese(self):
        text = "1、开发核心模块\n2、维护系统稳定"
        items = RegexParser._parse_list_items(text)
        assert len(items) == 2
        assert items[0] == "开发核心模块"

    def test_numbered_dot(self):
        text = "1. 开发模块\n2. 编写文档"
        items = RegexParser._parse_list_items(text)
        assert len(items) == 2

    def test_dash_list(self):
        text = "- 开发模块\n- 编写文档\n- 代码审查"
        items = RegexParser._parse_list_items(text)
        assert len(items) == 3

    def test_bullet_list(self):
        text = "· 开发模块\n· 编写文档"
        items = RegexParser._parse_list_items(text)
        assert len(items) == 2

    def test_skip_subtitles(self):
        text = "【核心技能】\n1、Python\n2、Java"
        items = RegexParser._parse_list_items(text)
        assert len(items) == 2
        assert "核心技能" not in items[0]

    def test_empty_text(self):
        items = RegexParser._parse_list_items("")
        assert items == []

    def test_single_item(self):
        items = RegexParser._parse_list_items("1、负责后端开发")
        assert len(items) == 1


# ── 面向对象 ──


class TestExtractTargetGroup:
    """测试面向对象提取"""

    def test_social_recruitment(self, parser):
        jd = parser.parse("职位\n面向对象：社招\n内容", "t.txt")
        assert jd.target_group == "社招"

    def test_campus_recruitment(self, parser):
        jd = parser.parse("职位\n面向对象：校招\n内容", "t.txt")
        assert jd.target_group == "校招"

    def test_no_target(self, parser):
        jd = parser.parse("职位\n一些内容", "t.txt")
        assert jd.target_group is None
