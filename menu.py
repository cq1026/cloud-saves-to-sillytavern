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
    print("  1. 执行手动备份")
    print("  2. 列出并拉取备份版本")
    print("  3. 退出")
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
            choice = input("请选择操作 (1-3): ").strip()
            
            if choice == '1':
                manual_backup(config)
            elif choice == '2':
                list_and_restore(config)
            elif choice == '3':
                print()
                print("再见！")
                return 0
            else:
                print()
                print("❌ 无效的选择，请输入 1-3")
                input("按回车键继续...")
    
    except KeyboardInterrupt:
        print("\n\n已取消")
        return 0
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
