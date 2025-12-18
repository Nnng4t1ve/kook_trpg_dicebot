/**
 * COC7 角色卡创建器 - 职业管理
 */

const OccupationManager = {
    occupations: [],
    occupationSkills: new Set(),

    // 初始化
    async init() {
        console.log('OccupationManager 初始化中...');
        await this.loadOccupations();
        this.bindEvents();
        console.log('OccupationManager 初始化完成，职业数量:', this.occupations.length);
    },

    // 加载职业数据
    async loadOccupations() {
        try {
            const resp = await fetch('/static/data/occupations.json');
            this.occupations = await resp.json();
        } catch (e) {
            console.error('加载职业数据失败:', e);
        }
    },

    // 绑定事件
    bindEvents() {
        const queryBtn = document.getElementById('queryOccupationBtn');
        const occupationInput = document.getElementById('occupationId');

        // 查询按钮点击
        if (queryBtn) {
            queryBtn.onclick = () => {
                console.log('查询按钮被点击');
                this.queryOccupation();
            };
        }

        // 回车查询
        if (occupationInput) {
            occupationInput.onkeydown = (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('回车键触发查询');
                    this.queryOccupation();
                    return false;
                }
            };
        }

        // 绑定技能行双击事件 - 使用document级别的事件委托
        document.addEventListener('dblclick', (e) => {
            // 忽略输入框的双击
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            const row = e.target.closest('tr.skill-row');
            if (row) {
                console.log('双击技能行:', row.dataset.skill);
                e.preventDefault();
                this.toggleOccupationSkill(row);
            }
        });
    },

    // 查询职业
    queryOccupation() {
        const input = document.getElementById('occupationId');
        const output = document.getElementById('occupationOutput');
        
        if (!input || !output) {
            console.error('找不到输入或输出元素');
            return;
        }

        const id = parseInt(input.value);
        console.log('查询职业ID:', id);

        if (isNaN(id) || id < 0) {
            output.innerHTML = '<p class="hint" style="color: #f44336;">请输入有效的职业序号</p>';
            return;
        }

        const occupation = this.occupations.find(o => o.id === id);
        console.log('找到职业:', occupation);

        if (!occupation) {
            output.innerHTML = '<p class="hint" style="color: #f44336;">未找到该职业</p>';
            return;
        }

        // 特殊处理序号0
        if (id === 0) {
            output.innerHTML = `<div class="occ-name">${occupation.name}</div>`;
            this.clearOccupationSkills();
            return;
        }

        output.innerHTML = `
            <div class="occ-name">${occupation.name}</div>
            <div class="occ-info">
                <span class="occ-label">信用评级:</span>
                <span class="occ-value">${occupation.credit}</span>
                <span class="occ-label">职业属性:</span>
                <span class="occ-value">${occupation.attributes}</span>
            </div>
            <div class="occ-skills">
                <strong>本职技能:</strong> ${occupation.skills}
            </div>
        `;

        this.parseOccupationSkills(occupation.skills);
    },

    // 解析职业技能字符串
    parseOccupationSkills(skillsStr) {
        this.occupationSkills.clear();
        
        const knownSkills = [
            '会计', '人类学', '估价', '考古', '技艺', '取悦', '攀爬', '计算机', '信用评级',
            '克苏鲁神话', '乔装', '闪避', '汽车驾驶', '电气维修', '电子学', '话术', '格斗',
            '射击', '急救', '历史', '恐吓', '跳跃', '语言', '母语', '外语', '法律', '图书馆',
            '聆听', '锁匠', '机械维修', '医学', '自然', '导航', '神秘学', '操作重型机械',
            '说服', '驾驶', '精神分析', '心理学', '骑乘', '科学', '妙手', '侦查', '潜行',
            '生存', '游泳', '投掷', '追踪', '驯兽', '潜水', '爆破', '催眠', '读唇'
        ];

        const parts = skillsStr.split(/[，,、]/);
        
        for (const part of parts) {
            const trimmed = part.trim();
            for (const skill of knownSkills) {
                if (trimmed.includes(skill)) {
                    this.occupationSkills.add(skill);
                }
            }
        }
    },

    // 清除本职技能标记
    clearOccupationSkills() {
        this.occupationSkills.clear();
        document.querySelectorAll('.skill-row').forEach(row => {
            row.classList.remove('occupation-skill');
            const nameCell = row.querySelector('.skill-name');
            if (nameCell) {
                const marker = nameCell.querySelector('.occ-marker');
                if (marker) marker.remove();
            }
        });
    },

    // 切换本职技能状态
    toggleOccupationSkill(row) {
        const skillName = row.dataset.skill;
        const nameCell = row.querySelector('.skill-name');

        if (!nameCell) return;

        if (row.classList.contains('occupation-skill')) {
            row.classList.remove('occupation-skill');
            const marker = nameCell.querySelector('.occ-marker');
            if (marker) marker.remove();
            this.occupationSkills.delete(skillName);
            console.log('移除本职技能:', skillName);
        } else {
            row.classList.add('occupation-skill');
            if (!nameCell.querySelector('.occ-marker')) {
                const marker = document.createElement('span');
                marker.className = 'occ-marker';
                marker.textContent = '★';
                nameCell.insertBefore(marker, nameCell.firstChild);
            }
            this.occupationSkills.add(skillName);
            console.log('添加本职技能:', skillName);
        }
    }
};
