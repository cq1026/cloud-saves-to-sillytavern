#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷操作菜单
提供简单的命令行界面进行备份和恢复操作
"""

import sys
from pathlib import Path

from config import load_config, validate_config
from backup import BackupManager
from restore import RestoreManager
from logger import setup_logger
import logging

logger = logging.getLogger(__name__)


def show_menu():
    """显示主菜单"""
    print()
    print("=" * 60)
    print("       SillyTavern 云备份工具 - 快捷操作菜单")
    print("=" * 60)
    print()
    print("  📦 备份操作")
    print("    1. 执行手动备份")
    print("    2. 列出并拉取备份版本")
    print()
    print("  🛠️  存档管理")
    print("    3. 修改存档描述")
    print("    4. 删除云端存档")
    print("    5. 比较存档差异")
    print()
    print("  ❌ 退出")
    print("    0. 退出程序")
    print()


def manual_backup(config):
    """执行手动备份"""
    print()
    print("-" * 60)
    print("开始手动备份...")
    print("-" * 60)
    
    manager = BackupManager(config)
    success = manager.run_backup()
    
    if success:
        print()
        print("✅ 备份成功！")
        print()
    else:
        print()
        print("❌ 备份失败，请查看日志")
        print()
    
    input("按回车键继续...")


def list_and_restore(config):
    """列出备份版本并拉取"""
    print()
    print("-" * 60)
    print("备份版本列表")
    print("-" * 60)
    
    manager = RestoreManager(config)
    
    # 初始化仓库
    if not manager.init_repo():
        print("❌ 无法连接到备份仓库")
        input("按回车键继续...")
        return
    
    # 列出备份
    backups = manager.list_backups(max_count=20)
    if not backups:
        print("❌ 没有可用的备份")
        input("按回车键继续...")
        return
    
    print()
    print("序号  提交哈希   时间                    描述")
    print("-" * 80)
    for i, (hash_val, msg, dt) in enumerate(backups, 1):
        # 只显示第一行（时间戳）
        first_line = msg.split('\n')[0]
        print(f"{i:2d}.   {hash_val}    {dt.strftime('%Y-%m-%d %H:%M:%S')}  {first_line}")
        
        # 如果有详细信息，显示在下一行
        if '\n' in msg:
            details = msg.split('\n\n')
            if len(details) > 1:
                # 显示变更摘要（缩进）
                for detail in details[1:]:
                    if detail.strip():
                        print(f"       → {detail.strip()}")
        print()  # 空行分隔
    print("-" * 80)
    
    # 选择版本
    while True:
        choice = input("请选择要拉取的版本（输入序号，或 'q' 取消）: ").strip()
        if choice.lower() == 'q':
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                break
            else:
                print("❌ 无效的序号，请重新输入")
        except ValueError:
            print("❌ 请输入数字")
    
    selected_hash = backups[index][0]
    selected_msg = backups[index][1]
    selected_time = backups[index][2]
    
    print()
    print(f"您选择的版本: {selected_hash} - {selected_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"描述: {selected_msg}")
    print()
    
    # 拉取到本地
    print("正在拉取备份到 /backup/data/ ...")
    try:
        # 检出指定版本
        manager.repo.git.checkout(selected_hash)
        
        # 检查 data 目录是否存在
        backup_data_path = manager.repo_path / 'data'
        if backup_data_path.exists():
            print()
            print("=" * 60)
            print("✅ 备份已拉取到容器内路径：/backup/data/")
            print()
            print("📂 在宿主机上的位置：/opt/cloud-saves/backup-repo/data/")
            print()
            print("⚠️  接下来请手动操作：")
            print("   1. 停止 SillyTavern 服务")
            print("   2. 备份当前 /opt/SillyTavern/data 目录（可选）")
            print("   3. 复制 /opt/cloud-saves/backup-repo/data/ 的内容")
            print("      到 /opt/SillyTavern/data/")
            print("   4. 重启 SillyTavern 服务")
            print()
            print("命令示例：")
            print("  # 备份当前数据（可选）")
            print("  mv /opt/SillyTavern/data /opt/SillyTavern/data.backup")
            print()
            print("  # 复制恢复的数据")
            print("  cp -r /opt/cloud-saves/backup-repo/data /opt/SillyTavern/")
            print("=" * 60)
        else:
            print()
            print("❌ 备份中未找到 data 目录，可能是旧版本备份")
            print("   备份内容在：/opt/cloud-saves/backup-repo/")
        
        # 返回到最新版本
        manager.repo.git.checkout('HEAD')
        
    except Exception as e:
        print(f"❌ 拉取失败: {e}")
    
    print()
    input("按回车键继续...")


def edit_commit_message(config):
    """修改存档描述"""
    print()
    print("-" * 60)
    print("修改存档描述")
    print("-" * 60)
    
    manager = RestoreManager(config)
    
    if not manager.init_repo():
        print("❌ 无法连接到备份仓库")
        input("按回车键继续...")
        return
    
    backups = manager.list_backups(max_count=20)
    if not backups:
        print("❌ 没有可用的备份")
        input("按回车键继续...")
        return
    
    # 显示列表
    print()
    print("序号  提交哈希   时间                    当前描述")
    print("-" * 80)
    for i, (hash_val, msg, dt) in enumerate(backups, 1):
        first_line = msg.split('\n')[0]
        print(f"{i:2d}.   {hash_val}    {dt.strftime('%Y-%m-%d %H:%M:%S')}  {first_line}")
    print()
    
    # 选择要编辑的版本
    while True:
        choice = input("请选择要修改的版本（输入序号，或 'q' 取消）: ").strip()
        if choice.lower() == 'q':
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                break
            else:
                print("❌ 无效的序号")
        except ValueError:
            print("❌ 请输入数字")
    
    selected_hash = backups[index][0]
    old_msg = backups[index][1]
    
    print()
    print(f"当前完整描述：")
    print("-" * 60)
    print(old_msg)
    print("-" * 60)
    print()
    
    # 输入新描述
    print("请输入新的描述（可多行，输入空行结束）：")
    new_lines = []
    while True:
        line = input()
        if not line:
            break
        new_lines.append(line)
    
    if not new_lines:
        print("❌ 描述不能为空")
        input("按回车键继续...")
        return
    
    new_msg = '\n'.join(new_lines)
    
    # 确认修改
    print()
    print("新的描述：")
    print("-" * 60)
    print(new_msg)
    print("-" * 60)
    print()
    
    confirm = input("确认修改？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        input("按回车键继续...")
        return
    
    try:
        # 使用 git commit --amend 修改最近的提交（如果是最新的）
        # 或使用 git rebase -i 修改历史提交
        current_branch = manager.repo.active_branch.name
        
        if index == 0:
            # 最新的提交，可以直接 amend
            manager.repo.git.commit('--amend', '-m', new_msg)
            print("✅ 描述已更新")
            
            # 强制推送到远程
            print("正在推送到远程...")
            manager.repo.git.push('origin', current_branch, '--force')
            print("✅ 已同步到云端")
        else:
            print()
            print("⚠️  修改历史提交需要重写 Git 历史")
            print("   这会影响所有后续提交，建议谨慎操作")
            print()
            confirm2 = input("确认继续？(y/n): ").strip().lower()
            if confirm2 != 'y':
                print("已取消")
                input("按回车键继续...")
                return
            
            # 使用 filter-branch 或 rebase -i（这里简化处理）
            print("❌ 暂不支持修改历史提交，请联系开发者")
            print("   建议：删除旧存档，重新创建")
    
    except Exception as e:
        print(f"❌ 修改失败: {e}")
    
    print()
    input("按回车键继续...")


def delete_backup(config):
    """删除云端存档"""
    print()
    print("-" * 60)
    print("删除云端存档")
    print("-" * 60)
    print()
    print("⚠️  警告：此操作将永久删除选定的备份！")
    print()
    
    manager = RestoreManager(config)
    
    if not manager.init_repo():
        print("❌ 无法连接到备份仓库")
        input("按回车键继续...")
        return
    
    backups = manager.list_backups(max_count=20)
    if not backups:
        print("❌ 没有可用的备份")
        input("按回车键继续...")
        return
    
    print()
    print("序号  提交哈希   时间                    描述")
    print("-" * 80)
    for i, (hash_val, msg, dt) in enumerate(backups, 1):
        first_line = msg.split('\n')[0]
        print(f"{i:2d}.   {hash_val}    {dt.strftime('%Y-%m-%d %H:%M:%S')}  {first_line}")
    print()
    
    # 选择要删除的版本
    while True:
        choice = input("请选择要删除的版本（输入序号，或 'q' 取消）: ").strip()
        if choice.lower() == 'q':
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                break
            else:
                print("❌ 无效的序号")
        except ValueError:
            print("❌ 请输入数字")
    
    selected_hash = backups[index][0]
    selected_msg = backups[index][1]
    
    print()
    print(f"将要删除: {selected_hash}")
    print(f"描述: {selected_msg.split(chr(10))[0]}")
    print()
    print("⚠️  此操作不可逆！")
    print()
    
    confirm = input("确认删除？请输入 'DELETE' 确认: ").strip()
    if confirm != 'DELETE':
        print("已取消")
        input("按回车键继续...")
        return
    
    try:
        # 删除提交（使用 git rebase）
        if index == 0:
            # 删除最新提交
            manager.repo.git.reset('--hard', 'HEAD~1')
            print("✅ 本地提交已删除")
            
            # 强制推送
            print("正在同步到云端...")
            current_branch = manager.repo.active_branch.name
            manager.repo.git.push('origin', current_branch, '--force')
            print("✅ 云端存档已删除")
        else:
            print("❌ 暂不支持删除历史提交")
            print("   如需删除，请使用 git rebase -i")
    
    except Exception as e:
        print(f"❌ 删除失败: {e}")
    
    print()
    input("按回车键继续...")


def compare_diff(config):
    """比较存档与当前数据的差异"""
    print()
    print("-" * 60)
    print("比较存档差异")
    print("-" * 60)
    
    manager = RestoreManager(config)
    backup_manager = BackupManager(config)
    
    if not manager.init_repo():
        print("❌ 无法连接到备份仓库")
        input("按回车键继续...")
        return
    
    backups = manager.list_backups(max_count=20)
    if not backups:
        print("❌ 没有可用的备份")
        input("按回车键继续...")
        return
    
    print()
    print("序号  提交哈希   时间                    描述")
    print("-" * 80)
    for i, (hash_val, msg, dt) in enumerate(backups, 1):
        first_line = msg.split('\n')[0]
        print(f"{i:2d}.   {hash_val}    {dt.strftime('%Y-%m-%d %H:%M:%S')}  {first_line}")
    print()
    
    # 选择要比较的版本
    while True:
        choice = input("请选择要比较的版本（输入序号，或 'q' 取消）: ").strip()
        if choice.lower() == 'q':
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                break
            else:
                print("❌ 无效的序号")
        except ValueError:
            print("❌ 请输入数字")
    
    selected_hash = backups[index][0]
    
    print()
    print("正在分析差异...")
    
    try:
        # 检出选定版本
        manager.repo.git.checkout(selected_hash)
        
        # 比较两个目录
        backup_data = manager.repo_path / 'data'
        current_data = backup_manager.data_path
        
        if not backup_data.exists():
            print("❌ 备份中未找到 data 目录")
            manager.repo.git.checkout('HEAD')
            input("按回车键继续...")
            return
        
        # 收集文件列表
        backup_files = set()
        current_files = set()
        
        for item in backup_data.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(backup_data)
                backup_files.add(str(rel_path))
        
        for item in current_data.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(current_data)
                current_files.add(str(rel_path))
        
        # 分析差异
        only_in_backup = backup_files - current_files
        only_in_current = current_files - backup_files
        common_files = backup_files & current_files
        
        # 检查共同文件的修改
        modified_files = []
        for rel_path in common_files:
            backup_file = backup_data / rel_path
            current_file = current_data / rel_path
            
            # 简单比较文件大小（可以改用哈希比较）
            if backup_file.stat().st_size != current_file.stat().st_size:
                modified_files.append(rel_path)
        
        # 显示结果
        print()
        print("=" * 60)
        print("差异分析结果")
        print("=" * 60)
        
        if only_in_backup:
            print()
            print(f"📂 仅在备份中存在 ({len(only_in_backup)} 个文件)：")
            for f in sorted(list(only_in_backup)[:10]):
                print(f"   - {f}")
            if len(only_in_backup) > 10:
                print(f"   ... 还有 {len(only_in_backup) - 10} 个文件")
        
        if only_in_current:
            print()
            print(f"📂 仅在当前数据中存在 ({len(only_in_current)} 个文件)：")
            for f in sorted(list(only_in_current)[:10]):
                print(f"   + {f}")
            if len(only_in_current) > 10:
                print(f"   ... 还有 {len(only_in_current) - 10} 个文件")
        
        if modified_files:
            print()
            print(f"🔄 已修改的文件 ({len(modified_files)} 个)：")
            for f in sorted(modified_files[:10]):
                print(f"   ~ {f}")
            if len(modified_files) > 10:
                print(f"   ... 还有 {len(modified_files) - 10} 个文件")
        
        if not only_in_backup and not only_in_current and not modified_files:
            print()
            print("✅ 备份与当前数据完全一致")
        
        print()
        print("=" * 60)
        
        # 返回到最新版本
        manager.repo.git.checkout('HEAD')
        
    except Exception as e:
        print(f"❌ 比较失败: {e}")
        try:
            manager.repo.git.checkout('HEAD')
        except:
            pass
    
    print()
    input("按回车键继续...")


def main():
    """主函数"""
    setup_logger()
    
    try:
        # 加载配置
        config = load_config()
        
        # 验证配置
        if not validate_config(config):
            logger.error("配置验证失败")
            return 1
        
        # 主循环
        while True:
            show_menu()
            choice = input("请选择操作 (0-5): ").strip()
            
            if choice == '1':
                manual_backup(config)
            elif choice == '2':
                list_and_restore(config)
            elif choice == '3':
                edit_commit_message(config)
            elif choice == '4':
                delete_backup(config)
            elif choice == '5':
                compare_diff(config)
            elif choice == '0':
                print()
                print("再见！")
                return 0
            else:
                print()
                print("❌ 无效的选择，请输入 0-5")
                input("按回车键继续...")
    
    except KeyboardInterrupt:
        print("\n\n已取消")
        return 0
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
