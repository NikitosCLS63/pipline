// === СОХРАНЯЕМ ТОКЕН И CUSTOMER_ID В COOKIES ДЛЯ ПЕРЕДАЧИ ПРИ НАВИГАЦИИ ===
// Когда токен изменяется в localStorage, сохраняем его в cookies

function updateTokenCookie() {
  const token = localStorage.getItem('access_token');
  
  if (token) {
    // Сохраняем токен в cookie с длительностью жизни (4 недели)
    // 4 weeks = 28 days = 2419200 seconds
    document.cookie = `access_token=${token}; path=/; max-age=2419200; SameSite=Lax`;
    console.log('✅ Токен сохранён в cookie');
    
    // Извлекаем и сохраняем customer_id из токена
    try {
      const parts = token.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        // token uses `customer_id` claim (see SIMPLE_JWT USER_ID_CLAIM)
        const customerId = payload.customer_id || payload.user_id;
        if (customerId) {
          document.cookie = `customer_id=${customerId}; path=/; max-age=2419200; SameSite=Lax`;
          console.log('✅ Customer ID сохранён в cookie:', customerId);
        }
      }
    } catch (e) {
      console.warn('⚠️ Не удалось извлечь customer_id из токена');
    }
  } else {
    // Сохраняем токен в cookie с длительностью жизни (4 недели)
    // 4 weeks = 28 days = 2419200 seconds
    document.cookie = `access_token=${token}; path=/; max-age=2419200; SameSite=Lax`;
    document.cookie = 'customer_id=; path=/; max-age=0';
    console.log('🗑️ Токены удалены из cookie');
  }
}

// Проверяем токен при загрузке страницы
updateTokenCookie();


// === ДОБАВЛЯЕМ ТОКЕН КО ВСЕМ FETCH ЗАПРОСАМ ===
const originalFetch = window.fetch;

window.fetch = function(...args) {
  const token = localStorage.getItem('access_token');
  
  if (token) {
    if (!args[1]) args[1] = {};
    if (!args[1].headers) args[1].headers = {};
    args[1].headers['Authorization'] = 'Bearer ' + token;
  }
  
  return originalFetch.apply(this, args);
};

// --- Silent token refresh on load ---
async function attemptTokenRefresh() {
  try {
    const access = localStorage.getItem('access_token');
    const refresh = localStorage.getItem('refresh_token');
    // If we already have an access token, nothing to do
    if (access) return;
    if (!refresh) return;

    console.log('[AUTH] Attempting silent token refresh...');
    const res = await fetch('/api/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh })
    });

    if (!res.ok) {
      console.warn('[AUTH] Refresh failed, clearing tokens');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      updateTokenCookie();
      return;
    }

    const data = await res.json();
    if (data.access) {
      localStorage.setItem('access_token', data.access);
      // If server returned a new refresh token (rotation), update it
      if (data.refresh) localStorage.setItem('refresh_token', data.refresh);
      updateTokenCookie();
      console.log('[AUTH] Silent refresh succeeded');
    }
  } catch (e) {
    console.warn('[AUTH] Silent refresh error', e);
  }
}

// Try refresh immediately on script load
attemptTokenRefresh();

