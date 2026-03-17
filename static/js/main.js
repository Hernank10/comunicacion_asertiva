/* ============================================
   MAIN JAVASCRIPT - ComunicaPro
   Funciones globales y utilidades
   ============================================ */

// ============================================
// INICIALIZACIÓN GLOBAL
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ ComunicaPro iniciado correctamente');
    
    // Inicializar todas las funcionalidades
    initTooltips();
    initPopovers();
    initScrollSpy();
    initBackToTop();
    initFormValidation();
    initPasswordStrength();
    initCharacterCounters();
    initAutoSave();
    initKeyboardShortcuts();
    initThemeToggle();
    initAnimations();
    
    // Cargar datos del usuario si está autenticado
    if (window.currentUser) {
        loadUserPreferences();
    }
});

// ============================================
// UTILIDADES DE ALMACENAMIENTO LOCAL
// ============================================

const Storage = {
    // Guardar con expiración
    set: function(key, value, ttl = null) {
        const item = {
            value: value,
            timestamp: new Date().getTime()
        };
        if (ttl) {
            item.expiry = new Date().getTime() + (ttl * 1000);
        }
        localStorage.setItem(key, JSON.stringify(item));
    },
    
    // Obtener valor
    get: function(key) {
        const itemStr = localStorage.getItem(key);
        if (!itemStr) return null;
        
        try {
            const item = JSON.parse(itemStr);
            const now = new Date().getTime();
            
            if (item.expiry && now > item.expiry) {
                localStorage.removeItem(key);
                return null;
            }
            
            return item.value;
        } catch(e) {
            return null;
        }
    },
    
    // Eliminar
    remove: function(key) {
        localStorage.removeItem(key);
    },
    
    // Limpiar todo
    clear: function() {
        localStorage.clear();
    },
    
    // Guardar progreso de práctica
    savePracticeProgress: function(data) {
        this.set('practice_progress', data, 3600); // 1 hora
    },
    
    // Cargar progreso de práctica
    loadPracticeProgress: function() {
        return this.get('practice_progress');
    },
    
    // Guardar preferencias de usuario
    saveUserPreferences: function(prefs) {
        this.set('user_preferences', prefs);
    },
    
    // Cargar preferencias de usuario
    loadUserPreferences: function() {
        return this.get('user_preferences') || {};
    }
};

// ============================================
// NOTIFICACIONES
// ============================================

