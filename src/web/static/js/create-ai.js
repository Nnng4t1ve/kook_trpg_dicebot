/**
 * COC7 角色卡创建器 - AI生成模块
 */

const AIManager = {
    enabled: false,
    cooldownRemaining: 0,
    cooldownTimer: null,
    
    // 初始化
    async init() {
        await this.checkStatus();
        this.bindEvents();
        this.startCooldownTimer();
    },
    
    // 绑定事件
    bindEvents() {
        document.getElementById('aiGenerateBtn')?.addEventListener('click', () => this.generate());
    },
    
    // 检查LLM服务状态
    async checkStatus() {
        try {
            const resp = await fetch(`/api/review/llm/status?token=${APP_TOKEN}`);
            const result = await resp.json();
            
            this.enabled = result.enabled;
            this.cooldownRemaining = result.cooldown_remaining || 0;
            
            this.updateUI();
        } catch (err) {
            console.error('检查LLM状态失败:', err);
            this.enabled = false;
            this.updateUI();
        }
    },
    
    // 启动冷却计时器
    startCooldownTimer() {
        this.cooldownTimer = setInterval(() => {
            if (this.cooldownRemaining > 0) {
                this.cooldownRemaining--;
                this.updateCooldownDisplay();
            }
        }, 1000);
    },
    
    // 更新UI状态
    updateUI() {
        const section = document.getElementById('aiGenerateSection');
        const btn = document.getElementById('aiGenerateBtn');
        
        if (!section) return;
        
        if (!this.enabled) {
            section.style.display = 'none';
            return;
        }
        
        section.style.display = 'block';
        this.updateCooldownDisplay();
    },
    
    // 更新冷却显示
    updateCooldownDisplay() {
        const btn = document.getElementById('aiGenerateBtn');
        const cooldownEl = document.getElementById('aiCooldown');
        
        if (!btn) return;
        
        if (this.cooldownRemaining > 0) {
            btn.disabled = true;
            btn.classList.add('cooling');
            
            const minutes = Math.floor(this.cooldownRemaining / 60);
            const seconds = this.cooldownRemaining % 60;
            const timeStr = minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`;
            
            if (cooldownEl) {
                cooldownEl.textContent = `冷却中: ${timeStr}`;
                cooldownEl.style.display = 'inline';
            }
            btn.textContent = '🤖 冷却中...';
        } else {
            btn.disabled = false;
            btn.classList.remove('cooling');
            btn.textContent = '🤖 AI生成详细经历';
            
            if (cooldownEl) {
                cooldownEl.style.display = 'none';
            }
        }
    },
    
    // 收集角色信息
    collectCharInfo() {
        const charInfo = {
            name: document.getElementById('charName')?.value || '',
            age: document.getElementById('charAge')?.value || '',
            gender: document.getElementById('charGender')?.value || '',
            nationality: document.getElementById('charNationality')?.value || '',
            occupation: document.getElementById('charOccupation')?.value || '',
            era: document.getElementById('charEra')?.value || '',
            attributes: {},
            skills: {},
            backstory: {}
        };
        
        // 收集属性
        const attrIds = ['str', 'con', 'siz', 'dex', 'app', 'int', 'pow', 'edu', 'luk'];
        const attrKeys = ['STR', 'CON', 'SIZ', 'DEX', 'APP', 'INT', 'POW', 'EDU', 'LUK'];
        attrIds.forEach((id, i) => {
            const el = document.getElementById(id);
            if (el) {
                charInfo.attributes[attrKeys[i]] = parseInt(el.value) || 50;
            }
        });
        
        // 收集技能（只收集非基础值的技能）
        document.querySelectorAll('.skill-row').forEach(row => {
            const skillName = row.dataset.skill;
            const totalEl = row.querySelector('.total');
            if (skillName && totalEl) {
                const total = parseInt(totalEl.textContent) || 0;
                const baseEl = row.querySelector('.base');
                const base = baseEl?.tagName === 'INPUT' 
                    ? (parseInt(baseEl.value) || 0)
                    : (parseInt(baseEl?.textContent) || 0);
                
                // 只记录高于基础值的技能
                if (total > base) {
                    charInfo.skills[skillName] = total;
                }
            }
        });
        
        // 收集背景故事要素
        const backstoryFields = [
            'appearance', 'ideology', 'significant_people', 
            'meaningful_locations', 'treasured_possessions', 
            'traits', 'injuries', 'phobias'
        ];
        backstoryFields.forEach(field => {
            const el = document.querySelector(`textarea[name="${field}"]`);
            if (el && el.value.trim()) {
                charInfo.backstory[field] = el.value.trim();
            }
        });
        
        return charInfo;
    },
    
    // 生成详细经历
    async generate() {
        const btn = document.getElementById('aiGenerateBtn');
        const resultEl = document.getElementById('aiGenerateResult');
        
        if (!btn || btn.disabled) return;
        
        // 检查必要信息
        const charName = document.getElementById('charName')?.value?.trim();
        if (!charName) {
            showToast('请先填写角色名称', 'warning');
            return;
        }
        
        // 收集角色信息
        const charInfo = this.collectCharInfo();
        
        // 更新UI状态
        btn.disabled = true;
        btn.textContent = '🤖 生成中...';
        if (resultEl) {
            resultEl.innerHTML = '<p class="generating">AI正在生成详细经历，请稍候...</p>';
            resultEl.style.display = 'block';
        }
        
        try {
            const resp = await fetch('/api/review/llm/generate-backstory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: APP_TOKEN,
                    char_info: charInfo
                })
            });
            
            const result = await resp.json();
            
            // 更新冷却时间
            this.cooldownRemaining = result.cooldown_remaining || 0;
            
            if (result.success) {
                // 填充到详细经历文本框
                const storyEl = document.querySelector('textarea[name="detailed_story"]');
                if (storyEl) {
                    // 如果已有内容，询问是否覆盖
                    if (storyEl.value.trim()) {
                        if (confirm('详细经历已有内容，是否覆盖？')) {
                            storyEl.value = result.content;
                        } else {
                            // 追加到末尾
                            storyEl.value += '\n\n--- AI生成 ---\n' + result.content;
                        }
                    } else {
                        storyEl.value = result.content;
                    }
                    // 触发自动调整高度
                    if (typeof autoResizeTextarea === 'function') {
                        autoResizeTextarea(storyEl);
                    }
                }
                
                if (resultEl) {
                    resultEl.innerHTML = '<p class="success">✅ 生成成功！内容已填入详细经历</p>';
                }
                showToast('AI生成成功', 'success');
            } else {
                if (resultEl) {
                    resultEl.innerHTML = `<p class="error">❌ ${result.error || '生成失败'}</p>`;
                }
                showToast(result.error || '生成失败', 'error');
            }
        } catch (err) {
            console.error('AI生成失败:', err);
            if (resultEl) {
                resultEl.innerHTML = `<p class="error">❌ 请求失败: ${err.message}</p>`;
            }
            showToast('请求失败: ' + err.message, 'error');
        } finally {
            this.updateCooldownDisplay();
        }
    }
};
