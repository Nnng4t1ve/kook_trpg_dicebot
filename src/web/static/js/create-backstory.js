/**
 * COC7 角色卡创建器 - 背景故事随机模块
 */

const BackstoryRandomizer = {
    // 随机数据
    data: {
        appearance: [
            '结实的', '英俊的', '茶褐的', '机灵的', '迷人的', '娃娃脸', '聪明的', '邋遢的', 
            '死人脸', '肌腱的', '耀眼的', '书呆脸', '年轻的', '疲惫脸', '肥胖的', '喧闹的', 
            '长头发', '苗条的', '优雅的', '标准的', '矮壮的', '苦闷的', '阴沉的', '平庸的', 
            '乐观的', '棕褐色', '斑纹的', '古板的', '狐臭的', '狡猾的', '健壮的', '妖娆的', 
            '筋肉的', '魅惑的', '迟钝的', '虚弱的'
        ],
        ideology: [
            '你信仰并崇拜一位大能。（例如毗沙门天、耶稣、基督、海尔赛西一世）',
            '人类无高于一切。（例如坚定的无神论者、人文主义者、世俗主义者）',
            '科学万能！科学万岁！你将选择其中之一。（例如进化论、低温学、太空探索）',
            '命中注定。（例如因果报应、种姓系统、超自然存在）',
            '社团或秘密结社的一员。（例如共济会、女协匿名者）',
            '社会坏掉了，而你将成为正义的伙伴。应斩除之物是？（例如毒品、暴力、种族歧视）',
            '神秘依然在。（例如占星术、招魂术、塔罗）',
            '渴望，我喜欢政治。（例如保守党、共产党、自由党）',
            '金钱就是力量。我的朋友，我将竭尽全力获取能看到的一切。（例如盗窃、进取、冷酷心）',
            '完美者/激进主义者。（例如女权运动、平等主义家、工会权利）'
        ],
        significant_people: [
            '父辈。',
            '祖父辈。',
            '兄弟。',
            '孩子。',
            '另一半。',
            '那位指引你人生技能的人。指明该技能和该人。',
            '青梅竹马。',
            '名人。偶像或者英雄。当然也许你从未见过他。',
            '游戏中的另一位调查员伙伴。随机或自选。',
            '游戏中另一位 NPC，详情咨询你的守秘人。'
        ],
        significant_people_reason: [
            '你欠了他们人情。他们帮助了你什么？',
            '他们教会了你一些东西。',
            '他们给了你生命的意义。',
            '你害了他们，而现在寻求救赎。',
            '同甘共苦。',
            '你想向他们证明自己。',
            '你崇拜他们。',
            '后悔的感觉。',
            '你试图证明你比他们更出色。他们的缺点是什么？',
            '他们扰乱了你的人生，而你寻求复仇。发生了什么？'
        ],
        meaningful_locations: [
            '你最爱的学府。',
            '你的故乡。',
            '相识和恋之处。',
            '常驻之地。',
            '社交之地。',
            '联系你思想/信念的场所。',
            '重要之人的坟墓。',
            '家族所在。',
            '生命中最为开心的所在。',
            '工作地点。'
        ],
        treasured_possessions: [
            '与你最密切相关之物',
            '职业必需品',
            '童年的遗留物',
            '逝者遗物',
            '重要之人给予之物',
            '收藏品',
            '你发现而不知其价值的东西',
            '体育用品',
            '武器',
            '宠物'
        ],
        traits: [
            '慷慨大方。',
            '善待动物。',
            '梦想家。',
            '享乐主义者。',
            '赌徒，冒险家。',
            '好厨子，好吃货。',
            '女人缘/万人迷。',
            '忠心在我。',
            '好名头。',
            '雄心壮志。'
        ]
    },

    // 初始化
    init() {
        this.bindEvents();
    },

    // 绑定事件
    bindEvents() {
        // 单项随机按钮
        document.querySelectorAll('.btn-backstory-random').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const field = e.target.dataset.field;
                this.randomizeField(field);
            });
        });

        // 全部随机按钮
        document.getElementById('randomAllBackstoryBtn')?.addEventListener('click', () => {
            this.randomizeAll();
        });
    },

    // 随机选择一项
    pickRandom(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    },

    // 随机选择多项（不重复）
    pickRandomMultiple(arr, count) {
        const shuffled = [...arr].sort(() => Math.random() - 0.5);
        return shuffled.slice(0, Math.min(count, arr.length));
    },

    // 随机单个字段
    randomizeField(field) {
        const textarea = document.querySelector(`textarea[name="${field}"]`);
        if (!textarea) return;

        let result = '';
        
        if (field === 'appearance') {
            // 形象描述随机3个
            const items = this.pickRandomMultiple(this.data.appearance, 3);
            result = items.join('、');
        } else if (field === 'significant_people') {
            // 重要之人需要同时随机人物和原因
            const person = this.pickRandom(this.data.significant_people);
            const reason = this.pickRandom(this.data.significant_people_reason);
            result = `${person}\n原因：${reason}`;
        } else if (this.data[field]) {
            result = this.pickRandom(this.data[field]);
        }

        if (result) {
            textarea.value = result;
            // 触发自动调整高度
            if (typeof autoResizeTextarea === 'function') {
                autoResizeTextarea(textarea);
            }
            // 触发input事件以便缓存
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
    },

    // 随机全部
    randomizeAll() {
        const fields = ['appearance', 'ideology', 'significant_people', 'meaningful_locations', 'treasured_possessions', 'traits'];
        fields.forEach(field => this.randomizeField(field));
        
        if (typeof showToast === 'function') {
            showToast('已随机生成背景故事', 'success');
        }
    }
};

// 页面加载后初始化
document.addEventListener('DOMContentLoaded', () => {
    BackstoryRandomizer.init();
});
