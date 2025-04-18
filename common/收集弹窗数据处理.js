// 处理数据来源节点数据
let customNodeData = [
    {
        "afterFormData": {
            "bof_code_5fd34c08adaed6ba989927a7": 123,
            "bof_code_05c942a8956285c473bffc7a": "单行",
            "bof_code_modal_result": "确定",
            "bof_code_aa1540d98e7422f40dd6c558": "多行"
        },
        "afterTableData": {}
    }
]
// customNodeData  字段是获取得来自数据来源节点中得全部数据
// 在这里进行数据的处理，处理完成后把处理的结果  return  出去
// 处理后得数据只能是Array[],  或者是Object{}

debugger;
// 处理数据
const result = {};

// 遍历 customNodeData 数组
for (let i = 0; i < customNodeData.length; i++) {
    const afterFormData = customNodeData[i].afterFormData;
    // 遍历 afterFormData 对象的每个属性
    for (const key in afterFormData) {
        if (afterFormData.hasOwnProperty(key)) {
            result[key] = afterFormData[key];
        }
    }
}

console.log(result);


// 使用JS设置收集弹窗组件值
var setComponentValues = function() {
    // 封装通用的输入设置函数
    function setInputValue(selector, value) {
        var inputElement = document.querySelector(selector);
        if (inputElement) {
            inputElement.value = value;
            // 使用 InputEvent 模拟更精确的输入事件
            var inputEvent = new InputEvent('input', { bubbles: true, cancelable: true });
            inputElement.dispatchEvent(inputEvent);
            console.info(`已设置输入值: ${value}`);
        } else {
            console.warn(`未找到匹配的选择器: ${selector}`);
        }
    }

    // 定位单行输入组件并输入"单行"
    setInputValue('[data-component-id="05c942a8956285c473bffc7a"] [class="el-input__inner"]', '单行');

    // 定位数字输入组件并输入"123"
    setInputValue('[data-component-id="5fd34c08adaed6ba989927a7"] [class="el-input__inner"]', '123');

    // 定位多行输入组件并输入"多行"
    setInputValue('[data-component-id="aa1540d98e7422f40dd6c558"] [class="el-textarea__inner"]', '多行');
};

// 在控制台中直接调用这个函数即可执行所有组件的赋值操作
setComponentValues();
