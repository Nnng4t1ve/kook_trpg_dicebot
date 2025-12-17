/**
 * COC7 角色卡创建器 - 技能管理
 */

const SkillManager = {
    skillIndex: 0,

    // 加载技能
    async load() {
        try {
            const resp = await fetch('/api/skills');
            const data = await resp.json();
            this.render(data.skills);
            AttributeManager.updateDerived();
        } catch (e) {
            document.getElementById('skillsContainer').innerHTML = '<p style="color:red;">加载失败</p>';
        }
    },

    // 渲染技能
    render(skillsByCategory) {
        const container = document.getElementById('skillsContainer');
        container.innerHTML = '';
        this.skillIndex = 0;

        const dex = getNumValue('dex') || 50;
        const edu = getNumValue('edu') || 50;

        for (const [category, skills] of Object.entries(skillsByCategory)) {
            const catDiv = document.createElement('div');
            catDiv.className = 'skill-category';

            let html = `<h3>${category}</h3><table class="skill-table">
                <tr><th>技能</th><th>基础</th><th>职业</th><th>兴趣</th><th>成功率</th></tr>`;

            for (const skill of skills) {
                html += this.renderRow(skill, dex, edu);
            }
            html += '</table>';
            catDiv.innerHTML = html;
            container.appendChild(catDiv);
        }

        this.bindEvents();
        PointsManager.calculateHobbyPoints();
    },

    // 渲染单行技能
    renderRow(skill, dex, edu) {
        const { name, initial, customName, customBase } = skill;
        const isCM = name === '克苏鲁神话';
        const rowId = `skill_${this.skillIndex++}`;

        // 计算基础值
        let baseValue = initial;
        const isFlash = name === '闪避';
        const isNative = name.startsWith('母语');
        if (isFlash) baseValue = Math.floor(dex / 2);
        else if (isNative) baseValue = edu;

        // 技能名称列
        let nameCell;
        if (customName) {
            nameCell = `<td class="skill-name">${name}<input type="text" class="custom-name" placeholder="填写" style="width:50px;"></td>`;
        } else {
            nameCell = `<td class="skill-name">${name}</td>`;
        }

        // 基础值列
        let baseCell;
        if (customBase) {
            baseCell = `<td><input type="number" class="base custom-base" value="${initial}" min="0" max="99"></td>`;
        } else if (isFlash || isNative) {
            baseCell = `<td class="base">${baseValue}</td>`;
        } else {
            baseCell = `<td class="base">${initial}</td>`;
        }

        return `<tr class="skill-row" data-skill="${name}" data-custom-name="${customName}" data-custom-base="${customBase}" id="${rowId}">
            ${nameCell}
            ${baseCell}
            <td><input type="number" class="job" value="0" min="0" max="99" ${isCM ? 'disabled' : ''}></td>
            <td><input type="number" class="hobby" value="0" min="0" max="99" ${isCM ? 'disabled' : ''}></td>
            <td class="total">${baseValue}</td>
        </tr>`;
    },

    // 更新单行技能总值
    updateRowTotal(row) {
        const baseEl = row.querySelector('.base');
        const base = baseEl.tagName === 'INPUT'
            ? (parseInt(baseEl.value) || 0)
            : (parseInt(baseEl.textContent) || 0);
        const job = parseInt(row.querySelector('.job').value) || 0;
        const hobby = parseInt(row.querySelector('.hobby').value) || 0;
        row.querySelector('.total').textContent = base + job + hobby;
    },

    // 更新所有技能总值
    updateAllTotals() {
        document.querySelectorAll('.skill-row').forEach(row => this.updateRowTotal(row));
    },

    // 绑定事件
    bindEvents() {
        document.querySelectorAll('.skill-table input').forEach(input => {
            input.addEventListener('input', () => {
                this.updateRowTotal(input.closest('.skill-row'));
                PointsManager.calculateUsedPoints();
            });
        });
    },

    // 获取技能数据
    getData() {
        const skills = {};

        document.querySelectorAll('.skill-row').forEach(row => {
            let skillName = row.dataset.skill;
            const total = parseInt(row.querySelector('.total').textContent) || 0;

            const customNameInput = row.querySelector('.custom-name');
            if (customNameInput && customNameInput.value.trim()) {
                skillName = customNameInput.value.trim();
            } else {
                if (skillName.includes('：')) {
                    skillName = skillName.split('：').pop();
                } else if (skillName.includes(':')) {
                    skillName = skillName.split(':').pop();
                }
            }

            const isCustomName = row.dataset.customName === 'true';
            if (total > 0) {
                if (isCustomName && !customNameInput?.value.trim()) {
                    return;
                }
                skills[skillName] = total;
            }
        });

        return skills;
    }
};
