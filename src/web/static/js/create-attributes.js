/**
 * COC7 角色卡创建器 - 属性管理
 */

const AttributeManager = {
    previewSets: [], // 存储5组随机属性
    currentView: 'card', // 当前视图模式
    selectedIdx: -1, // 当前选中的方案索引

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

    // 生成一组随机属性
    generateOneSet() {
        const set = {};
        let total = 0;
        ATTR_IDS.forEach(id => {
            set[id] = rollAttribute(id);
            if (id !== 'luk') total += set[id];
        });
        set.totalNoLuk = total;
        set.totalWithLuk = total + set.luk;
        return set;
    },

    // 生成5组随机属性并显示预览
    randomMulti() {
        this.previewSets = [];
        this.selectedIdx = -1;
        for (let i = 0; i < 5; i++) {
            this.previewSets.push(this.generateOneSet());
        }
        // 按总值排序（不含幸运）
        this.previewSets.sort((a, b) => b.totalNoLuk - a.totalNoLuk);
        this.renderPreview();
        document.getElementById('randomPreviewPanel').style.display = 'block';
    },

    // 渲染预览
    renderPreview() {
        const container = document.getElementById('previewContent');
        if (this.currentView === 'card') {
            container.className = 'preview-content preview-card-view';
            container.innerHTML = this.previewSets.map((set, idx) => this.renderCardItem(set, idx)).join('');
        } else {
            container.className = 'preview-content preview-table-view';
            container.innerHTML = this.renderTableView();
        }
    },

    // 渲染卡片项
    renderCardItem(set, idx) {
        const attrNames = { str: '力量', con: '体质', siz: '体型', dex: '敏捷', app: '外貌', int: '智力', pow: '意志', edu: '教育', luk: '幸运' };
        let attrsHtml = ATTR_IDS.map(id =>
            `<div class="preview-card-attr"><span class="attr-name">${attrNames[id].slice(0, 1)}</span><span class="attr-val">${set[id]}</span></div>`
        ).join('');

        const selectedClass = this.selectedIdx === idx ? ' selected' : '';
        return `<div class="preview-card${selectedClass}" onclick="AttributeManager.applySet(${idx})">
            <div class="preview-card-header">方案 ${idx + 1}${this.selectedIdx === idx ? ' ✓' : ''}</div>
            <div class="preview-card-total"><span>${set.totalNoLuk}</span> <span class="with-luk">${set.totalWithLuk}</span></div>
            <div class="preview-card-attrs">${attrsHtml}</div>
        </div>`;
    },

    // 渲染表格视图
    renderTableView() {
        const attrNames = { str: '力量', con: '体质', siz: '体型', dex: '敏捷', app: '外貌', int: '智力', pow: '意志', edu: '教育', luk: '幸运' };
        let headerHtml = '<th>方案</th>' + ATTR_IDS.map(id => `<th>${attrNames[id]}</th>`).join('') + '<th>总计</th><th>操作</th>';

        let rowsHtml = this.previewSets.map((set, idx) => {
            let cells = ATTR_IDS.map(id => `<td>${set[id]}</td>`).join('');
            const selectedClass = this.selectedIdx === idx ? ' selected' : '';
            const btnText = this.selectedIdx === idx ? '已选 ✓' : '选择';
            return `<tr class="preview-row${selectedClass}" onclick="AttributeManager.applySet(${idx})">
                <td>${idx + 1}</td>${cells}
                <td class="total-cell">${set.totalNoLuk} <span class="with-luk">${set.totalWithLuk}</span></td>
                <td><button type="button" class="select-btn">${btnText}</button></td>
            </tr>`;
        }).join('');

        return `<table class="preview-table"><thead><tr>${headerHtml}</tr></thead><tbody>${rowsHtml}</tbody></table>`;
    },

    // 应用选中的属性组
    applySet(idx) {
        const set = this.previewSets[idx];
        this.selectedIdx = idx;
        ATTR_IDS.forEach(id => {
            setNumValue(id, set[id]);
        });
        this.updateTotal();
        this.updateDerived();
        PointsManager.calculateJobPoints();
        PointsManager.calculateHobbyPoints();
        // 重新渲染以更新选中状态
        this.renderPreview();
        showToast('已应用方案 ' + (idx + 1), 'success');
    },

    // 切换视图
    switchView(view) {
        this.currentView = view;
        document.querySelectorAll('.preview-view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        this.renderPreview();
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

        // 批量随机按钮
        document.getElementById('randomMultiBtn')?.addEventListener('click', () => {
            this.randomMulti();
        });

        // 关闭预览面板
        document.getElementById('closePreviewBtn')?.addEventListener('click', () => {
            document.getElementById('randomPreviewPanel').style.display = 'none';
        });

        // 视图切换按钮
        document.querySelectorAll('.preview-view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchView(btn.dataset.view);
            });
        });
    }
};
