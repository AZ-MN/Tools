# import definesys
# 采用该方式安装第三方库
# import os
# os.system("pip3 install requests")
import requests

def invoke(url, headers):
    # 获取数据来源节点全部数据
    r = requests.get(url, headers)

    # 检查HTTP状态码
    if r.status_code == 500:
        # 打印JSON数据
        print(r.json())pip
        return r.json()
    else:
        print(f"请求失败，状态码: {r.status_code}")
        # 处理失败情况的逻辑
        return None  # 或者根据需要返回其他值

# 定义 URL 和 headers
url = "https://apaas-qa.dfy.definesys.cn/apaas/backend/jycz/test1713/xdap-app/process/menu/query/todoStatistics?timestamp=1701483307246"
headers = {'Xdapappid': '466616701169958912', 'Xdaptenantid': '464005230405615617', 'Xdaptimestamp': '21701483307258',
           "Xdaptoken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJleHAiOjE3MDE1MTI3NjIsImlhdCI6MTcwMTUwNTU2MiwieGRhcHVzZXJpZCI6IjEwMDQ2NDAwMzQ0OTM2MTUzMDg4MCJ9.wzgQgr8qYDNRv-ydLEkYvQ3j025-J4FnhP5z57Zp_uCANhQWvXdhTFscBAd8Guz8PRhUMFqsLK8RzLgNjPgZgQ"}

# 调用函数
invoke(url, headers)