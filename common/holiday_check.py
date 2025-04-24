# import requests
# from datetime import datetime
#
#
# def is_holiday():
#     # 1. 获取当前日期
#     today = datetime.now().strftime("%Y%m%d")
#
#     # 2. 调用节假日API（这里使用腾讯日历API示例）
#     api_url = f"https://api.apihubs.cn/holiday/get?date={today}"
#
#     try:
#         response = requests.get(api_url)
#         data = response.json()
#
#         # 3. 判断是否为节假日（0工作日 1周末 2法定节假日）
#         if data["data"]["list"][0]["type"] in [1, 2]:
#             return True
#     except Exception as e:
#         print(f"API调用失败: {str(e)}")
#         return False  # API故障时默认执行
#
#     return False
#
#
# if __name__ == "__main__":
#     print("true" if is_holiday() else "false")

# from datetime import datetime
# from workalendar.europe import Germany
#
#
# def is_holiday():
#     # 1. 获取当前日期
#     today = datetime.now().strftime("%Y%m%d")
#     cal = Germany()
#     flag = cal.is_holiday(today)
#     # 输出是否为节假日
#     return flag
#
#
# if __name__ == "__main__":
#     print(is_holiday())


# import requests
# from datetime import datetime
# from workalendar.asia import China  # 根据实际使用的日历调整
#
#
# def is_holiday(check_date=None):
#     # 获取当前日期（如果未指定日期）
#     if not check_date:
#         check_date = datetime.now().date()
#     elif isinstance(check_date, str):
#         # 转换字符串为日期对象
#         check_date = datetime.strptime(check_date, '%Y%m%d').date()
#
#     # 初始化中国日历（支持节假日）
#     cal = China()
#
#     # 判断是否为节假日（包含周末和法定假日）
#     return not cal.is_working_day(check_date)
#
#
# if __name__ == "__main__":
#     import sys
#
#     # 支持命令行传参或自动检测
#     date_to_check = sys.argv[1] if len(sys.argv) > 1 else None
#
#     # 执行检查并输出结果
#     print("true" if is_holiday(date_to_check) else "false")

import datetime
from chinese_calendar import is_holiday, is_in_lieu, is_workday

today = datetime.datetime.now().date()


def check_workday(date):
    # 对于当天进行判断
    # print(today)
    if is_workday(date) or is_in_lieu(date) and not is_holiday(date):
        # print("今天工作日")
        return True
    else:
        # print("今天节假日")
        return False


check_workday(today)
# print(check_workday(today))
# print(check_workday(datetime.date(2025, 6, 4)))
