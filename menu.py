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
from backup_manager import BackupManager as AdvancedManager
from logger import setup_logger
import logging

logger = logging.getLogger(__name__)


def show_menu():
    """显示主菜单"""
    print()
    print("=" * 70)
    print("       SillyTavern 云备份工具 - 快捷操作菜单")
    print("=" * 70)
    print()
    print("  1. 执行手动备份")
    print("  2. 列出并拉取备份版本")
    print("  3. 修改备份描述")
    print("  4. 删除备份")
    print("  5. 比较差异")
    print("  0. 退出")
    print()


def manual_backup(config):
    """执行手动备份"""
    print()
    print("-" * 70)
    print("开始手动备份...")
    print("-" * 70)
    
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
    print("-" * 70)
    print("备份版本列表")
    print("-" * 70)
    
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
            print("=" * 70)
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
            print("=" * 70)
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


def modify_description(config):
    """修改备份描述（支持任意提交）"""
    print()
    print("-" * 70)
    print("修改备份描述")
    print("-" * 70)
    
    # 初始化恢复管理器来列出备份
    restore_manager = RestoreManager(config)
    
    if not restore_manager.init_repo():
        print("❌ 无法打开备份仓库")
        input("按回车键继续...")
        return
    
    # 列出备份
    backups = restore_manager.list_backups(max_count=20)
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
    print("-" * 80)
    
    # 选择要修改的版本
    while True:
        choice = input("请选择要修改的版本（输入序号，或 'q' 取消）: ").strip()
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
    print(f"选中的提交: {selected_hash}")
    print(f"时间: {selected_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"当前描述:")
    print("-" * 70)
    print(selected_msg)
    print("-" * 70)
    print()
    
    # 输入新描述
    if index == 0:
        print("💡 提示：这是最新提交，修改较快")
    else:
        print("⚠️  警告：这是历史提交，修改会重写所有后续提交的 hash")
    
    print("\n请输入新的描述（多行，输入单独一行 'END' 结束）：")
    
    lines = []
    while True:
        line = input()
        if line == 'END':
            break
        lines.append(line)
    
    new_message = '\n'.join(lines)
    if not new_message.strip():
        print("❌ 描述不能为空")
        input("按回车键继续...")
        return
    
    # 确认
    print()
    print("新描述：")
    print("-" * 70)
    print(new_message)
    print("-" * 70)
    
    if index != 0:
        print()
        print("⚠️  再次警告：修改历史提交会：")
        print("   1. 改变所有后续提交的 hash")
        print("   2. 需要强制推送到远程")
        print("   3. 不建议在多人协作时使用")
    
    confirm = input("\n确认修改？(yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        # 使用高级管理器
        adv_manager = AdvancedManager(
            repo_path=config['backup_repo_path'],
            data_path=Path('/data') if Path('/.dockerenv').exists() else config['sillytavern_data_path']
        )
        adv_manager.repo = restore_manager.repo
        
        if adv_manager.modify_commit_message(selected_hash, new_message):
            print()
            print("✅ 描述修改成功！")
            print()
            print("⚠️  需要强制推送到远程")
            push_confirm = input("是否立即推送？(yes/no): ").strip().lower()
            
            if push_confirm in ['yes', 'y']:
                if adv_manager.force_push():
                    print("✅ 已推送到远程")
                else:
                    print("❌ 推送失败，请手动执行: git push --force")
        else:
            print("❌ 修改失败")
    else:
        print("已取消")
    
    print()
    input("按回车键继续...")


def delete_backup(config):
    """删除备份（仅限最新提交）"""
    print()
    print("-" * 70)
    print("删除备份")
    print("-" * 70)
    
    adv_manager = AdvancedManager(
        repo_path=config['backup_repo_path'],
        data_path=Path('/data') if Path('/.dockerenv').exists() else config['sillytavern_data_path']
    )
    
    if not adv_manager.init_repo():
        print("❌ 无法打开备份仓库")
        input("按回车键继续...")
        return
    
    try:
        latest_commit = adv_manager.repo.head.commit
        print()
        print(f"将要删除的提交: {latest_commit.hexsha[:7]}")
        print(f"时间: {latest_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"描述:")
        print("-" * 70)
        print(latest_commit.message)
        print("-" * 70)
        print()
        print("⚠️  警告：此操作不可撤销！")
        print("⚠️  注意：只能删除最新提交")
        print()
        
        confirm = input("确认删除？请输入 'DELETE' 确认: ").strip()
        
        if confirm == 'DELETE':
            if adv_manager.delete_commit(latest_commit.hexsha[:7]):
                print()
                print("✅ 本地备份已删除！")
                print()
                print("⚠️  需要强制推送到远程")
                push_confirm = input("是否立即推送到远程？(yes/no): ").strip().lower()
                
                if push_confirm in ['yes', 'y']:
                    if adv_manager.force_push():
                        print("✅ 远程备份已删除")
                    else:
                        print("❌ 推送失败，请手动执行: git push --force")
            else:
                print("❌ 删除失败")
        else:
            print("已取消")
    
    except Exception as e:
        print(f"❌ 操作失败: {e}")
    
    print()
    input("按回车键继续...")


def compare_diff(config):
    """比较云备份与本地数据的差异"""
    print()
    print("-" * 70)
    print("比较差异")
    print("-" * 70)
    
    adv_manager = AdvancedManager(
        repo_path=config['backup_repo_path'],
        data_path=Path('/data') if Path('/.dockerenv').exists() else config['sillytavern_data_path']
    )
    
    if not adv_manager.init_repo():
        print("❌ 无法打开备份仓库")
        input("按回车键继续...")
        return
    
    print()
    print("正在比较最新备份与当前本地数据...")
    print()
    
    diff = adv_manager.compare_with_local()
    
    if diff is None:
        print("❌ 比较失败")
    else:
        added = diff['added']
        modified = diff['modified']
        deleted = diff['deleted']
        
        if not added and not modified and not deleted:
            print("✅ 没有差异，数据一致")
        else:
            print("=" * 70)
            
            if added:
                print(f"\n📄 本地新增文件 ({len(added)} 个):")
                for f in added[:10]:  # 最多显示 10 个
                    print(f"  + {f}")
                if len(added) > 10:
                    print(f"  ... 还有 {len(added) - 10} 个")
            
            if modified:
                print(f"\n✏️  已修改文件 ({len(modified)} 个):")
                for f in modified[:10]:
                    print(f"  ~ {f}")
                if len(modified) > 10:
                    print(f"  ... 还有 {len(modified) - 10} 个")
            
            if deleted:
                print(f"\n🗑️  本地已删除文件 ({len(deleted)} 个):")
                for f in deleted[:10]:
                    print(f"  - {f}")
                if len(deleted) > 10:
                    print(f"  ... 还有 {len(deleted) - 10} 个")
            
            print()
            print("=" * 70)
            print(f"\n💡 提示：如果有差异，可以执行手动备份同步这些变更")
    
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
                modify_description(config)
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
