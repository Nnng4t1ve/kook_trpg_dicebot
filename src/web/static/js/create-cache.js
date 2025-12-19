/**
 * COC7 角色卡创建器 - 缓存管理
 */

const CacheManager = {
    token: null,
    autoSaveInterval: null,
    lastSaveTime: null,
    AUTO_SAVE_INTERVAL: 30000, // 30秒自动保存
    
    // 初始化
    init(token) {
        this.token = token;
        this.bindEvents();
        this.startAutoSave();
        this.loadCachedData();
        this.updateTokenExpireDisplay();
        this.startTokenExpireCountdown();
    },
    
    // 绑定事件
    bindEvents() {
        document.getElementById('manualCacheBtn')?.addEventListener('click', () => this.manualSave());
    },
    
    // 启动自动保存
    startAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.autoSave();
        }, this.AUTO_SAVE_INTERVAL);
    },
    
    // 停止自动保存
    stopAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    },
    
    // 自动保存
    async autoSave() {
        const charName = document.getElementById('charName')?.value?.trim();
        if (!charName) {
            // 没有角色名称，不保存
            return;
        }
        
        await this.saveToServer(false);
    },
    
    // 手动保存
    async manualSave() {
        const charName = document.getElementById('charName')?.value?.trim();
        if (!charName) {
            showToast('请先填写角色名称', 'warning');
            return;
        }
        
        await this.saveToServer(true);
    },
    
    // 获取本职技能列表
    getOccupationSkills() {
        const occupationSkills = [];
        document.querySelectorAll('.skill-row.occupation-skill').forEach(row => {
            const skillName = row.dataset.skill;
            if (skillName) {
                occupationSkills.push(skillName);
            }
        });
        return occupationSkills;
    },
    
    // 获取随机属性组
    getRandomSets() {
        if (typeof AttributeManager !== 'undefined' && AttributeManager.previewSets) {
            return AttributeManager.previewSets;
        }
        return [];
    },
    
    // 保存到服务器
    async saveToServer(isManual = false) {
        const charName = document.getElementById('charName')?.value?.trim();
        if (!charName) return;
        
        const statusEl = document.getElementById('cacheStatus');
        const btnEl = document.getElementById('manualCacheBtn');
        
        // 更新状态为保存中
        if (statusEl) {
            statusEl.textContent = '保存中...';
            statusEl.className = 'saving';
        }
        if (btnEl) {
            btnEl.disabled = true;
            btnEl.classList.add('saving');
        }
        
        try {
            const data = FormManager.getFormData();
            const occupationSkills = this.getOccupationSkills();
            const randomSets = this.getRandomSets();
            
            const resp = await fetch('/api/character/cache', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: this.token,
                    char_name: charName,
                    char_data: data,
                    occupation_skills: occupationSkills,
                    random_sets: randomSets,
                }),
            });
            
            const result = await resp.json();
            
            if (result.success) {
                this.lastSaveTime = new Date();
                this.updateCacheStatus();
                if (isManual) {
                    showToast('角色卡已保存', 'success');
                }
            } else {
                if (statusEl) {
                    statusEl.textContent = '保存失败';
                    statusEl.className = '';
                }
                if (isManual) {
                    showToast('保存失败: ' + (result.detail || result.message), 'error');
                }
            }
        } catch (err) {
            if (statusEl) {
                statusEl.textContent = '保存失败';
                statusEl.className = '';
            }
            if (isManual) {
                showToast('保存失败: ' + err.message, 'error');
            }
        } finally {
            if (btnEl) {
                btnEl.disabled = false;
                btnEl.classList.remove('saving');
            }
        }
    },
    
    // 更新缓存状态显示
    updateCacheStatus() {
        const statusEl = document.getElementById('cacheStatus');
        if (!statusEl || !this.lastSaveTime) return;
        
        const now = new Date();
        const diff = Math.floor((now - this.lastSaveTime) / 1000);
        
        if (diff < 60) {
            statusEl.textContent = `已保存 (${diff}秒前)`;
        } else if (diff < 3600) {
            statusEl.textContent = `已保存 (${Math.floor(diff / 60)}分钟前)`;
        } else {
            statusEl.textContent = `已保存 (${Math.floor(diff / 3600)}小时前)`;
        }
        statusEl.className = 'cached';
    },
    
    // 加载缓存数据
    async loadCachedData() {
        try {
            const resp = await fetch(`/api/character/cache/${this.token}`);
            const result = await resp.json();
            
            if (result.success && result.char_data) {
                // 询问用户是否恢复
                const charName = result.char_name || '未命名';
                const createdAt = result.created_at ? new Date(result.created_at).toLocaleString() : '未知时间';
                
                if (confirm(`发现缓存的角色卡数据:\n角色名: ${charName}\n保存时间: ${createdAt}\n\n是否恢复?`)) {
                    this.restoreFormData(result.char_data);
                    // 保存本职技能列表，等技能加载完成后恢复
                    if (result.occupation_skills && result.occupation_skills.length > 0) {
                        this._pendingOccupationSkills = result.occupation_skills;
                    }
                    // 恢复随机属性组
                    if (result.random_sets && result.random_sets.length > 0) {
                        this.restoreRandomSets(result.random_sets);
                    }
                    this.lastSaveTime = new Date(result.created_at);
                    this.updateCacheStatus();
                    showToast('已恢复缓存数据', 'success');
                }
            }
        } catch (err) {
            // 忽略加载错误
            console.log('加载缓存失败:', err);
        }
    },
    
    // 恢复表单数据
    restoreFormData(data) {
        // 恢复角色名称
        if (data.name) {
            document.getElementById('charName').value = data.name;
        }
        
        // 恢复属性
        if (data.attributes) {
            const attrMap = {
                'STR': 'str', 'CON': 'con', 'SIZ': 'siz',
                'DEX': 'dex', 'APP': 'app', 'INT': 'int',
                'POW': 'pow', 'EDU': 'edu', 'LUK': 'luk'
            };
            for (const [key, id] of Object.entries(attrMap)) {
                const el = document.getElementById(id);
                if (el && data.attributes[key] !== undefined) {
                    el.value = data.attributes[key];
                }
            }
        }
        
        // 恢复武器
        if (data.weapons) {
            data.weapons.forEach((weapon, i) => {
                const idx = i + 1;
                const nameEl = document.querySelector(`input[name="weapon_name_${idx}"]`);
                const skillEl = document.querySelector(`input[name="weapon_skill_${idx}"]`);
                const damageEl = document.querySelector(`input[name="weapon_damage_${idx}"]`);
                if (nameEl) nameEl.value = weapon.name || '';
                if (skillEl) skillEl.value = weapon.skill || '';
                if (damageEl) damageEl.value = weapon.damage || '';
            });
        }
        
        // 恢复物品栏
        if (data.inventory) {
            data.inventory.forEach((inv, i) => {
                const itemEl = document.querySelector(`input[name="inv_item_${i}"]`);
                const backpackEl = document.querySelector(`input[name="inv_backpack_${i}"]`);
                if (itemEl) itemEl.value = inv.item || '';
                if (backpackEl) backpackEl.value = inv.backpack || '';
            });
        }
        
        // 恢复背景故事
        if (data.backstory) {
            for (const [key, value] of Object.entries(data.backstory)) {
                if (key.endsWith('_key')) {
                    const el = document.querySelector(`input[name="${key}"]`);
                    if (el) el.checked = value;
                } else {
                    const el = document.querySelector(`textarea[name="${key}"]`);
                    if (el) el.value = value;
                }
            }
        }
        
        // 触发属性更新
        AttributeManager.updateTotal();
        AttributeManager.updateDerived();
        
        // 恢复技能需要等技能加载完成后处理
        if (data.skills) {
            this._pendingSkills = data.skills;
            // 延迟恢复技能
            setTimeout(() => this.restoreSkills(), 500);
        }
    },
    
    // 恢复技能数据
    restoreSkills() {
        if (!this._pendingSkills) return;
        
        const skills = this._pendingSkills;
        delete this._pendingSkills;
        
        document.querySelectorAll('.skill-row').forEach(row => {
            const skillName = row.dataset.skill;
            if (skills[skillName] !== undefined) {
                const total = skills[skillName];
                const baseEl = row.querySelector('.base');
                const base = baseEl.tagName === 'INPUT'
                    ? (parseInt(baseEl.value) || 0)
                    : (parseInt(baseEl.textContent) || 0);
                
                // 计算需要分配的点数（简化处理，全部放到职业点）
                const allocated = total - base;
                if (allocated > 0) {
                    const jobEl = row.querySelector('.job');
                    if (jobEl) {
                        jobEl.value = allocated;
                        SkillManager.updateRowTotal(row);
                    }
                }
            }
        });
        
        // 恢复本职技能标记
        this.restoreOccupationSkills();
        
        PointsManager.calculateUsedPoints();
    },
    
    // 恢复本职技能标记
    restoreOccupationSkills() {
        if (!this._pendingOccupationSkills) return;
        
        const occupationSkills = this._pendingOccupationSkills;
        delete this._pendingOccupationSkills;
        
        document.querySelectorAll('.skill-row').forEach(row => {
            const skillName = row.dataset.skill;
            if (occupationSkills.includes(skillName)) {
                const nameCell = row.querySelector('.skill-name');
                if (nameCell && !row.classList.contains('occupation-skill')) {
                    row.classList.add('occupation-skill');
                    if (!nameCell.querySelector('.occ-marker')) {
                        const marker = document.createElement('span');
                        marker.className = 'occ-marker';
                        marker.textContent = '★';
                        nameCell.insertBefore(marker, nameCell.firstChild);
                    }
                }
            }
        });
        
        // 更新审核按钮状态
        if (typeof ReviewManager !== 'undefined') {
            ReviewManager.updateReviewButton();
        }
    },
    
    // 恢复随机属性组
    restoreRandomSets(randomSets) {
        if (!randomSets || randomSets.length === 0) return;
        
        if (typeof AttributeManager !== 'undefined') {
            AttributeManager.previewSets = randomSets;
            // 显示预览面板
            const panel = document.getElementById('randomPreviewPanel');
            if (panel) {
                panel.style.display = 'block';
                AttributeManager.renderPreview();
            }
        }
    },
    
    // Token过期时间显示
    tokenRemainingSeconds: 0,
    
    // 更新Token过期时间显示
    updateTokenExpireDisplay() {
        this.tokenRemainingSeconds = typeof TOKEN_REMAINING_SECONDS !== 'undefined' ? TOKEN_REMAINING_SECONDS : 0;
        this.renderTokenExpire();
    },
    
    // 启动Token过期倒计时
    startTokenExpireCountdown() {
        setInterval(() => {
            if (this.tokenRemainingSeconds > 0) {
                this.tokenRemainingSeconds--;
                this.renderTokenExpire();
            }
        }, 1000);
        
        // 每分钟更新缓存状态显示
        setInterval(() => {
            this.updateCacheStatus();
        }, 60000);
    },
    
    // 渲染Token过期时间
    renderTokenExpire() {
        const el = document.getElementById('tokenExpireTime');
        const infoEl = document.querySelector('.token-expire-info');
        if (!el) return;
        
        const seconds = this.tokenRemainingSeconds;
        
        if (seconds <= 0) {
            el.textContent = '已过期';
            if (infoEl) infoEl.classList.add('danger');
            return;
        }
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        let text = '';
        if (days > 0) {
            text = `${days}天 ${hours}小时 ${minutes}分钟`;
        } else if (hours > 0) {
            text = `${hours}小时 ${minutes}分钟`;
        } else if (minutes > 0) {
            text = `${minutes}分钟 ${secs}秒`;
        } else {
            text = `${secs}秒`;
        }
        
        el.textContent = text;
        
        // 根据剩余时间设置样式
        if (infoEl) {
            infoEl.classList.remove('warning', 'danger');
            if (seconds < 3600) { // 小于1小时
                infoEl.classList.add('danger');
            } else if (seconds < 86400) { // 小于1天
                infoEl.classList.add('warning');
            }
        }
    }
};
