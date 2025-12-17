/**
 * COC7 角色卡创建器 - 工具函数
 */

// 骰子函数
function rollD6() {
    return Math.floor(Math.random() * 6) + 1;
}

function roll3D6x5() {
    return (rollD6() + rollD6() + rollD6()) * 5;
}

function roll2D6plus6x5() {
    return (rollD6() + rollD6() + 6) * 5;
}

// 根据属性配置获取随机值
function rollAttribute(attrId) {
    const config = ATTRIBUTES[attrId];
    return config.roll === '2d6+6' ? roll2D6plus6x5() : roll3D6x5();
}

// 计算体格和伤害加值
function calcBuildDB(strSiz) {
    for (const entry of BUILD_DB_TABLE) {
        if (strSiz <= entry.max) {
            return { build: entry.build, db: entry.db };
        }
    }
    return { build: 5, db: '+4d6' };
}

// 获取元素值（数字）
function getNumValue(id) {
    const el = document.getElementById(id);
    return parseInt(el?.value) || 0;
}

// 设置元素值
function setNumValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

// 设置元素文本
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

// Toast 提示
function showToast(message, type = 'warning') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

// 自动调整 textarea 高度
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}
