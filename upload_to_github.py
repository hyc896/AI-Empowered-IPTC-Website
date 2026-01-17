#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
上传一期项目到GitHub新仓库
仓库地址: https://github.com/hyc896/AI-Empowered-IPTC-Website.git
注意: 已通过.gitignore排除 global-news-dashboard 前端
"""

import subprocess
import os
import sys

def run_command(cmd, description):
    """执行命令并输出结果"""
    print(f"\n{'='*60}")
    print(f"[{description}]")
    print(f"{'='*60}")
    print(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode != 0:
            print(f"[警告] 命令返回非零状态码: {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"[错误] 执行失败: {str(e)}")
        return False

def main():
    # 切换到项目目录
    project_dir = r"D:\AI-Empowered IPTC Website\一期"
    os.chdir(project_dir)
    print(f"当前工作目录: {os.getcwd()}")
    
    print("\n" + "="*60)
    print("上传一期项目到GitHub新仓库")
    print("仓库地址: https://github.com/hyc896/AI-Empowered-IPTC-Website.git")
    print("注意: 已排除 global-news-dashboard 前端")
    print("="*60)
    
    # Step 1: 检查Git状态
    run_command("git status", "Step 1: 检查Git仓库状态")
    
    # Step 2: 添加所有更改
    run_command("git add .", "Step 2: 添加所有更改到暂存区")
    
    # Step 3: 提交更改
    run_command(
        'git commit -m "Initial commit: Upload Phase 1 project (exclude global-news-dashboard)"',
        "Step 3: 提交更改"
    )
    
    # Step 4: 移除旧的origin（如果存在）
    run_command("git remote remove origin", "Step 4: 移除旧的远程仓库（如果存在）")
    
    # Step 5: 添加新的远程仓库
    success = run_command(
        "git remote add origin https://github.com/hyc896/AI-Empowered-IPTC-Website.git",
        "Step 5: 添加新的远程仓库"
    )
    
    # Step 6: 确保在main分支
    run_command("git branch -M main", "Step 6: 确保使用main分支")
    
    # Step 7: 推送到GitHub
    print("\n" + "="*60)
    print("[Step 7: 推送到GitHub（首次推送）]")
    print("="*60)
    print("注意: 首次推送使用 -f 强制推送")
    
    success = run_command(
        "git push -u origin main -f",
        "推送到远程仓库"
    )
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] 上传完成！")
        print("="*60)
        print("远程仓库: https://github.com/hyc896/AI-Empowered-IPTC-Website.git")
        print("\n已排除的内容:")
        print("- global-news-dashboard/ 前端项目")
        print("- node_modules/")
        print("- __pycache__/")
        print("- data/chromadb/ 和 data/chromadb_mp/")
        print("- logs/")
        print("- .env 环境变量")
        print("- full_database_dump.sql")
        print("- 其他 .gitignore 中定义的文件")
    else:
        print("\n" + "="*60)
        print("[错误] 推送失败")
        print("="*60)
        print("可能原因:")
        print("1. 网络连接问题")
        print("2. GitHub 凭据未配置")
        print("3. 仓库访问权限不足")
        print("\n请手动执行以下命令:")
        print("cd \"D:\\AI-Empowered IPTC Website\\一期\"")
        print("git push -u origin main -f")
    
    # Step 8: 查看远程仓库配置
    run_command("git remote -v", "Step 8: 验证远程仓库配置")
    
    print("\n按任意键退出...")
    input()

if __name__ == "__main__":
    main()
