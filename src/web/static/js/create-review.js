/**
 * COC7 角色卡创建器 - 审核和提交
 */

const ReviewManager = {
    token: null,
    userId: null,

    // 初始化
    init(token, userId) {
        this.token = token;
        this.userId = userId;
    },

    // 将 input 转换为文本（用于截图）
    convertInputsToText(container) {
        const inputs = container.querySelectorAll('input[type="number"], input[type="text"]');
        const restoreList = [];

        inputs.forEach(input => {
            const value = input.value || '0';
            const span = document.createElement('span');
            span.textContent = value;
            span.className = 'input-snapshot';
            span.style.cssText = `
                display: inline-block;
                width: ${input.offsetWidth}px;
                height: ${input.offsetHeight}px;
                line-height: ${input.offsetHeight}px;
                text-align: center;
                color: #fff;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 6px;
                font-size: ${window.getComputedStyle(input).fontSize};
            `;

            input.style.display = 'none';
            input.parentNode.insertBefore(span, input.nextSibling);
            restoreList.push({ input, span });
        });

        return restoreList;
    },

    // 恢复 input 显示
    restoreInputs(restoreList) {
        restoreList.forEach(({ input, span }) => {
            input.style.display = '';
            span.remove();
        });
    },

    // 检查技能是否超出上限
    checkSkillLimits() {
        // 检查全局变量是否定义且有值
        const hasSkillLimit = typeof SKILL_LIMIT !== 'undefined' && SKILL_LIMIT !== null;
        const hasOccLimit = typeof OCC_LIMIT !== 'undefined' && OCC_LIMIT !== null;
        const hasNonOccLimit = typeof NON_OCC_LIMIT !== 'undefined' && NON_OCC_LIMIT !== null;
        
        // 如果没有任何上限设置，直接返回有效
        if (!hasSkillLimit && !hasOccLimit && !hasNonOccLimit) {
            return { valid: true, errors: [] };
        }
        
        const errors = [];
        document.querySelectorAll('.skill-row').forEach(row => {
            const skillName = row.dataset.skill;
            const total = parseInt(row.querySelector('.total').textContent) || 0;
            const isOccupation = row.classList.contains('occupation-skill');
            
            // 跳过母语技能（基础值为EDU，可能超过上限）
            if (skillName.startsWith('母语')) return;
            
            // 跳过信用评级（和母语一样不在上限计算里）
            if (skillName === '信用评级') return;
            
            // 只检查有实际点数的技能（排除初始值）
            if (total <= 0) return;
            
            if (hasSkillLimit && total > SKILL_LIMIT) {
                errors.push(`${skillName}: ${total} > ${SKILL_LIMIT}`);
            } else if (hasOccLimit && hasNonOccLimit) {
                if (isOccupation && total > OCC_LIMIT) {
                    errors.push(`${skillName}(本职): ${total} > ${OCC_LIMIT}`);
                } else if (!isOccupation && total > NON_OCC_LIMIT) {
                    errors.push(`${skillName}(非本职): ${total} > ${NON_OCC_LIMIT}`);
                }
            }
        });
        
        return { valid: errors.length === 0, errors };
    },

    // 提交审核
    async submitReview() {
        const data = FormManager.getFormData();
        if (!data.name) {
            alert('请填写角色名称');
            return;
        }
        if (PointsManager.isOverspent()) {
            alert('点数超支，无法提交审核');
            return;
        }
        
        // 检查技能上限
        const limitCheck = this.checkSkillLimits();
        if (!limitCheck.valid) {
            alert('技能超出上限，无法提交审核:\n' + limitCheck.errors.join('\n'));
            return;
        }

        const btn = document.getElementById('exportBtn');
        btn.disabled = true;
        btn.textContent = '📸 生成截图中...';

        let restoreList = [];
        try {
            const container = document.querySelector('.container');
            restoreList = this.convertInputsToText(container);

            await new Promise(r => setTimeout(r, 100));

            const canvas = await html2canvas(container, {
                backgroundColor: '#1a1a2e',
                scale: 2,
                useCORS: true,
            });
            const imageData = canvas.toDataURL('image/png');

            this.restoreInputs(restoreList);
            restoreList = [];

            btn.textContent = '📤 提交审核中...';

            const resp = await fetch('/api/character/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: this.token,
                    char_name: data.name,
                    image_data: imageData,
                    char_data: data,
                }),
            });
            const result = await resp.json();

            if (result.success) {
                document.getElementById('exportText').value = `.cc ${data.name}`;
                document.getElementById('exportResult').style.display = 'block';
                showToast('审核已提交！在 KOOK 中使用 .cc ' + data.name + ' 发起审核', 'success');
            } else {
                alert('提交失败: ' + (result.detail || result.message));
            }
        } catch (err) {
            alert('错误: ' + err.message);
            if (restoreList.length > 0) {
                this.restoreInputs(restoreList);
            }
        } finally {
            this.updateReviewButton();
        }
    },

    // 更新审核按钮状态
    updateReviewButton() {
        const reviewBtn = document.getElementById('exportBtn');
        
        if (PointsManager.isOverspent()) {
            reviewBtn.disabled = true;
            reviewBtn.textContent = '⚠️ 点数超支，无法审核';
            return;
        }
        
        // 检查技能上限
        const limitCheck = this.checkSkillLimits();
        if (!limitCheck.valid) {
            reviewBtn.disabled = true;
            reviewBtn.textContent = '⚠️ 技能超出上限，无法审核';
            return;
        }
        
        reviewBtn.disabled = false;
        reviewBtn.textContent = '📋 角色卡审核';
    },

    // 检查审核状态
    async checkReviewStatus() {
        const charName = document.getElementById('charName').value.trim();
        if (!charName) return;

        try {
            const resp = await fetch(`/api/character/review/${encodeURIComponent(charName)}`);
            if (resp.ok) {
                const data = await resp.json();
                const submitBtn = document.getElementById('submitBtn');
                if (data.approved) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = '✨ 创建角色卡 (已审核通过)';
                    submitBtn.classList.add('approved');
                }
            }
        } catch (err) {
            // 忽略错误
        }
    },

    // 提交创建角色
    async submitCreate() {
        const charName = document.getElementById('charName').value.trim();
        if (!charName) {
            alert('请填写角色名称');
            return;
        }

        const btn = document.getElementById('submitBtn');

        try {
            const resp = await fetch(`/api/character/review/${encodeURIComponent(charName)}`);
            if (!resp.ok) {
                alert('请先提交角色卡审核，在 KOOK 中使用 .cc 命令发起审核');
                return;
            }
            const reviewData = await resp.json();
            if (!reviewData.approved) {
                alert('角色卡尚未审核通过，请等待 KP 审核');
                return;
            }
        } catch (err) {
            alert('请先提交角色卡审核');
            return;
        }

        btn.disabled = true;
        btn.textContent = '创建中...';

        try {
            const resp = await fetch('/api/character/create-approved', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    char_name: charName,
                    user_id: this.userId,
                }),
            });
            const data = await resp.json();
            if (data.success) {
                document.getElementById('charForm').style.display = 'none';
                document.getElementById('exportResult').style.display = 'none';
                document.getElementById('result').innerHTML = '<div class="success"><h2>✅ ' + data.message + '</h2><p>返回 KOOK 使用 .pc show 查看</p></div>';
                document.getElementById('result').style.display = 'block';
            } else {
                alert('失败: ' + (data.detail || data.message));
                btn.disabled = false;
                btn.textContent = '✨ 创建角色卡';
            }
        } catch (err) {
            alert('错误: ' + err.message);
            btn.disabled = false;
            btn.textContent = '✨ 创建角色卡';
        }
    },

    // 复制指令
    copyCommand() {
        document.getElementById('exportText').select();
        document.execCommand('copy');
        const btn = document.getElementById('copyBtn');
        btn.textContent = '✅ 已复制';
        setTimeout(() => btn.textContent = '复制', 2000);
    },

    // 绑定事件
    bindEvents() {
        document.getElementById('exportBtn')?.addEventListener('click', () => this.submitReview());
        document.getElementById('copyBtn')?.addEventListener('click', () => this.copyCommand());
        document.getElementById('charForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitCreate();
        });

        // 定期检查审核状态
        setInterval(() => this.checkReviewStatus(), 5000);
    }
};
