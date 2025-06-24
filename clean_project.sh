#!/bin/bash
# 项目清理脚本 - 清理临时文件、缓存文件、日志文件等

echo "开始清理项目文件..."

# 清理 Python 缓存文件
echo "清理 Python 缓存文件..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# 清理日志文件
echo "清理日志文件..."
rm -rf logs 2>/dev/null || true
find . -name "*.log" -not -path "./.git/*" -delete 2>/dev/null || true

# 清理系统文件
echo "清理系统文件..."
find . -name ".DS_Store" -delete 2>/dev/null || true

# 清理临时文件和备份文件
echo "清理临时文件和备份文件..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
find . -name "*.orig" -delete 2>/dev/null || true

# 清理编辑器临时文件
echo "清理编辑器临时文件..."
find . -name ".*.swp" -delete 2>/dev/null || true
find . -name ".*.swo" -delete 2>/dev/null || true

# 清理测试覆盖率文件
echo "清理测试覆盖率文件..."
find . -name ".coverage" -delete 2>/dev/null || true
find . -name "coverage.xml" -delete 2>/dev/null || true
rm -rf htmlcov 2>/dev/null || true

echo "项目清理完成！"

# 显示清理后的状态
echo ""
echo "检查是否还有遗漏的文件..."
remaining=$(find . -name "__pycache__" -o -name "*.pyc" -o -name "*.pyo" -o -name ".DS_Store" -o -name "*.tmp" -o -name "*.swp" -o -name "*.bak" -o -name "*~" -not -path "./.git/*" 2>/dev/null)

if [ -z "$remaining" ]; then
    echo "✅ 所有临时文件已清理完成！"
else
    echo "⚠️  还有以下文件未清理："
    echo "$remaining"
fi 