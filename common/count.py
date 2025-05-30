issues = """
            ISSUE-2024120657534 
            ISSUE-2024120457380 
            ISSUE-2024120257241 
            ISSUE-2024110555932 
            ISSUE-2024120957583 
            ISSUE-2024120657504 
            ISSUE-2024120557438 
            ISSUE-2024112256760 
            ISSUE-2024120557474 
            ISSUE-2024120557467 
            ISSUE-2024120557411 
            ISSUE-2024120557481 
            ISSUE-2024120457374 
            ISSUE-2024120457340 
            ISSUE-2024112857080 
            ISSUE-2024112056666 
            ISSUE-2024120857574 
            ISSUE-2024120757552 
            ISSUE-2024120757547 
            ISSUE-2024120557413 
            ISSUE-2024120457401 
            ISSUE-2024120457388 
            ISSUE-2024120357311 
            ISSUE-2024120357301 
            ISSUE-2024120357297 
            ISSUE-2024112756971 
            ISSUE-2024120957596 
            ISSUE-2024120657517 
            ISSUE-2024120557427 
            ISSUE-2024112857037 
            ISSUE-2024112756995 
            ISSUE-2024112656931 
            ISSUE-2024112556856 
            ISSUE-2024120957611 
            ISSUE-2024120957597 
            ISSUE-2024120557463 
            ISSUE-2024120557452 
            ISSUE-2024120557445 
            ISSUE-2024120557410 
            ISSUE-2024120457399 
            ISSUE-2024120457393 
            ISSUE-2024120357289 
            ISSUE-2024120657520 
            ISSUE-2024120657491 
            ISSUE-2024120257197 
            ISSUE-2024120857568 
            ISSUE-2024120657492 
            ISSUE-2024112857059 
            ISSUE-2024120857562 
            ISSUE-2024120657526 
            ISSUE-2024111556460 
            ISSUE-2024121057677 
            ISSUE-2024121057672 
            ISSUE-2024121057682 
            ISSUE-2024121057683 
            ISSUE-2024121157733 
            ISSUE-2024121157750 
            ISSUE-2024121157760
"""

issue_list = issues.splitlines()  # 将文本按行分割成列表
unique_issues = set(issue_list)  # 利用集合去重
count = len(unique_issues)  # 统计去重后的数量

print("去重后的不同ISSUE编号数量为:", count)