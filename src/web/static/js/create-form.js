/**
 * COC7 角色卡创建器 - 表单和数据管理
 */

const FormManager = {
    // 初始化物品栏
    initInventory() {
        const tbody = document.getElementById('inventoryBody');
        for (let i = 0; i < INVENTORY_ROWS; i++) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><input type="text" class="inv-slot" name="inv_slot_${i}" placeholder=""></td>
                <td><input type="text" class="inv-item" name="inv_item_${i}" placeholder=""></td>
                <td><input type="text" class="inv-backpack" name="inv_backpack_${i}" placeholder=""></td>
            `;
            tbody.appendChild(tr);
        }
    },

    // 初始化背景故事输入
    initBackstoryInputs() {
        const allTextareas = document.querySelectorAll('.backstory-input, .detailed-story-input');
        allTextareas.forEach(textarea => {
            // Alt+Enter 换行
            textarea.addEventListener('keydown', (e) => {
                if (e.altKey && e.key === 'Enter') {
                    e.preventDefault();
                    const start = textarea.selectionStart;
                    const end = textarea.selectionEnd;
                    const value = textarea.value;
                    textarea.value = value.substring(0, start) + '\n' + value.substring(end);
                    textarea.selectionStart = textarea.selectionEnd = start + 1;
                    autoResizeTextarea(textarea);
                }
            });

            textarea.addEventListener('input', () => autoResizeTextarea(textarea));
            autoResizeTextarea(textarea);
        });
    },

    // 获取物品栏数据（只返回物品名称和背包格）
    getInventoryData() {
        const inventory = [];
        for (let i = 0; i < INVENTORY_ROWS; i++) {
            const item = document.querySelector(`input[name="inv_item_${i}"]`)?.value || '';
            const backpack = document.querySelector(`input[name="inv_backpack_${i}"]`)?.value || '';
            if (item || backpack) {
                inventory.push({ item, backpack });
            }
        }
        return inventory;
    },

    // 获取背景故事数据
    getBackstoryData() {
        const data = {};
        BACKSTORY_FIELDS.forEach(field => {
            data[field.name] = document.querySelector(`textarea[name="${field.name}"]`)?.value || '';
            data[`${field.name}_key`] = document.querySelector(`input[name="${field.name}_key"]`)?.checked || false;
        });
        data.detailed_story = document.querySelector('textarea[name="detailed_story"]')?.value || '';
        return data;
    },

    // 获取完整表单数据
    getFormData() {
        const name = document.getElementById('charName').value;
        
        return {
            name,
            attributes: {
                STR: getNumValue('str') || 50,
                CON: getNumValue('con') || 50,
                SIZ: getNumValue('siz') || 50,
                DEX: getNumValue('dex') || 50,
                APP: getNumValue('app') || 50,
                INT: getNumValue('int') || 50,
                POW: getNumValue('pow') || 50,
                EDU: getNumValue('edu') || 50,
                LUK: getNumValue('luk') || 50
            },
            skills: SkillManager.getData(),
            hp: parseInt(document.getElementById('hp').textContent),
            mp: parseInt(document.getElementById('mp').textContent),
            san: parseInt(document.getElementById('san').textContent),
            mov: parseInt(document.getElementById('mov').textContent),
            build: parseInt(document.getElementById('build').textContent),
            db: document.getElementById('db').textContent,
            inventory: this.getInventoryData(),
            backstory: this.getBackstoryData()
        };
    }
};
