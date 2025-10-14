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
            allowCustomMinute: options.allowCustomMinute !== false,
            onChange: options.onChange || null,
            ...options
        };

        this.render();
        this.attachEvents();
    }

    render() {
        const minuteOptions = this.generateMinuteOptions();

        this.container.innerHTML = `
            <div class="time-picker">
                <div class="time-picker-group">
                    <label class="time-picker-label">時</label>
                    <select class="time-picker-select time-picker-hour" aria-label="時">
                        ${this.generateHourOptions()}
                    </select>
                    <span class="time-picker-unit">時</span>
                </div>

                <span class="time-picker-separator">:</span>

                <div class="time-picker-group">
                    <label class="time-picker-label">分</label>
                    <select class="time-picker-select time-picker-minute" aria-label="分">
                        ${minuteOptions}
                    </select>
                    <span class="time-picker-unit">分</span>
                </div>

                ${this.options.allowCustomMinute ? `
                <div class="time-picker-custom">
                    <label class="time-picker-custom-label">
                        <input type="checkbox" class="time-picker-custom-toggle">
                        カスタム入力
                    </label>
                    <input type="number" class="time-picker-custom-input"
                           min="0" max="59" step="1"
                           placeholder="0-59"
                           aria-label="カスタム分"
                           disabled>
                </div>
                ` : ''}
            </div>
        `;

        // 初期値をセット
        this.setTime(this.options.defaultHour, this.options.defaultMinute);
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
        const hourSelect = this.container.querySelector('.time-picker-hour');
        const minuteSelect = this.container.querySelector('.time-picker-minute');

        if (hourSelect) {
            hourSelect.addEventListener('change', () => this.handleChange());
        }

        if (minuteSelect) {
            minuteSelect.addEventListener('change', () => this.handleChange());
        }

        if (this.options.allowCustomMinute) {
            const customToggle = this.container.querySelector('.time-picker-custom-toggle');
            const customInput = this.container.querySelector('.time-picker-custom-input');

            if (customToggle && customInput) {
                customToggle.addEventListener('change', (e) => {
                    const isCustom = e.target.checked;
                    customInput.disabled = !isCustom;
                    minuteSelect.disabled = isCustom;

                    if (isCustom) {
                        customInput.focus();
                    } else {
                        this.handleChange();
                    }
                });

                customInput.addEventListener('input', () => {
                    if (!customInput.disabled) {
                        this.handleChange();
                    }
                });
            }
        }
    }

    handleChange() {
        if (this.options.onChange) {
            const time = this.getTime();
            this.options.onChange(time);
        }
    }

    setTime(hour, minute) {
        const hourSelect = this.container.querySelector('.time-picker-hour');
        const minuteSelect = this.container.querySelector('.time-picker-minute');

        if (hourSelect) {
            hourSelect.value = hour;
        }

        if (minuteSelect) {
            // 15分刻みに丸める
            const roundedMinute = Math.round(minute / this.options.minuteStep) * this.options.minuteStep;
            minuteSelect.value = roundedMinute;
        }
    }

    setTimeFromString(timeString) {
        // "HH:MM" 形式の文字列をパース
        const [hour, minute] = timeString.split(':').map(Number);
        this.setTime(hour, minute);
    }

    getTime() {
        const hourSelect = this.container.querySelector('.time-picker-hour');
        const minuteSelect = this.container.querySelector('.time-picker-minute');
        const customToggle = this.container.querySelector('.time-picker-custom-toggle');
        const customInput = this.container.querySelector('.time-picker-custom-input');

        let hour = parseInt(hourSelect.value);
        let minute;

        if (customToggle && customToggle.checked) {
            minute = parseInt(customInput.value) || 0;
        } else {
            minute = parseInt(minuteSelect.value);
        }

        // バリデーション
        hour = Math.max(0, Math.min(23, hour));
        minute = Math.max(0, Math.min(59, minute));

        return {
            hour,
            minute,
            formatted: `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
        };
    }

    getValue() {
        return this.getTime().formatted;
    }
}

// グローバルに公開
window.TimePicker = TimePicker;
