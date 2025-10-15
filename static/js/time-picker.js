/**
 * TimePicker Component
 * 時間と分を分離した入力UIコンポーネント
 */

class TimePicker {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }

        this.options = {
            defaultHour: options.defaultHour || 13,
            defaultMinute: options.defaultMinute || 0,
            minuteStep: options.minuteStep || 15,
            allowAsap: options.allowAsap !== false,
            onChange: options.onChange || null,
            ...options
        };

        this.render();
        this.attachEvents();
    }

    render() {
        this.container.innerHTML = `
            <div class="time-picker">
                <div class="time-picker-group">
                    <button type="button" class="time-picker-btn time-picker-hour-up" aria-label="時を増やす">▲</button>
                    <div class="time-picker-display-wrapper">
                        <span class="time-picker-display time-picker-hour-display">13</span>
                        <span class="time-picker-unit">時</span>
                    </div>
                    <button type="button" class="time-picker-btn time-picker-hour-down" aria-label="時を減らす">▼</button>
                </div>

                <span class="time-picker-separator">:</span>

                <div class="time-picker-group">
                    <button type="button" class="time-picker-btn time-picker-minute-up" aria-label="分を増やす">▲</button>
                    <div class="time-picker-display-wrapper">
                        <span class="time-picker-display time-picker-minute-display">00</span>
                        <span class="time-picker-unit">分</span>
                    </div>
                    <button type="button" class="time-picker-btn time-picker-minute-down" aria-label="分を減らす">▼</button>
                </div>

                ${this.options.allowAsap ? `
                <div class="time-picker-asap">
                    <label class="time-picker-asap-label">
                        <input type="checkbox" class="time-picker-asap-toggle">
                        なる早
                    </label>
                </div>
                ` : ''}
            </div>
        `;

        // 初期値をセット
        this.currentHour = this.options.defaultHour;
        this.currentMinute = this.options.defaultMinute;
        this.updateDisplay();
    }

    generateHourOptions() {
        let options = '';
        for (let i = 0; i < 24; i++) {
            const hour = i.toString().padStart(2, '0');
            options += `<option value="${i}">${hour}</option>`;
        }
        return options;
    }

    generateMinuteOptions() {
        let options = '';
        for (let i = 0; i < 60; i += this.options.minuteStep) {
            const minute = i.toString().padStart(2, '0');
            options += `<option value="${i}">${minute}</option>`;
        }
        return options;
    }

    attachEvents() {
        const hourUpBtn = this.container.querySelector('.time-picker-hour-up');
        const hourDownBtn = this.container.querySelector('.time-picker-hour-down');
        const minuteUpBtn = this.container.querySelector('.time-picker-minute-up');
        const minuteDownBtn = this.container.querySelector('.time-picker-minute-down');

        if (hourUpBtn) {
            hourUpBtn.addEventListener('click', () => {
                this.currentHour = (this.currentHour + 1) % 24;
                this.updateDisplay();
                this.handleChange();
            });
        }

        if (hourDownBtn) {
            hourDownBtn.addEventListener('click', () => {
                this.currentHour = (this.currentHour - 1 + 24) % 24;
                this.updateDisplay();
                this.handleChange();
            });
        }

        if (minuteUpBtn) {
            minuteUpBtn.addEventListener('click', () => {
                this.currentMinute = (this.currentMinute + this.options.minuteStep) % 60;
                this.updateDisplay();
                this.handleChange();
            });
        }

        if (minuteDownBtn) {
            minuteDownBtn.addEventListener('click', () => {
                this.currentMinute = (this.currentMinute - this.options.minuteStep + 60) % 60;
                this.updateDisplay();
                this.handleChange();
            });
        }

        if (this.options.allowAsap) {
            const asapToggle = this.container.querySelector('.time-picker-asap-toggle');

            if (asapToggle) {
                asapToggle.addEventListener('change', (e) => {
                    const isAsap = e.target.checked;
                    const buttons = this.container.querySelectorAll('.time-picker-btn');
                    buttons.forEach(btn => btn.disabled = isAsap);
                    this.handleChange();
                });
            }
        }
    }

    updateDisplay() {
        const hourDisplay = this.container.querySelector('.time-picker-hour-display');
        const minuteDisplay = this.container.querySelector('.time-picker-minute-display');

        if (hourDisplay) {
            hourDisplay.textContent = this.currentHour.toString().padStart(2, '0');
        }

        if (minuteDisplay) {
            minuteDisplay.textContent = this.currentMinute.toString().padStart(2, '0');
        }
    }

    handleChange() {
        if (this.options.onChange) {
            const time = this.getTime();
            this.options.onChange(time);
        }
    }

    setTime(hour, minute) {
        this.currentHour = hour;
        // 15分刻みに丸める
        this.currentMinute = Math.round(minute / this.options.minuteStep) * this.options.minuteStep;
        this.updateDisplay();
    }

    setTimeFromString(timeString) {
        // "HH:MM" 形式の文字列をパース
        const [hour, minute] = timeString.split(':').map(Number);
        this.setTime(hour, minute);
    }

    getTime() {
        const asapToggle = this.container.querySelector('.time-picker-asap-toggle');

        // なる早モードの場合
        if (asapToggle && asapToggle.checked) {
            return {
                hour: null,
                minute: null,
                formatted: 'なるべく早めに出勤',
                isAsap: true
            };
        }

        // バリデーション
        const hour = Math.max(0, Math.min(23, this.currentHour));
        const minute = Math.max(0, Math.min(59, this.currentMinute));

        return {
            hour,
            minute,
            formatted: `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`,
            isAsap: false
        };
    }

    getValue() {
        return this.getTime().formatted;
    }
}

// グローバルに公開
window.TimePicker = TimePicker;
