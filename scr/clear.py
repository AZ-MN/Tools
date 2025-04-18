# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


# def print_hi(name):
#     # Use a breakpoint in the code line below to debug your script.
#     print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.
#
#
# # Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

test = ("[{\"batchApproveFlag\":false,\"buttonCode\":\"REJECT\",\"buttonName\":\"拒绝\",\"comment\":\"\","
        "\"commonFlag\":false,\"completedFlag\":false,\"data\":{},\"documentId\":\"644175608233197696\","
        "\"draftStatusUpdateFlag\":false,\"formId\":\"66da72c42667a101ff1b02c1\",\"isDifferentParallelFlow\":false,"
        "\"modelFlag\":false,\"permissionFlag\":false,\"saveFlag\":true,\"skipFlag\":false,\"submitFlag\":false,"
        "\"tableData\":{},\"taskId\":\"1238747\"},{\"batchApproveFlag\":false,\"buttonCode\":\"REJECT\","
        "\"buttonName\":\"拒绝\",\"comment\":\"\",\"commonFlag\":false,\"completedFlag\":false,\"data\":{},"
        "\"documentId\":\"644175616147849344\",\"draftStatusUpdateFlag\":false,"
        "\"formId\":\"66da72c42667a101ff1b02c1\",\"isDifferentParallelFlow\":false,\"modelFlag\":false,"
        "\"permissionFlag\":false,\"saveFlag\":true,\"skipFlag\":false,\"submitFlag\":false,\"tableData\":{},"
        "\"taskId\":\"1238771\"},{\"batchApproveFlag\":false,\"buttonCode\":\"REJECT\",\"buttonName\":\"拒绝\","
        "\"comment\":\"\",\"commonFlag\":false,\"completedFlag\":false,\"data\":{},"
        "\"documentId\":\"644175623651459200\",\"draftStatusUpdateFlag\":false,"
        "\"formId\":\"66da72c42667a101ff1b02c1\",\"isDifferentParallelFlow\":false,\"modelFlag\":false,"
        "\"permissionFlag\":false,\"saveFlag\":true,\"skipFlag\":false,\"submitFlag\":false,\"tableData\":{},"
        "\"taskId\":\"1238795\"}]")


# 去除特殊字符
def clear(s):
    s1 = s.replace('\\', '')
    s2 = s1.replace('[', '')
    s3 = s2.replace(']', '')
    s4 = s3.replace(',', '\n')
    return s4


if __name__ == '__main__':
    print(clear(test))


