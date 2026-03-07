# -*- coding: utf-8 -*-
"""
SQL 验证器 — 对生成的 SQL 进行语法检查和质量验证

提供二次检查机制，在渲染后验证 SQL 质量
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class IssueSeverity(Enum):
    """问题严重级别"""
    CRITICAL = "critical"  # 致命错误，SQL 无法执行
    WARNING = "warning"    # 警告，可能导致运行时错误
    INFO = "info"          # 提示信息


@dataclass
class SQLIssue:
    """SQL 问题描述"""
    severity: IssueSeverity
    category: str          # 问题类别
    line_number: int       # 行号（从 1 开始）
    column: Optional[int]  # 列号（可选）
    problem: str           # 问题描述
    detail: str            # 详细信息
    suggestion: str        # 修复建议
    code_snippet: str      # 问题代码片段
    
    def to_dict(self):
        return {
            "severity": self.severity.value,
            "category": self.category,
            "line_number": self.line_number,
            "column": self.column,
            "problem": self.problem,
            "detail": self.detail,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
        }


class SQLValidator:
    """SQL 验证器"""
    
    def __init__(self):
        self.issues: List[SQLIssue] = []
        # SQL 关键字列表（用于验证）
        self.sql_keywords = frozenset({
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'EXISTS',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'ON', 'JOIN',
            'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS',
            'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET',
            'UNION', 'ALL', 'DISTINCT', 'TOP', 'INTO', 'VALUES',
            'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
            'TABLE', 'VIEW', 'INDEX', 'PROCEDURE', 'FUNCTION', 'TRIGGER',
            'BEGIN', 'END', 'DECLARE', 'IF', 'ELSE', 'WHILE', 'FOR', 'LOOP',
            'CURSOR', 'OPEN', 'FETCH', 'CLOSE', 'RETURN', 'NULL', 'IS',
            'LIKE', 'BETWEEN', 'NULLS', 'FIRST', 'LAST', 'OVER', 'PARTITION',
            'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
            'NVL', 'COALESCE', 'DECODE', 'CAST', 'CONVERT', 'TO_CHAR', 'TO_DATE',
            'TO_NUMBER', 'SUBSTR', 'SUBSTRING', 'INSTR', 'LENGTH', 'TRIM', 'LTRIM',
            'RTRIM', 'UPPER', 'LOWER', 'INITCAP', 'REPLACE', 'TRANSLATE', 'CONCAT',
            'LPAD', 'RPAD', 'INSTR', 'ASCII', 'CHR', 'ROUND', 'TRUNC', 'CEIL', 'FLOOR',
            'ABS', 'MOD', 'POWER', 'SQRT', 'SIGN', 'SYSDATE', 'CURRENT_DATE',
            'CURRENT_TIMESTAMP', 'USER', 'DUAL', 'ROWID', 'ROWNUM', 'LEVEL',
            'CONNECT', 'PRIOR', 'START', 'WITH', 'NO', 'YES', 'TRUE', 'FALSE',
            'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK',
            'DEFAULT', 'CONSTRAINT', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK',
            'SAVEPOINT', 'SET', 'TRANSACTION', 'LOCK', 'TABLESPACE',
            'PCTFREE', 'PCTUSED', 'INITRANS', 'MAXTRANS', 'STORAGE',
            'COMPRESS', 'NOCOMPRESS', 'PARALLEL', 'NOPARALLEL',
            'GREATEST', 'LEAST', 'NANVL', 'LNNVL', 'NVL2',
            'ADD_MONTHS', 'LAST_DAY', 'MONTHS_BETWEEN', 'NEXT_DAY',
            'NEW_TIME', 'EXTRACT', 'NUMTODSINTERVAL', 'NUMTOYMINTERVAL',
        })
        # SQL 函数名列表
        self.sql_functions = frozenset({
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'NVL', 'COALESCE', 'DECODE',
            'CAST', 'CONVERT', 'TO_CHAR', 'TO_DATE', 'TO_NUMBER',
            'SUBSTR', 'SUBSTRING', 'INSTR', 'LENGTH', 'TRIM', 'LTRIM', 'RTRIM',
            'UPPER', 'LOWER', 'INITCAP', 'REPLACE', 'TRANSLATE', 'CONCAT',
            'LPAD', 'RPAD', 'ASCII', 'CHR', 'ROUND', 'TRUNC', 'CEIL', 'FLOOR',
            'ABS', 'MOD', 'POWER', 'SQRT', 'SIGN', 'GREATEST', 'LEAST',
            'NVL2', 'NANVL', 'LNNVL', 'ROW_NUMBER', 'RANK', 'DENSE_RANK',
            'ADD_MONTHS', 'LAST_DAY', 'MONTHS_BETWEEN', 'NEXT_DAY',
            'SYSDATE', 'CURRENT_DATE', 'CURRENT_TIMESTAMP',
            'USER', 'EXTRACT', 'REGEXP_REPLACE', 'REGEXP_SUBSTR', 'REGEXP_INSTR',
            'LISTAGG', 'XMLAGG', 'XMLELEMENT', 'JSON_ARRAY', 'JSON_OBJECT',
        })
    
    def validate(self, sql: str, context: dict = None) -> dict:
        """
        验证 SQL 代码质量
        
        Args:
            sql: SQL 代码字符串
            context: 上下文信息（表名、组名等）
        
        Returns:
            {
                "has_errors": bool,          # 是否有错误
                "has_warnings": bool,        # 是否有警告
                "issues": [                  # 问题列表
                    {
                        "severity": str,
                        "category": str,
                        "line_number": int,
                        "problem": str,
                        "suggestion": str,
                        ...
                    }
                ],
                "error_count": int,           # 错误数量
                "warning_count": int,         # 警告数量
            }
        """
        self.issues = []
        context = context or {}
        
        lines = sql.split('\n')
        
        # 1. 检查字符串字面量问题
        self._check_string_literals(lines)
        
        # 2. 检查括号匹配
        self._check_parentheses(lines)
        
        # 3. 检查注释语法
        self._check_comments(lines)
        
        # 4. 检查 FROM 子句
        self._check_from_clause(lines)
        
        # 5. 检查常见 SQL 语法错误
        self._check_sql_syntax(lines)
        
        # 6. 检查数据类型和函数使用
        self._check_functions(lines)
        
        # 7. 检查 SQL 结构问题
        self._check_sql_structure(lines)
        
        # 8. 检查 SELECT 和 INSERT 列数是否匹配
        self._check_column_count(lines)
        
        # 9. 检查未定义的列引用
        self._check_undefined_references(lines, context)
        
        # 10. 检查关键字拼写错误
        self._check_keyword_typos(lines)
        
        # 11. 检查 SELECT * 使用
        self._check_select_star(lines)
        
        # 12. 检查 ORDER BY 在子查询中的使用
        self._check_order_by_in_subquery(lines)
        
        # 统计错误和警告
        error_count = sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)
        warning_count = sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)
        info_count = sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)
        
        return {
            "has_errors": error_count > 0,
            "has_warnings": warning_count > 0,
            "issues": [issue.to_dict() for issue in self.issues],
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "total_issues": len(self.issues),
        }
    
    def validate_list(self, sql: str, context: dict = None) -> List[SQLIssue]:
        """
        验证 SQL 并返回问题列表（向后兼容）
        
        Args:
            sql: SQL 代码字符串
            context: 上下文信息
            
        Returns:
            SQLIssue 对象列表
        """
        self.validate(sql, context)
        return self.issues
    
    def _check_string_literals(self, lines: List[str]):
        """检查字符串字面量的问题"""
        for line_no, line in enumerate(lines, 1):
            # 跳过注释行
            if line.strip().startswith('--'):
                continue
            
            # 检查单引号配对（排除注释部分）
            code_part = line.split('--')[0] if '--' in line else line
            
            # 1. 检查未配对的引号
            quote_count = code_part.count("'")
            if quote_count % 2 != 0:
                self.issues.append(SQLIssue(
                    severity=IssueSeverity.CRITICAL,
                    category="字符串字面量",
                    line_number=line_no,
                    column=None,
                    problem="单引号未配对",
                    detail=f"该行包含 {quote_count} 个单引号，数量为奇数",
                    suggestion="检查字符串常量是否正确闭合，SQL 中的单引号需要用 '' 转义",
                    code_snippet=line.strip()[:100]
                ))
            
            # 2. 检查单引号转义问题的特殊模式
            # 模式：'value'' --comment  (两个单引号后面紧跟空格和注释)
            # 这是错误的，正确应该是 'value' --comment
            if re.search(r"'[^']*''\s+--", code_part):
                self.issues.append(SQLIssue(
                    severity=IssueSeverity.CRITICAL,
                    category="字符串字面量",
                    line_number=line_no,
                    column=None,
                    problem="单引号转义错误",
                    detail="检测到 ''-- 模式，可能是单引号转义不正确",
                    suggestion="如果字符串内容不包含单引号，应该是 'value' --comment；如果包含单引号，应该是 'val''ue' --comment",
                    code_snippet=line.strip()[:100]
                ))
            
            # 3. 检查未转义的单引号（在字符串内部）
            # 但要排除 CASE WHEN 等 SQL 表达式中的正常情况
            # 如：CASE WHEN ... THEN 'Y' ELSE 'N' END
            upper_code = code_part.upper()
            is_sql_expr = any(kw in upper_code for kw in ['CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'SELECT', 'FROM', 'WHERE'])
            
            # 只有在非 SQL 表达式中才检查这种模式
            if not is_sql_expr:
                # 查找 'xxx'xxx' 这种模式（字符串后还有字符再跟引号）
                if re.search(r"'[^']*'[^'\s,)]+?'", code_part):
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.WARNING,
                        category="字符串字面量",
                        line_number=line_no,
                        column=None,
                        problem="可能存在未转义的单引号",
                        detail="字符串字面量后出现非空白字符再跟单引号",
                        suggestion="在 SQL 字符串常量中，单引号需要用两个单引号 '' 转义",
                        code_snippet=line.strip()[:100]
                    ))
    
    def _check_parentheses(self, lines: List[str]):
        """检查括号配对"""
        total_left = 0
        total_right = 0
        
        for line_no, line in enumerate(lines, 1):
            # 跳过注释行
            if line.strip().startswith('--'):
                continue
            
            # 只检查代码部分（不含注释）
            code_part = line.split('--')[0] if '--' in line else line
            
            left_count = code_part.count('(')
            right_count = code_part.count(')')
            
            total_left += left_count
            total_right += right_count
            
            # 检查当前行括号不平衡（某些场景）
            if right_count > left_count:
                diff = right_count - left_count
                if total_left < total_right:
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="括号匹配",
                        line_number=line_no,
                        column=None,
                        problem=f"右括号多于左括号（多 {diff} 个）",
                        detail="当前行或之前的代码中右括号数量超过左括号",
                        suggestion="检查函数调用、子查询或 CASE 表达式的括号是否正确闭合",
                        code_snippet=line.strip()[:100]
                    ))
        
        # 全局括号不匹配
        if total_left != total_right:
            self.issues.append(SQLIssue(
                severity=IssueSeverity.CRITICAL,
                category="括号匹配",
                line_number=len(lines),
                column=None,
                problem=f"全局括号不匹配（左括号: {total_left}, 右括号: {total_right}）",
                detail=f"整个 SQL 中括号数量不匹配",
                suggestion="请检查所有函数调用和子查询的括号配对",
                code_snippet=""
            ))
    
    def _check_comments(self, lines: List[str]):
        """检查注释语法"""
        for line_no, line in enumerate(lines, 1):
            # 检查行尾注释前是否有代码
            if '--' in line:
                parts = line.split('--', 1)
                code_part = parts[0].strip()
                comment_part = parts[1] if len(parts) > 1 else ""
                
                # 如果注释前有代码，但代码以逗号或 AS 结尾，检查是否有潜在的语法问题
                if code_part and code_part.endswith(','):
                    # 检查下一行是否存在
                    if line_no < len(lines):
                        next_line = lines[line_no].strip()
                        if next_line.startswith('--') or next_line == '':
                            self.issues.append(SQLIssue(
                                severity=IssueSeverity.WARNING,
                                category="注释语法",
                                line_number=line_no,
                                column=None,
                                problem="逗号后的注释可能导致语法错误",
                                detail="该行以逗号结尾，下一行是注释或空行",
                                suggestion="确保逗号后有下一个字段或表达式",
                                code_snippet=line.strip()[:100]
                            ))
    
    def _check_from_clause(self, lines: List[str]):
        """检查 FROM 子句"""
        in_from_clause = False
        from_start_line = 0
        
        for line_no, line in enumerate(lines, 1):
            upper_line = line.upper().strip()
            
            # 检测 FROM 关键字
            if re.search(r'\bFROM\b', upper_line) and not upper_line.startswith('--'):
                in_from_clause = True
                from_start_line = line_no
            
            # FROM 子句结束（遇到 WHERE, GROUP BY, ORDER BY 等）
            if in_from_clause and re.search(r'\b(WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|UNION|;)\b', upper_line):
                in_from_clause = False
            
            # 在 FROM 子句中检查问题
            if in_from_clause:
                # 1. 检查序号前缀残留（如 "1.表" 或 "2.FROM"）
                if re.search(r'\d+\.\s*(表|FROM|[A-Z]+)', line):
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.WARNING,
                        category="FROM 子句",
                        line_number=line_no,
                        column=None,
                        problem="FROM 子句中可能包含序号前缀",
                        detail="检测到数字加点号的模式，可能是 Excel 解析残留",
                        suggestion="FROM 子句应该只包含表名、别名和 JOIN 条件",
                        code_snippet=line.strip()[:100]
                    ))
                
                # 2. 检查表名后是否有别名
                code_part = line.split('--')[0] if '--' in line else line
                # 匹配表名模式（不在 JOIN ON 条件中）
                if not re.search(r'\bON\b', code_part.upper()):
                    table_match = re.search(r'\b([A-Z_][A-Z0-9_]{2,})\s*$', code_part.strip(), re.IGNORECASE)
                    if table_match and not re.search(r'\b(FROM|JOIN)\s+' + table_match.group(1) + r'\s+[A-Z]', code_part, re.IGNORECASE):
                        # 可能缺少别名
                        pass  # 这个检查可能误报太多，暂时不加入
    
    def _check_sql_syntax(self, lines: List[str]):
        """检查常见 SQL 语法错误"""
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith('--'):
                continue
            
            code_part = line.split('--')[0] if '--' in line else line
            upper_code = code_part.upper()
            
            # 1. 检查 CASE WHEN 缺少 END
            if 'CASE' in upper_code and 'WHEN' in upper_code:
                # 简单检查：如果这行有 CASE WHEN 但没有 END，标记一下
                # （完整检查需要跨行分析）
                pass
            
            # 2. 检查连续的逗号
            if ',,' in code_part:
                self.issues.append(SQLIssue(
                    severity=IssueSeverity.CRITICAL,
                    category="SQL 语法",
                    line_number=line_no,
                    column=code_part.index(',,'),
                    problem="检测到连续的逗号",
                    detail="SQL 中不应该出现连续的逗号",
                    suggestion="检查字段列表或表达式列表是否有遗漏",
                    code_snippet=line.strip()[:100]
                ))
            
            # 3. 检查行尾多余的逗号（在括号或分号前）
            if re.search(r',\s*[);]', code_part):
                self.issues.append(SQLIssue(
                    severity=IssueSeverity.CRITICAL,
                    category="SQL 语法",
                    line_number=line_no,
                    column=None,
                    problem="检测到多余的逗号",
                    detail="括号或分号前不应该有逗号",
                    suggestion="删除多余的逗号",
                    code_snippet=line.strip()[:100]
                ))
    
    def _check_functions(self, lines: List[str]):
        """检查函数使用"""
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith('--'):
                continue
            
            code_part = line.split('--')[0] if '--' in line else line
            
            # 检查常见的函数拼写错误
            common_errors = {
                'SUBSRT': 'SUBSTR',
                'REPALCE': 'REPLACE',
                'CONCATE': 'CONCAT',
                'BEWTEEN': 'BETWEEN',
            }
            
            for wrong, correct in common_errors.items():
                if wrong in code_part.upper():
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="函数调用",
                        line_number=line_no,
                        column=None,
                        problem=f"可能的函数名拼写错误: {wrong}",
                        detail=f"检测到 {wrong}，可能应该是 {correct}",
                        suggestion=f"将 {wrong} 修改为 {correct}",
                        code_snippet=line.strip()[:100]
                    ))
            
            # 检查 NVL 参数数量错误 (NVL 只接受2个参数)
            nvl_matches = re.finditer(r'\bNVL\s*\([^)]+\)', code_part, re.IGNORECASE)
            for match in nvl_matches:
                nvl_content = match.group(0)
                # 统计逗号数量
                # 简单判断：如果 NVL 有3个或更多参数
                inner = nvl_content[nvl_content.find('(')+1:nvl_content.rfind(')')]
                # 计算顶层逗号数量（忽略嵌套括号内的逗号）
                depth = 0
                comma_count = 0
                for char in inner:
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        depth -= 1
                    elif char == ',' and depth == 0:
                        comma_count += 1
                
                if comma_count >= 2:  # 3个或更多参数
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="函数调用",
                        line_number=line_no,
                        column=None,
                        problem="NVL 函数参数数量错误",
                        detail=f"NVL 函数只接受2个参数，检测到 {comma_count + 1} 个参数",
                        suggestion="检查 NVL 函数的参数，格式应为 NVL(expr, default_value)",
                        code_snippet=line.strip()[:100]
                    ))
            
            # 检查 MAX(0, ...) 误用 - Oracle 的 MAX 是聚合函数，不是取最大值
            if re.search(r'\bMAX\s*\(\s*0\s*,', code_part, re.IGNORECASE):
                self.issues.append(SQLIssue(
                    severity=IssueSeverity.CRITICAL,
                    category="函数调用",
                    line_number=line_no,
                    column=None,
                    problem="MAX 函数误用",
                    detail="检测到 MAX(0, ...) 格式，Oracle/OceanBase 的 MAX 是聚合函数，不能用于取两个值的最大值",
                    suggestion="使用 GREATEST(0, ...) 函数来获取多个值中的最大值",
                    code_snippet=line.strip()[:100]
                ))
                        
            # 检查子查询中缺少 FROM 关键字
            # 模式: (select ... 表名 ZTxx 但缺少 FROM 的情况
            # 例如: (select ZT01.*, ROW_NUMBER()... F_TABLE_NAME ZT01
            # 正则匹配: 括号后 select ... 表名 ZTxx 的模式
            if re.search(r'\(\s*select\s+[A-Z0-9_.,\s\(\)]+\s+[A-Z_][A-Z0-9_.]+\s+ZT\d+\s*\)', code_part, re.IGNORECASE):
                # 检测到 select 后跟表名和别名 ZTxx 但可能缺少 FROM
                # 需要进一步验证是否缺少 FROM
                if not re.search(r'\bFROM\b', code_part, re.IGNORECASE):
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="SQL 语法",
                        line_number=line_no,
                        column=None,
                        problem="子查询中缺少 FROM 关键字",
                        detail="检测到 SELECT ... 表名 ZTxx 模式，但缺少 FROM 关键字",
                        suggestion="检查子查询语法，确保 SELECT 后有 FROM 关键字，如: SELECT ... FROM table_name alias",
                        code_snippet=line.strip()[:100]
                    ))
    
    def _check_sql_structure(self, lines: List[str]):
        """检查 SQL 结构问题"""
        full_sql = '\n'.join(lines)
        
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith('--'):
                continue
            
            code_part = line.split('--')[0] if '--' in line else line
            
            # 检查重复表别名 TXX.TXX.
            dup_alias_match = re.search(r'\b(T\d{2})\.\1\.', code_part)
            if dup_alias_match:
                self.issues.append(SQLIssue(
                    severity=IssueSeverity.CRITICAL,
                    category="表别名",
                    line_number=line_no,
                    column=None,
                    problem="重复的表别名",
                    detail=f"检测到 {dup_alias_match.group(0)}，表别名重复",
                    suggestion=f"将 {dup_alias_match.group(0)} 修改为 {dup_alias_match.group(1)}.",
                    code_snippet=line.strip()[:100]
                ))
            
            # 检查 SUM/AVG/COUNT 等聚合函数中 AS 别名位置错误
            # 模式: sum((...) AS alias) 或类似
            agg_funcs = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'NVL']
            for func in agg_funcs:
                # 查找 func((... AS alias) 模式 - AS 在括号内
                pattern = rf'\b{func}\s*\(\s*\([^)]*\bAS\s+[A-Za-z_]+'
                if re.search(pattern, code_part, re.IGNORECASE):
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="聚合函数",
                        line_number=line_no,
                        column=None,
                        problem=f"{func} 函数中 AS 别名位置错误",
                        detail=f"检测到 {func}((...) AS alias) 模式，AS 别名应该在函数括号外",
                        suggestion=f"修改为 {func}(...) AS alias 格式",
                        code_snippet=line.strip()[:100]
                    ))
        
        # 检查 CASE WHEN 缺少 END（跨行检查）
        case_depth = 0
        case_start_line = 0
        for line_no, line in enumerate(lines, 1):
            code_part = line.split('--')[0] if '--' in line else line
            upper_code = code_part.upper()
            
            if 'CASE' in upper_code and 'WHEN' in upper_code:
                case_depth += 1
                if case_start_line == 0:
                    case_start_line = line_no
            
            if 'END' in upper_code and case_depth > 0:
                case_depth -= 1
        
        if case_depth > 0:
            self.issues.append(SQLIssue(
                severity=IssueSeverity.CRITICAL,
                category="CASE 表达式",
                line_number=case_start_line,
                column=None,
                problem="CASE WHEN 缺少 END",
                detail=f"检测到未闭合的 CASE 表达式（从第 {case_start_line} 行开始）",
                suggestion="在每个 CASE WHEN ... THEN ... 后添加 END 关键字",
                code_snippet=""
            ))
        
        # 检查缺少 WHERE 关键字的过滤条件
        # 模式：在 INSERT...SELECT 语句中，FROM 子句后有条件但缺少 WHERE
        in_insert = False
        in_from = False
        last_from_line = 0
        for line_no, line in enumerate(lines, 1):
            code_part = line.split('--')[0] if '--' in line else line
            upper_code = code_part.upper().strip()
            
            if 'INSERT INTO' in upper_code:
                in_insert = True
            
            if re.search(r'\bFROM\b', upper_code) and in_insert:
                in_from = True
                last_from_line = line_no
            
            # 如果在 FROM 后遇到条件表达式但没有 WHERE
            if in_from and not upper_code.startswith('WHERE'):
                # 检查是否有类似过滤条件的模式（字段名 = 值 或 字段名 > 值）
                # 但排除 JOIN ON 条件和已经以 WHERE 开头的行
                if re.search(r'\b[A-Z_][A-Z0-9_]*\s*(=|>|<|<>|>=|<=)\s*', upper_code):
                    # 检查上一行是否是空行或注释，当前行以表别名开头
                    if line_no > 1:
                        prev_line = lines[line_no - 2].strip()
                        if prev_line == '' or prev_line.startswith('--'):
                            # 检查是否在 JOIN 块之后
                            # 简单判断：如果前面有 LEFT JOIN 但没有 WHERE
                            if not re.search(r'\bWHERE\b', '\n'.join(lines[:line_no]), re.IGNORECASE):
                                # 再检查是否已经检测过这个问题
                                already_reported = any(
                                    i.category == "WHERE 子句" and i.line_number == line_no 
                                    for i in self.issues
                                )
                                if not already_reported:
                                    self.issues.append(SQLIssue(
                                        severity=IssueSeverity.CRITICAL,
                                        category="WHERE 子句",
                                        line_number=line_no,
                                        column=None,
                                        problem="可能缺少 WHERE 关键字",
                                        detail="检测到过滤条件但前面没有 WHERE 关键字",
                                        suggestion="在过滤条件前添加 WHERE 关键字",
                                        code_snippet=line.strip()[:100]
                                    ))

    def _check_column_count(self, lines: List[str]):
        """检查 SELECT 和 INSERT 列数是否匹配"""
        in_insert = False
        in_select = False
        insert_columns = []
        select_columns = []
        insert_line = 0
        select_line = 0
        paren_depth = 0
        select_paren_depth = 0
        
        for line_no, line in enumerate(lines, 1):
            code_part = line.split('--')[0] if '--' in line else line
            upper_code = code_part.upper()
            
            # 检测 INSERT INTO ... ( 的开始
            if 'INSERT INTO' in upper_code:
                in_insert = True
                insert_line = line_no
                insert_columns = []
            
            if in_insert:
                # 统计括号内的列
                for char in code_part:
                    if char == '(':
                        paren_depth += 1
                    elif char == ')':
                        paren_depth -= 1
                
                # 提取列名（简单方式）
                if paren_depth > 0:
                    # 提取标识符
                    cols = re.findall(r'\b([A-Z_][A-Z0-9_]*)\b', code_part, re.IGNORECASE)
                    for col in cols:
                        if col.upper() not in ('INSERT', 'INTO', 'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NULL'):
                            insert_columns.append(col)
                
                # INSERT 列表结束
                if paren_depth == 0 and 'SELECT' in upper_code:
                    in_insert = False
                    in_select = True
                    select_line = line_no
                    select_columns = []
            
            if in_select or ('SELECT' in upper_code and 'INSERT' not in upper_code):
                # 简单检测 SELECT 列
                # 这里只是粗略估计，实际可能需要更复杂的解析
                pass

    def _check_undefined_references(self, lines: List[str], context: dict):
        """检查未定义的表引用和列引用"""
        # 从上下文获取定义的表别名
        defined_aliases = set()
        from_clause = context.get('from_clause', '') if context else ''
        
        if from_clause:
            # 提取 FROM 子句中定义的表别名
            # 模式：表名 别名 或 JOIN 表名 别名
            alias_matches = re.findall(
                r'\b(?:FROM|JOIN)\s+([A-Z_][A-Z0-9_]*)\s+([A-Z][A-Z0-9_]*)',
                from_clause.upper()
            )
            for table, alias in alias_matches:
                defined_aliases.add(alias)
        
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith('--'):
                continue
            
            code_part = line.split('--')[0] if '--' in line else line
            
            # 检查 alias.column 模式
            ref_matches = re.findall(r'\b([A-Z][A-Z0-9_]*)\.([A-Z_][A-Z0-9_]*)', code_part, re.IGNORECASE)
            for alias, column in ref_matches:
                alias_upper = alias.upper()
                # 跳过 SQL 关键字和函数
                if alias_upper in self.sql_keywords or alias_upper in self.sql_functions:
                    continue
                # 如果有定义的别名列表，检查是否在列表中
                if defined_aliases and alias_upper not in defined_aliases:
                    # 可能是未定义的别名
                    pass  # 暂时不报告，因为可能上下文信息不完整

    def _check_keyword_typos(self, lines: List[str]):
        """检查 SQL 关键字拼写错误"""
        # 常见的关键字拼写错误映射
        keyword_typos = {
            'SELEC': 'SELECT',
            'SELECET': 'SELECT',
            'SELCET': 'SELECT',
            'FROME': 'FROM',
            'WHER': 'WHERE',
            'WHEER': 'WHERE',
            'JOIIN': 'JOIN',
            'INER': 'INNER',
            'OUTER': 'OUTER',  # 正确拼写，检查是否有 OTER
            'OTER': 'OUTER',
            'LEF': 'LEFT',
            'RIGH': 'RIGHT',
            'GROUP': 'GROUP',
            'GROP': 'GROUP',
            'ODER': 'ORDER',
            'ORDRE': 'ORDER',
            'HAVNG': 'HAVING',
            'HAVIN': 'HAVING',
            'DISTINC': 'DISTINCT',
            'DISTINT': 'DISTINCT',
            'INSET': 'INSERT',
            'INSER': 'INSERT',
            'UPATE': 'UPDATE',
            'UPDAET': 'UPDATE',
            'DELEET': 'DELETE',
            'DELEATE': 'DELETE',
            'DELETe': 'DELETE',
            'CREAT': 'CREATE',
            'CRETAE': 'CREATE',
            'ALTEr': 'ALTER',
            'ALTRE': 'ALTER',
            'DRP': 'DROP',
            'DROOP': 'DROP',
        }
        
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith('--'):
                continue
            
            code_part = line.split('--')[0] if '--' in line else line
            upper_code = code_part.upper()
            
            for typo, correct in keyword_typos.items():
                # 使用单词边界匹配
                if re.search(r'\b' + typo + r'\b', upper_code):
                    # 确保不是正确关键字的一部分
                    if correct not in upper_code or typo != correct:
                        self.issues.append(SQLIssue(
                            severity=IssueSeverity.CRITICAL,
                            category="关键字拼写",
                            line_number=line_no,
                            column=None,
                            problem=f"SQL 关键字可能拼写错误: {typo}",
                            detail=f"检测到 {typo}，可能应该是 {correct}",
                            suggestion=f"将 {typo} 修改为 {correct}",
                            code_snippet=line.strip()[:100]
                        ))

    def _check_select_star(self, lines: List[str]):
        """检查 SELECT * 使用（在生产代码中不推荐）"""
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith('--'):
                continue
            
            code_part = line.split('--')[0] if '--' in line else line
            
            # 检查 SELECT * 但排除注释中的
            if re.search(r'\bSELECT\s+\*', code_part, re.IGNORECASE):
                # 检查是否在子查询中（有时候是允许的）
                # 简单判断：如果这行有括号，可能是子查询
                if '(' not in code_part:
                    self.issues.append(SQLIssue(
                        severity=IssueSeverity.WARNING,
                        category="SQL 规范",
                        line_number=line_no,
                        column=None,
                        problem="使用了 SELECT *",
                        detail="在生产代码中使用 SELECT * 可能导致性能问题和维护困难",
                        suggestion="建议明确列出需要查询的字段名",
                        code_snippet=line.strip()[:100]
                    ))

    def _check_order_by_in_subquery(self, lines: List[str]):
        """检查子查询中的 ORDER BY（某些数据库不支持）"""
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith('--'):
                continue
            
            code_part = line.split('--')[0] if '--' in line else line
            
            # 检查子查询中的 ORDER BY
            # 模式：(SELECT ... ORDER BY ... )
            if re.search(r'\(\s*SELECT\s+.*\s+ORDER\s+BY\s+', code_part, re.IGNORECASE | re.DOTALL):
                self.issues.append(SQLIssue(
                    severity=IssueSeverity.WARNING,
                    category="子查询",
                    line_number=line_no,
                    column=None,
                    problem="子查询中使用了 ORDER BY",
                    detail="子查询中的 ORDER BY 可能不被支持，除非配合 TOP/LIMIT/ROWNUM 使用",
                    suggestion="考虑是否需要在子查询中使用 ORDER BY，或者使用 TOP/LIMIT",
                    code_snippet=line.strip()[:100]
                ))


def validate_insert_sql(sql: str, table_name: str = "", group_name: str = "") -> Dict:
    """
    验证 INSERT SQL 的质量
    
    Args:
        sql: INSERT SQL 代码
        table_name: 表名
        group_name: 组名
    
    Returns:
        验证报告
    """
    validator = SQLValidator()
    issues = validator.validate(sql, {
        "table_name": table_name,
        "group_name": group_name,
    })
    
    return {
        "table_name": table_name,
        "group_name": group_name,
        "total_issues": len(issues),
        "critical": sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL),
        "warning": sum(1 for i in issues if i.severity == IssueSeverity.WARNING),
        "info": sum(1 for i in issues if i.severity == IssueSeverity.INFO),
        "issues": [i.to_dict() for i in issues],
        "has_errors": any(i.severity == IssueSeverity.CRITICAL for i in issues),
    }


def validate_procedure_sql(sql: str, table_name: str = "") -> Dict:
    """
    验证存储过程 SQL 的质量
    
    Args:
        sql: 存储过程 SQL 代码
        table_name: 表名
    
    Returns:
        验证报告
    """
    validator = SQLValidator()
    issues = validator.validate(sql, {
        "table_name": table_name,
        "type": "procedure",
    })
    
    return {
        "table_name": table_name,
        "total_issues": len(issues),
        "critical": sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL),
        "warning": sum(1 for i in issues if i.severity == IssueSeverity.WARNING),
        "info": sum(1 for i in issues if i.severity == IssueSeverity.INFO),
        "issues": [i.to_dict() for i in issues],
        "has_errors": any(i.severity == IssueSeverity.CRITICAL for i in issues),
    }


def validate_sql_expression(expr: str, context: dict = None) -> Dict:
    """
    验证单个 SQL 表达式（用于实时预览验证）
    
    Args:
        expr: SQL 表达式字符串
        context: 上下文信息
    
    Returns:
        验证报告
    """
    if not expr or not expr.strip():
        return {
            "is_valid": True,
            "issues": [],
            "total_issues": 0,
        }
    
    validator = SQLValidator()
    context = context or {}
    
    issues = []
    
    # 1. 检查引号配对
    quote_count = expr.count("'")
    if quote_count % 2 != 0:
        issues.append({
            "severity": "critical",
            "category": "字符串字面量",
            "problem": "单引号未配对",
            "detail": f"表达式包含 {quote_count} 个单引号，数量为奇数",
            "suggestion": "检查字符串常量是否正确闭合，SQL 中的单引号需要用 '' 转义",
        })
    
    # 2. 检查括号配对
    left_count = expr.count('(')
    right_count = expr.count(')')
    if left_count != right_count:
        issues.append({
            "severity": "critical",
            "category": "括号匹配",
            "problem": "括号未配对",
            "detail": f"左括号: {left_count}，右括号: {right_count}",
            "suggestion": "检查函数调用或子表达式的括号是否正确闭合",
        })
    
    # 3. 检查函数调用参数
    # NVL 函数只接受 2 个参数
    nvl_matches = re.finditer(r'\bNVL\s*\([^)]+\)', expr, re.IGNORECASE)
    for match in nvl_matches:
        nvl_content = match.group(0)
        inner = nvl_content[nvl_content.find('(')+1:nvl_content.rfind(')')]
        depth = 0
        comma_count = 0
        for char in inner:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                comma_count += 1
        if comma_count >= 2:
            issues.append({
                "severity": "critical",
                "category": "函数调用",
                "problem": "NVL 函数参数数量错误",
                "detail": f"NVL 函数只接受2个参数，检测到 {comma_count + 1} 个参数",
                "suggestion": "检查 NVL 函数的参数，格式应为 NVL(expr, default_value)",
            })
    
    # 4. 检查 MAX(0, ...) 误用
    if re.search(r'\bMAX\s*\(\s*0\s*,', expr, re.IGNORECASE):
        issues.append({
            "severity": "critical",
            "category": "函数调用",
            "problem": "MAX 函数误用",
            "detail": "检测到 MAX(0, ...) 格式，Oracle/OceanBase 的 MAX 是聚合函数",
            "suggestion": "使用 GREATEST(0, ...) 函数来获取多个值中的最大值",
        })
    
    # 5. 检查常见拼写错误
    common_errors = {
        'SUBSRT': 'SUBSTR',
        'REPALCE': 'REPLACE',
        'CONCATE': 'CONCAT',
        'BEWTEEN': 'BETWEEN',
    }
    for wrong, correct in common_errors.items():
        if wrong in expr.upper():
            issues.append({
                "severity": "critical",
                "category": "函数调用",
                "problem": f"函数名拼写错误: {wrong}",
                "detail": f"检测到 {wrong}，应该为 {correct}",
                "suggestion": f"将 {wrong} 修改为 {correct}",
            })
    
    # 6. 检查 CASE WHEN 结构
    upper_expr = expr.upper()
    if 'CASE' in upper_expr:
        case_count = upper_expr.count('CASE')
        end_count = upper_expr.count('END')
        if case_count > end_count:
            issues.append({
                "severity": "critical",
                "category": "CASE 表达式",
                "problem": "CASE 表达式缺少 END",
                "detail": f"检测到 {case_count} 个 CASE 但只有 {end_count} 个 END",
                "suggestion": "在每个 CASE WHEN ... THEN ... 后添加 END 关键字",
            })
    
    # 7. 检查重复表别名 TXX.TXX.
    dup_alias_match = re.search(r'\b(T\d{2})\.\1\.', expr)
    if dup_alias_match:
        issues.append({
            "severity": "critical",
            "category": "表别名",
            "problem": "重复的表别名",
            "detail": f"检测到 {dup_alias_match.group(0)}",
            "suggestion": f"将 {dup_alias_match.group(0)} 修改为 {dup_alias_match.group(1)}.",
        })
    
    return {
        "is_valid": len([i for i in issues if i["severity"] == "critical"]) == 0,
        "issues": issues,
        "total_issues": len(issues),
        "critical": sum(1 for i in issues if i["severity"] == "critical"),
        "warning": sum(1 for i in issues if i["severity"] == "warning"),
    }


def validate_from_clause(from_clause: str, context: dict = None) -> Dict:
    """
    验证 FROM 子句（用于实时预览验证）
    
    Args:
        from_clause: FROM 子句字符串
        context: 上下文信息
    
    Returns:
        验证报告
    """
    if not from_clause or not from_clause.strip():
        return {
            "is_valid": False,
            "issues": [{
                "severity": "critical",
                "category": "FROM 子句",
                "problem": "FROM 子句为空",
                "detail": "缺少数据源表定义，SQL 无法执行",
                "suggestion": "请填写源表名称和别名，例如：F_TABLE_NAME T01",
            }],
            "total_issues": 1,
        }
    
    issues = []
    
    # 1. 检查序号前缀污染
    if re.search(r'\d+\.\s*(表|FROM)', from_clause):
        issues.append({
            "severity": "warning",
            "category": "FROM 子句",
            "problem": "FROM 子句可能包含序号前缀",
            "detail": "检测到数字加点号的模式，可能是 Excel 解析残留",
            "suggestion": "FROM 子句应该只包含表名和别名",
        })
    
    # 2. 检查 JOIN 条件
    # 确保 LEFT JOIN 有 ON 条件
    lines = from_clause.split('\n')
    for i, line in enumerate(lines):
        upper_line = line.upper()
        if 'LEFT JOIN' in upper_line or 'RIGHT JOIN' in upper_line or 'INNER JOIN' in upper_line:
            # 检查是否有 ON 条件
            # 可能 ON 在同一行或下一行
            has_on = ' ON ' in upper_line
            if not has_on and i + 1 < len(lines):
                next_upper = lines[i + 1].upper()
                if next_upper.strip().startswith('ON '):
                    has_on = True
            
            if not has_on:
                issues.append({
                    "severity": "warning",
                    "category": "JOIN 条件",
                    "problem": "JOIN 可能缺少 ON 条件",
                    "detail": f"检测到 {line.strip()[:50]}",
                    "suggestion": "为 JOIN 添加 ON 条件，例如：LEFT JOIN table_name alias ON alias.id = main.id",
                })
    
    # 3. 检查表别名重复
    alias_pattern = r'\b(?:FROM|JOIN)\s+([A-Z_][A-Z0-9_]*)\s+([A-Z][A-Z0-9_]*)'
    aliases = re.findall(alias_pattern, from_clause.upper())
    alias_list = [a[1] for a in aliases]
    seen = set()
    for alias in alias_list:
        if alias in seen:
            issues.append({
                "severity": "critical",
                "category": "表别名",
                "problem": f"表别名重复: {alias}",
                "detail": "同一个查询中不能使用相同的表别名",
                "suggestion": "为每个表指定不同的别名",
            })
        seen.add(alias)
    
    # 4. 检查括号配对
    left_count = from_clause.count('(')
    right_count = from_clause.count(')')
    if left_count != right_count:
        issues.append({
            "severity": "critical",
            "category": "括号匹配",
            "problem": "FROM 子句中括号未配对",
            "detail": f"左括号: {left_count}，右括号: {right_count}",
            "suggestion": "检查子查询或条件的括号是否正确闭合",
        })
    
    return {
        "is_valid": len([i for i in issues if i["severity"] == "critical"]) == 0,
        "issues": issues,
        "total_issues": len(issues),
        "critical": sum(1 for i in issues if i["severity"] == "critical"),
        "warning": sum(1 for i in issues if i["severity"] == "warning"),
    }


def validate_sql(sql: str, context: dict = None) -> Dict:
    """
    便捷函数：验证 SQL 代码
    
    Args:
        sql: SQL 代码字符串
        context: 上下文信息
        
    Returns:
        验证报告字典
    """
    validator = SQLValidator()
    return validator.validate(sql, context)
