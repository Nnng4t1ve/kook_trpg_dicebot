/**
 * COC7 角色卡创建器 - 属性管理
 */

const AttributeManager = {
    // 随机全部属性
    randomAll() {
        ATTR_IDS.forEach(id => {
            setNumValue(id, rollAttribute(id));
        });
        this.updateTotal();
        this.updateDerived();
        PointsManager.calculateJobPoints();
        PointsManager.calculateHobbyPoints();
    },

    // 更新属性总值
    updateTotal() {
        let totalNoLuk = 0;
        ATTR_IDS.forEach(id => {
            if (id !== 'luk') {
                totalNoLuk += getNumValue(id);
            }
        });
        const totalWithLuk = totalNoLuk + getNumValue('luk');

        setText('totalNoLuk', totalNoLuk);
        setText('totalWithLuk', totalWithLuk);
    },

    // 更新派生属性
    updateDerived() {
        const str = getNumValue('str') || 50;
        const con = getNumValue('con') || 50;
        const siz = getNumValue('siz') || 50;
        const dex = getNumValue('dex') || 50;
        const pow = getNumValue('pow') || 50;

        // HP, MP, SAN
        setText('hp', Math.floor((con + siz) / 10));
        setText('mp', Math.floor(pow / 5));
        setText('san', pow);

        // MOV
        let mov = 8;
        if (str > siz && dex > siz) mov = 9;
        else if (str < siz && dex < siz) mov = 7;
        setText('mov', mov);

        // 体格和伤害加值
        const { build, db } = calcBuildDB(str + siz);
        setText('build', build);
        setText('db', db);

        // 更新闪避和母语的基础值
        const edu = getNumValue('edu') || 50;
        document.querySelectorAll('[data-skill="闪避"] .base').forEach(el => {
            if (el.tagName !== 'INPUT') el.textContent = Math.floor(dex / 2);
        });
        document.querySelectorAll('[data-skill="母语:"] .base').forEach(el => {
            if (el.tagName !== 'INPUT') el.textContent = edu;
        });

        SkillManager.updateAllTotals();
    },

    // 绑定属性输入事件
    bindEvents() {
        ATTR_IDS.forEach(id => {
            document.getElementById(id)?.addEventListener('input', () => {
                this.updateTotal();
                this.updateDerived();
                PointsManager.calculateJobPoints();
                if (id === 'int') PointsManager.calculateHobbyPoints();
            });
        });

        document.getElementById('randomAllBtn')?.addEventListener('click', () => {
            this.randomAll();
        });
    }
};
