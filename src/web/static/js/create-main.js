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

        // 初始化职业管理器
        OccupationManager.init();

        // 初始化属性总值
        AttributeManager.updateTotal();
        
        // 显示技能上限提示
        this.showSkillLimitHint();
        
        // 初始化缓存管理器
        if (typeof CacheManager !== 'undefined') {
            CacheManager.init(token);
        }
    },
    
    // 显示技能上限提示
    showSkillLimitHint() {
        const hintEl = document.getElementById('skillLimitHint');
        if (!hintEl) return;
        
        if (typeof SKILL_LIMIT !== 'undefined' && SKILL_LIMIT !== null) {
            hintEl.innerHTML = `⚠️ 技能上限: <strong>${SKILL_LIMIT}</strong>（所有技能成功率不能超过此值）`;
            hintEl.style.display = 'block';
        } else if (typeof OCC_LIMIT !== 'undefined' && OCC_LIMIT !== null && 
                   typeof NON_OCC_LIMIT !== 'undefined' && NON_OCC_LIMIT !== null) {
            hintEl.innerHTML = `⚠️ 技能上限: 本职 <strong>${OCC_LIMIT}</strong> / 非本职 <strong>${NON_OCC_LIMIT}</strong>（双击技能行标记为本职技能）`;
            hintEl.style.display = 'block';
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // token 和 userId 由模板注入
    if (typeof APP_TOKEN !== 'undefined' && typeof APP_USER_ID !== 'undefined') {
        CharacterCreator.init(APP_TOKEN, APP_USER_ID);
    }
});
