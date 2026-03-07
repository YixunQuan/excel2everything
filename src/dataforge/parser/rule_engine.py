# -*- coding: utf-8 -*-
"""
映射规则引擎 - 将 Excel 映射规则文本转换为 SQL 表达式

支持：
1. 从配置文件加载规则
2. 按优先级依次匹配
3. 执行对应的转换动作
4. 支持条件触发规则
"""

import re
from typing import Tuple, Optional, Dict, Any, List, Callable
from dataclasses import dataclass

from dataforge.config.models import MappingRuleConfig, MappingRule


@dataclass
class RuleContext:
    """规则执行上下文"""
    source_table: str = ""      # 源表名
    source_field: str = ""      # 源字段名
    alias: str = ""             # 表别名
    target_field: str = ""      # 目标字段名
    target_label: str = ""      # 目标字段标签
    raw_rule: str = ""          # 原始规则文本


@dataclass
class RuleResult:
    """规则执行结果"""
    expr: str           # SQL 表达式
    comment: str = ""   # 注释
    warning: str = ""   # 告警信息
    rule_name: str = "" # 匹配的规则名称


class MappingRuleEngine:
    """映射规则引擎"""
    
    def __init__(self, config: Optional[MappingRuleConfig] = None):
        """
        初始化规则引擎
        
        Args:
            config: 映射规则配置，为 None 时使用内置默认规则
        """
        self.config = config
        self._compiled_rules: List[Tuple[re.Pattern, MappingRule]] = []
        
        if config:
            self._compile_rules(config.rules)
        else:
            self._use_builtin_rules()
    
    def _compile_rules(self, rules: List[MappingRule]):
        """编译正则表达式规则"""
        for rule in rules:
            try:
                pattern = re.compile(rule.pattern, re.IGNORECASE)
                self._compiled_rules.append((pattern, rule))
            except re.error as e:
                print(f"规则编译失败: {rule.name} - {e}")
    
    def _use_builtin_rules(self):
        """使用内置默认规则"""
        builtin_rules = [
            # 直取/码值
            MappingRule(name="直取", pattern=r"^(直取|码值)$", action="direct_field"),
            # 变量引用
            MappingRule(name="变量引用", pattern=r"^[VP]_[A-Z0-9_]+$", action="variable"),
            # 引号字符串
            MappingRule(name="引号字符串", pattern=r"^'([^']*)'\s*(--.*)?$", action="quoted_string"),
            # SQL 函数
            MappingRule(name="SQL函数", pattern=r"^(CASE|SELECT|CONCAT|NVL|COALESCE|DECODE|SUBSTR|REPLACE|TO_CHAR|TO_DATE|TRIM|UPPER|LOWER|CAST|TRUNC|TDH_TODATE)", action="sql_expression"),
            # CASE WHEN
            MappingRule(name="CASE表达式", pattern=r"CASE\s+WHEN", action="sql_expression"),
            # 数字
            MappingRule(name="数字", pattern=r"^\d+(\.\d+)?$", action="number"),
            # 字段引用
            MappingRule(name="字段引用", pattern=r"^[A-Z_][A-Z0-9_]*\.[A-Z_][A-Z0-9_]*$", action="field_reference"),
            # 字符串拼接
            MappingRule(name="字符串拼接", pattern=r"\|\|", action="sql_expression"),
        ]
        self._compile_rules(builtin_rules)
    
    def apply(self, rule_text: str, context: Optional[RuleContext] = None) -> RuleResult:
        """
        应用规则转换映射文本
        
        Args:
            rule_text: 映射规则文本
            context: 规则执行上下文
            
        Returns:
            RuleResult: 转换结果
        """
        if context is None:
            context = RuleContext()
        
        # 空值处理
        if not rule_text or rule_text.strip() in ("", "nan"):
            return RuleResult(expr="NULL", rule_name="empty")
        
        rule_text = rule_text.strip()
        
        # 检查条件规则（如 source_table == "固定"）
        if context.source_table and context.source_table.strip() == "固定":
            return self._handle_fixed_value(rule_text, context)
        
        # 按优先级匹配规则
        for pattern, rule in self._compiled_rules:
            match = pattern.search(rule_text)
            if match:
                return self._execute_action(rule, rule_text, match, context)
        
        # fallback: 尝试智能处理
        return self._fallback(rule_text, context)
    
    def _execute_action(
        self, 
        rule: MappingRule, 
        rule_text: str, 
        match: re.Match, 
        context: RuleContext
    ) -> RuleResult:
        """执行规则动作"""
        action = rule.action.lower()
        
        if action == "direct_field":
            return self._handle_direct_field(rule_text, context)
        elif action == "variable":
            return RuleResult(expr=rule_text.upper(), rule_name=rule.name)
        elif action == "quoted_string":
            return self._handle_quoted_string(rule_text, match, context)
        elif action == "sql_expression":
            return self._handle_sql_expression(rule_text, context)
        elif action == "number":
            return RuleResult(expr=rule_text, rule_name=rule.name)
        elif action == "field_reference":
            return RuleResult(expr=rule_text, rule_name=rule.name)
        elif action == "fixed_value":
            return self._handle_fixed_value(rule_text, context)
        else:
            return RuleResult(expr=rule_text, warning=f"未知动作: {action}", rule_name=rule.name)
    
    def _handle_direct_field(self, rule_text: str, context: RuleContext) -> RuleResult:
        """处理直取规则"""
        if context.source_field:
            # 取源字段的第一个（可能有多行）
            field = context.source_field.strip().split("\n")[0].strip()
            if context.alias:
                expr = f"{context.alias}.{field}"
            else:
                expr = field
            return RuleResult(expr=expr, rule_name="直取")
        return RuleResult(
            expr="NULL", 
            warning=f"映射规则={rule_text}, 但无源字段",
            rule_name="直取"
        )
    
    def _handle_quoted_string(self, rule_text: str, match: re.Match, context: RuleContext) -> RuleResult:
        """处理引号字符串"""
        # 提取引号内的值
        value = match.group(1) if match.groups() else ""
        comment = ""
        
        # 检查是否有注释
        rest = rule_text[match.end():].strip()
        if rest.startswith("--"):
            comment = rest
        
        return RuleResult(expr=f"'{value}'", comment=comment, rule_name="引号字符串")
    
    def _handle_sql_expression(self, rule_text: str, context: RuleContext) -> RuleResult:
        """处理 SQL 表达式"""
        # 清理尾部注释（保留在 comment 字段）
        expr = self._sanitize_trailing_comment(rule_text)
        return RuleResult(expr=expr, rule_name="SQL表达式")
    
    def _handle_fixed_value(self, rule_text: str, context: RuleContext) -> RuleResult:
        """处理固定值"""
        # 如果已经是引号字符串，检查转义
        if rule_text.startswith("'"):
            # 处理内部引号
            last_quote = rule_text.rfind("'")
            if last_quote > 0:
                value = rule_text[1:last_quote]
                # 检查是否需要转义
                if "'" in value and "''" not in value:
                    value = value.replace("'", "''")
                return RuleResult(expr=f"'{value}'", rule_name="固定值")
            return RuleResult(expr="''", rule_name="固定值")
        
        # 不是引号字符串，自动加引号
        escaped = rule_text.replace("'", "''")
        return RuleResult(expr=f"'{escaped}'", rule_name="固定值")
    
    def _sanitize_trailing_comment(self, expr: str) -> str:
        """清理表达式尾部的 SQL 单行注释"""
        if "--" not in expr:
            return expr.strip()
        
        lines = expr.split("\n")
        if len(lines) == 1:
            return re.sub(r"\s*--[^\n]*$", "", expr).rstrip()
        
        cleaned = lines[:-1]
        cleaned.append(re.sub(r"\s*--[^\n]*$", "", lines[-1]).rstrip())
        return "\n".join(cleaned)
    
    def _fallback(self, rule_text: str, context: RuleContext) -> RuleResult:
        """Fallback 处理：无法匹配时的智能处理"""
        # 检查常见 SQL 模式
        if any(pat in rule_text.upper() for pat in ["(", ")", "+", "-", "*", "/", "."]):
            expr = self._sanitize_trailing_comment(rule_text)
            return RuleResult(expr=expr, rule_name="fallback-sql")
        
        # 缺失左引号的情况: value' -- comment
        m = re.match(r"^([^']+)'\\s*(--.*)?$", rule_text)
        if m:
            val = m.group(1).strip()
            if not any(k in val.upper() for k in ("SELECT", "FROM", "WHERE", "CASE", "WHEN", "END")):
                if "'" in val:
                    val = val.replace("'", "''")
                return RuleResult(expr=f"'{val}'", rule_name="fallback-missing-quote")
        
        # 原样保留并告警
        return RuleResult(
            expr=rule_text,
            warning=f"未识别的映射规则，已原样保留: {rule_text[:60]}",
            rule_name="fallback"
        )


# 全局引擎实例
_engine: Optional[MappingRuleEngine] = None


def get_rule_engine(config: Optional[MappingRuleConfig] = None) -> MappingRuleEngine:
    """获取规则引擎实例"""
    global _engine
    if _engine is None or config:
        _engine = MappingRuleEngine(config)
    return _engine


def apply_rule(rule_text: str, context: Optional[RuleContext] = None) -> RuleResult:
    """便捷函数：应用规则"""
    return get_rule_engine().apply(rule_text, context)
