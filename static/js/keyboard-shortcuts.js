// Глобальные горячие клавиши
(function() {
    'use strict';
    
    let gKeyPressed = false;
    let lastKeyTime = 0;
    const KEY_TIMEOUT = 1000; // 1 секунда для комбинации G+X
    
    document.addEventListener('keydown', function(e) {
        const key = e.key.toLowerCase();
        const isInput = e.target.tagName === 'INPUT' || 
                       e.target.tagName === 'TEXTAREA' || 
                       e.target.isContentEditable;
        
        // G + K - Корзина
        // G + C - Каталог
        // G + P - Админ-панель (только для админов)
        if (key === 'g' && !isInput) {
            gKeyPressed = true;
            lastKeyTime = Date.now();
            return;
        }
        
        if (gKeyPressed && !isInput) {
            const timeSinceG = Date.now() - lastKeyTime;
            if (timeSinceG < KEY_TIMEOUT) {
                if (key === 'k') {
                    e.preventDefault();
                    window.location.href = '/cart/';
                } else if (key === 'c') {
                    e.preventDefault();
                    window.location.href = '/catalog/';
                } else if (key === 'p') {
                    // Проверяем, является ли пользователь админом
                    const adminLink = document.getElementById('admin-link');
                    if (adminLink && adminLink.style.display !== 'none') {
                        e.preventDefault();
                        window.location.href = '/admin-panel/';
                    }
                }
            }
            gKeyPressed = false;
        } else if (key !== 'g') {
            gKeyPressed = false;
        }
    });
    
    document.addEventListener('keyup', function(e) {
        if (e.key.toLowerCase() === 'g') {
            setTimeout(() => {
                if (Date.now() - lastKeyTime > KEY_TIMEOUT) {
                    gKeyPressed = false;
                }
            }, KEY_TIMEOUT);
        }
    });
})();

