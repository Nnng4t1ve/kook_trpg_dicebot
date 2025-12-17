/**
 * COC7 角色卡创建器 - 点数系统
 */

const PointsManager = {
    totalJobPoints: null,
    totalHobbyPoints: null,
    usedJobPoints: 0,
    usedHobbyPoints: 0,
    lastJobRemain: null,
    lastHobbyRemain: null,

    // 更新点数显示
    updateDisplay() {
        const jobEl = document.getElementById('jobPointsRemain');
        const hobbyEl = document.getElementById('hobbyPointsRemain');
        const submitBtn = document.getElementById('submitBtn');
        const reviewBtn = document.getElementById('exportBtn');

        jobEl.classList.remove('zero', 'negative');
        hobbyEl.classList.remove('zero', 'negative');

        // 职业点数
        if (this.totalJobPoints === null) {
            jobEl.textContent = '--';
        } else {
            const jobRemain = this.totalJobPoints - this.usedJobPoints;
            jobEl.textContent = jobRemain;

            if (jobRemain === 0) {
                jobEl.classList.add('zero');
                if (this.lastJobRemain !== 0) showToast('职业点数已用完！', 'success');
            } else if (jobRemain < 0) {
                jobEl.classList.add('negative');
            }
            this.lastJobRemain = jobRemain;
        }

        // 兴趣点数
        if (this.totalHobbyPoints === null) {
            hobbyEl.textContent = '--';
        } else {
            const hobbyRemain = this.totalHobbyPoints - this.usedHobbyPoints;
            hobbyEl.textContent = hobbyRemain;

            if (hobbyRemain === 0) {
                hobbyEl.classList.add('zero');
                if (this.lastHobbyRemain !== 0) showToast('兴趣点数已用完！', 'success');
            } else if (hobbyRemain < 0) {
                hobbyEl.classList.add('negative');
            }
            this.lastHobbyRemain = hobbyRemain;
        }

        // 更新按钮状态
        const isOverspent = this.isOverspent();
        if (isOverspent) {
            submitBtn.disabled = true;
            submitBtn.textContent = '⚠️ 点数超支，无法创建';
            reviewBtn.disabled = true;
            reviewBtn.textContent = '⚠️ 点数超支，无法审核';
        } else {
            submitBtn.disabled = true;
            submitBtn.textContent = '✨ 创建角色卡 (需先审核通过)';
            reviewBtn.disabled = false;
            reviewBtn.textContent = '📋 角色卡审核';
        }
    },

    // 计算职业点数
    calculateJobPoints() {
        const checked = document.querySelectorAll('.attr-checkbox:checked');
        const checkedAttrs = Array.from(checked).map(cb => cb.dataset.attr);

        let formula = '';
        if (checkedAttrs.length === 0) {
            this.totalJobPoints = null;
            this.lastJobRemain = null;
            formula = '未选择属性（不限制）';
        } else if (checkedAttrs.length === 1) {
            const val = getNumValue(checkedAttrs[0]);
            this.totalJobPoints = val * 4;
            formula = `${checkedAttrs[0].toUpperCase()} × 4 = ${this.totalJobPoints}`;
        } else {
            const val1 = getNumValue(checkedAttrs[0]);
            const val2 = getNumValue(checkedAttrs[1]);
            this.totalJobPoints = val1 * 2 + val2 * 2;
            formula = `${checkedAttrs[0].toUpperCase()}×2 + ${checkedAttrs[1].toUpperCase()}×2 = ${this.totalJobPoints}`;
        }

        setText('jobFormula', formula);
        this.calculateHobbyPoints();
    },

    // 计算兴趣点数
    calculateHobbyPoints() {
        const hasSelectedAttr = document.querySelectorAll('.attr-checkbox:checked').length > 0;
        if (hasSelectedAttr) {
            this.totalHobbyPoints = getNumValue('int') * 2;
        } else {
            this.totalHobbyPoints = null;
            this.lastHobbyRemain = null;
        }
        this.updateDisplay();
    },

    // 计算已使用点数
    calculateUsedPoints() {
        this.usedJobPoints = 0;
        this.usedHobbyPoints = 0;

        document.querySelectorAll('.skill-row').forEach(row => {
            const jobInput = row.querySelector('.job');
            const hobbyInput = row.querySelector('.hobby');

            if (jobInput && !jobInput.disabled) {
                this.usedJobPoints += parseInt(jobInput.value) || 0;
            }
            if (hobbyInput && !hobbyInput.disabled) {
                this.usedHobbyPoints += parseInt(hobbyInput.value) || 0;
            }
        });

        this.updateDisplay();
    },

    // 检查是否超支
    isOverspent() {
        const jobOverspent = this.totalJobPoints !== null && (this.totalJobPoints - this.usedJobPoints) < 0;
        const hobbyOverspent = this.totalHobbyPoints !== null && (this.totalHobbyPoints - this.usedHobbyPoints) < 0;
        return jobOverspent || hobbyOverspent;
    },

    // 设置复选框限制
    setupCheckboxLimit() {
        document.querySelectorAll('.attr-checkbox').forEach(cb => {
            cb.addEventListener('change', () => {
                const checked = document.querySelectorAll('.attr-checkbox:checked');
                if (checked.length > 2) {
                    cb.checked = false;
                    showToast('最多只能选择2个属性！');
                    return;
                }
                this.calculateJobPoints();
            });
        });
    }
};
