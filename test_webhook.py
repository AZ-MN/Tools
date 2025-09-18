import os
import json

# 测试Webhook配置文件是否能正确创建和写入
CONFIG_FILENAME = "webhooks_config.json"

# 测试配置文件路径
user_dir = os.path.expanduser("~")
config_file = os.path.join(user_dir, f".{CONFIG_FILENAME}")
backup_file = os.path.join(user_dir, CONFIG_FILENAME)

print(f"用户目录: {user_dir}")
print(f"配置文件路径: {config_file}")
print(f"备份文件路径: {backup_file}")

# 检查目录是否存在
config_dir = os.path.dirname(config_file)
print(f"配置目录是否存在: {os.path.exists(config_dir)}")

# 测试写入配置文件
test_webhooks = {"test_webhook": "https://example.com/webhook"}

try:
    # 确保目录存在
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        print(f"已创建配置目录: {config_dir}")
    
    # 尝试写入配置文件
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(test_webhooks, f, ensure_ascii=False, indent=2)
    print(f"成功写入测试配置到: {config_file}")
    
    # 读取并验证
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"读取配置成功，内容: {data}")
    
    # 清理测试文件
    os.remove(config_file)
    print(f"已删除测试配置文件")
    
    print("\n测试成功！Webhook配置文件的路径、目录创建和文件读写功能正常。")
except Exception as e:
    print(f"测试失败: {str(e)}")
    
    # 尝试使用备用位置
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(test_webhooks, f, ensure_ascii=False, indent=2)
        print(f"备用位置测试成功，已写入: {backup_file}")
        os.remove(backup_file)
        print(f"已删除备用位置测试文件")
    except Exception as backup_err:
        print(f"备用位置测试也失败: {str(backup_err)}")