const Notifications = {
    // Mostrar notificación toast
    toast: function(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="bi ${this.getIcon(type)}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="bi bi-x"></i>
            </button>
        `;
        
        document.body.appendChild(toast);
        
        // Mostrar con animación
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Auto-cerrar
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
        
        return toast;
    },
    
    // Obtener ícono según tipo
    getIcon: function(type) {
        const icons = {
            success: 'bi-check-circle-fill',
            error: 'bi-exclamation-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill'
        };
        return icons[type] || icons.info;
    },
    
    // Mostrar confirmación
    confirm: function(message, title = 'Confirmación') {
        return new Promise((resolve) => {
            // Crear modal de confirmación
            const modal = document.createElement('div');
            modal.className = 'modal fade show confirm-modal';
            modal.style.display = 'block';
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-question-circle me-2"></i>
                                ${title}
                            </h5>
                            <button type="button" class="btn-close btn-close-white" onclick="this.closest('.modal').remove()"></button>
                        </div>
                        <div class="modal-body">
                            <p class="lead mb-0">${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">
                                Cancelar
                            </button>
                            <button type="button" class="btn btn-primary" id="confirmBtn">
                                Aceptar
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Manejar confirmación
            document.getElementById('confirmBtn').onclick = () => {
                modal.remove();
                resolve(true);
            };
            
            // Manejar cierre
            modal.querySelector('.btn-close').onclick = () => {
                modal.remove();
                resolve(false);
            };
        });
    }
};

// ============================================
// VALIDACIÓN DE FORMULARIOS
// ============================================

const FormValidator = {
    // Validar email
    email: function(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },
    
    // Validar usuario
    username: function(username) {
        const re = /^[a-zA-Z0-9_]{3,20}$/;
        return re.test(username);
    },
    
    // Validar contraseña
    password: function(password) {
        return password.length >= 6;
    },
    
    // Validar contraseña fuerte
    strongPassword: function(password) {
        const hasUpperCase = /[A-Z]/.test(password);
        const hasLowerCase = /[a-z]/.test(password);
        const hasNumbers = /\d/.test(password);
        const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        return password.length >= 8 && hasUpperCase && hasLowerCase && hasNumbers && hasSpecial;
    },
    
    // Validar coincidencia de contraseñas
    passwordMatch: function(password, confirm) {
        return password === confirm;
    },
    
    // Validar campo requerido
    required: function(value) {
        return value && value.trim().length > 0;
    },
    
    // Validar número en rango
    range: function(value, min, max) {
        const num = parseInt(value);
        return !isNaN(num) && num >= min && num <= max;
    },
    
    // Validar URL
    url: function(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }
};

// ============================================
// FORMATEO DE DATOS
// ============================================

const Formatter = {
    // Formatear fecha
    date: function(date, format = 'dd/mm/yyyy') {
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';
        
        const day = d.getDate().toString().padStart(2, '0');
        const month = (d.getMonth() + 1).toString().padStart(2, '0');
        const year = d.getFullYear();
        const hours = d.getHours().toString().padStart(2, '0');
        const minutes = d.getMinutes().toString().padStart(2, '0');
        
        return format
            .replace('dd', day)
            .replace('mm', month)
            .replace('yyyy', year)
            .replace('HH', hours)
            .replace('MM', minutes);
    },
    
    // Formatear tiempo (segundos a formato legible)
    time: function(seconds) {
        if (seconds < 60) return `${seconds} segundos`;
        if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            return `${minutes} minutos`;
        }
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    },
    
    // Formatear número con separadores de miles
    number: function(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    },
    
    // Formatear porcentaje
    percentage: function(value, decimals = 1) {
        return `${value.toFixed(decimals)}%`;
    },
    
    // Formatear estrellas
    stars: function(count, max = 5) {
        return '★'.repeat(count) + '☆'.repeat(max - count);
    }
};

// ============================================
// ANIMACIONES
// ============================================

const Animations = {
    // Animar conteo
    countUp: function(element, start, end, duration = 1000) {
        const range = end - start;
        const increment = range / (duration / 10);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= end) {
                element.textContent = end;
                clearInterval(timer);
            } else {
                element.textContent = Math.round(current);
            }
        }, 10);
    },
    
    // Animar elemento al hacer scroll
    scrollReveal: function() {
        const elements = document.querySelectorAll('.reveal');
        const windowHeight = window.innerHeight;
        
        elements.forEach(el => {
            const elementTop = el.getBoundingClientRect().top;
            const elementVisible = 150;
            
            if (elementTop < windowHeight - elementVisible) {
                el.classList.add('active');
            }
        });
    },
    
    // Agregar efecto de onda al hacer click
    ripple: function(event) {
        const button = event.currentTarget;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.className = 'ripple';
        
        button.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
    },
    
    // Efecto de escritura
    typewriter: function(element, text, speed = 50) {
        let i = 0;
        element.textContent = '';
        
        function type() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        }
        
        type();
    }
};

// ============================================
// FUNCIONES DE INICIALIZACIÓN
// ============================================

function initTooltips() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
}

function initPopovers() {
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => new bootstrap.Popover(popover));
}

function initScrollSpy() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    
    window.addEventListener('scroll', () => {
        let current = '';
        const scrollY = window.scrollY;
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop - 100;
            const sectionHeight = section.clientHeight;
            
            if (scrollY >= sectionTop && scrollY < sectionTop + sectionHeight) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
                link.classList.add('active');
            }
        });
    });
}

function initBackToTop() {
    const btn = document.getElementById('btnTop');
    if (!btn) return;
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            btn.style.display = 'block';
        } else {
            btn.style.display = 'none';
        }
    });
    
    btn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

function initFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

function initPasswordStrength() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            const strength = calculatePasswordStrength(this.value);
            updatePasswordStrengthIndicator(this, strength);
        });
    });
}

function calculatePasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 6) strength += 20;
    if (password.length >= 8) strength += 10;
    if (/[a-z]/.test(password)) strength += 20;
    if (/[A-Z]/.test(password)) strength += 20;
    if (/[0-9]/.test(password)) strength += 20;
    if (/[^a-zA-Z0-9]/.test(password)) strength += 10;
    
    return Math.min(strength, 100);
}

function updatePasswordStrengthIndicator(input, strength) {
    const container = input.closest('.mb-3');
    let indicator = container.querySelector('.password-strength');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.className = 'password-strength mt-2';
        indicator.innerHTML = `
            <div class="progress" style="height: 5px;">
                <div class="progress-bar" role="progressbar" style="width: 0%"></div>
            </div>
        `;
        container.appendChild(indicator);
    }
    
    const bar = indicator.querySelector('.progress-bar');
    bar.style.width = strength + '%';
    
    if (strength < 30) {
        bar.className = 'progress-bar bg-danger';
    } else if (strength < 60) {
        bar.className = 'progress-bar bg-warning';
    } else if (strength < 80) {
        bar.className = 'progress-bar bg-info';
    } else {
        bar.className = 'progress-bar bg-success';
    }
}

function initCharacterCounters() {
    const textareas = document.querySelectorAll('textarea[maxlength]');
    
    textareas.forEach(textarea => {
        const counter = document.createElement('small');
        counter.className = 'form-text text-muted float-end';
        textarea.parentNode.appendChild(counter);
        
        const updateCounter = () => {
            const remaining = textarea.maxLength - textarea.value.length;
            counter.textContent = `${remaining} caracteres restantes`;
            
            if (remaining < 20) {
                counter.classList.add('text-danger');
                counter.classList.remove('text-muted');
            } else {
                counter.classList.remove('text-danger');
                counter.classList.add('text-muted');
            }
        };
        
        textarea.addEventListener('input', updateCounter);
        updateCounter();
    });
}

function initAutoSave() {
    const forms = document.querySelectorAll('[data-autosave]');
    
    forms.forEach(form => {
        const formId = form.id || 'form_' + Math.random().toString(36).substr(2, 9);
        const inputs = form.querySelectorAll('input, textarea, select');
        
        // Cargar datos guardados
        const savedData = Storage.get(`autosave_${formId}`);
        if (savedData) {
            Object.keys(savedData).forEach(name => {
                const input = form.querySelector(`[name="${name}"]`);
                if (input) {
                    input.value = savedData[name];
                }
            });
        }
        
        // Guardar cambios
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                const data = {};
                inputs.forEach(inp => {
                    if (inp.name) {
                        data[inp.name] = inp.value;
                    }
                });
                Storage.set(`autosave_${formId}`, data, 86400); // 24 horas
            });
        });
    });
}

function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+S para guardar
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            const saveBtn = document.querySelector('[data-save]');
            if (saveBtn) saveBtn.click();
        }
        
        // Ctrl+Enter para enviar formulario
        if (e.ctrlKey && e.key === 'Enter') {
            const submitBtn = document.querySelector('[type="submit"]');
            if (submitBtn) submitBtn.click();
        }
        
        // Escape para cerrar modales
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal.show');
            if (modal) {
                const closeBtn = modal.querySelector('.btn-close');
                if (closeBtn) closeBtn.click();
            }
        }
    });
}

function initThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) return;
    
    const savedTheme = Storage.get('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        Storage.set('theme', newTheme);
        
        Notifications.toast(`Tema cambiado a ${newTheme}`, 'info');
    });
}

function initAnimations() {
    // Scroll reveal
    window.addEventListener('scroll', Animations.scrollReveal);
    Animations.scrollReveal();
    
    // Ripple effect en botones
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', Animations.ripple);
    });
}

// ============================================
// FUNCIONES DE USUARIO
// ============================================

function loadUserPreferences() {
    const prefs = Storage.loadUserPreferences();
    
    // Aplicar preferencias guardadas
    if (prefs.theme) {
        document.documentElement.setAttribute('data-theme', prefs.theme);
    }
    
    if (prefs.language) {
        changeLanguage(prefs.language);
    }
}

function changeLanguage(lang) {
    Storage.set('language', lang);
    
    // Disparar evento para que otros componentes reaccionen
    const event = new CustomEvent('languageChanged', { detail: { language: lang } });
    document.dispatchEvent(event);
    
    Notifications.toast(`Idioma cambiado a ${lang}`, 'success');
}

// ============================================
// FUNCIONES DE REDES SOCIALES
// ============================================

const Social = {
    // Compartir en Twitter
    tweet: function(text, url = window.location.href) {
        const tweetUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
        window.open(tweetUrl, '_blank', 'width=600,height=400');
    },
    
    // Compartir en Facebook
    facebook: function(url = window.location.href) {
        const fbUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
        window.open(fbUrl, '_blank', 'width=600,height=400');
    },
    
    // Compartir en LinkedIn
    linkedin: function(title, summary, url = window.location.href) {
        const liUrl = `https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}&summary=${encodeURIComponent(summary)}`;
        window.open(liUrl, '_blank', 'width=600,height=400');
    },
    
    // Compartir por WhatsApp
    whatsapp: function(text) {
        const waUrl = `https://wa.me/?text=${encodeURIComponent(text)}`;
        window.open(waUrl, '_blank');
    }
};

