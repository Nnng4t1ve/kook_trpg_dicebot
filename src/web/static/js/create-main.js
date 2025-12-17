/**
 * COC7 角色卡创建器 - 主入口
 */

const CharacterCreator = {
    // 初始化应用
    init(token, userId) {
        // 初始化审核管理器
        ReviewManager.init(token, userId);

        // 绑定事件
        AttributeManager.bindEvents();
        PointsManager.setupCheckboxLimit();
        ReviewManager.bindEvents();

        // 初始化表单
        FormManager.initInventory();
        FormManager.initBackstoryInputs();

        // 加载技能
        SkillManager.load();

        // 初始化属性总值
        AttributeManager.updateTotal();
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // token 和 userId 由模板注入
    if (typeof APP_TOKEN !== 'undefined' && typeof APP_USER_ID !== 'undefined') {
        CharacterCreator.init(APP_TOKEN, APP_USER_ID);
    }
});