// ============================================
// FUNCIONES DE EXPORTACIÓN
// ============================================

const Export = {
    // Exportar a JSON
    toJSON: function(data, filename = 'datos.json') {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        
        URL.revokeObjectURL(url);
    },
    
    // Exportar a CSV
    toCSV: function(data, filename = 'datos.csv') {
        if (!data || !data.length) return;
        
        const headers = Object.keys(data[0]);
        const csv = [
            headers.join(','),
            ...data.map(row => headers.map(h => JSON.stringify(row[h])).join(','))
        ].join('\n');
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        
        URL.revokeObjectURL(url);
    },
    
    // Exportar a PDF (requiere librería externa)
    toPDF: function(elementId, filename = 'documento.pdf') {
        Notifications.toast('Funcionalidad PDF en desarrollo', 'info');
    }
};

// ============================================
// EXPORTAR FUNCIONES GLOBALES
// ============================================
window.Storage = Storage;
window.Notifications = Notifications;
window.FormValidator = FormValidator;
window.Formatter = Formatter;
window.Animations = Animations;
window.Social = Social;
window.Export = Export;

// ============================================
// ESTILOS PARA NOTIFICACIONES (añadidos dinámicamente)
// ============================================
const style = document.createElement('style');
style.textContent = `
    .toast-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        min-width: 300px;
        max-width: 400px;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        gap: 1rem;
        transform: translateX(120%);
        transition: transform 0.3s ease;
        z-index: 9999;
    }
    
    .toast-notification.show {
        transform: translateX(0);
    }
    
    .toast-success { border-left: 4px solid #2ecc71; }
    .toast-error { border-left: 4px solid #e74c3c; }
    .toast-warning { border-left: 4px solid #f1c40f; }
    .toast-info { border-left: 4px solid #3498db; }
    
    .toast-icon i { font-size: 1.5rem; }
    .toast-success .toast-icon i { color: #2ecc71; }
    .toast-error .toast-icon i { color: #e74c3c; }
    .toast-warning .toast-icon i { color: #f1c40f; }
    .toast-info .toast-icon i { color: #3498db; }
    
    .toast-content { flex: 1; }
    .toast-message { font-size: 0.95rem; }
    
    .toast-close {
        background: none;
        border: none;
        font-size: 1.2rem;
        cursor: pointer;
        color: #999;
        padding: 0;
    }
    
    .toast-close:hover { color: #333; }
    
    .ripple {
        position: absolute;
        background: rgba(255,255,255,0.5);
        border-radius: 50%;
        transform: scale(0);
        animation: ripple 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple {
        to { transform: scale(4); opacity: 0; }
    }
    
    .btn { position: relative; overflow: hidden; }
    
    [data-theme="dark"] {
        --bg-color: #1a1a1a;
        --text-color: #ffffff;
        --card-bg: #2d2d2d;
    }
    
    .confirm-modal {
        background: rgba(0,0,0,0.5);
    }
`;

document.head.appendChild(style);
