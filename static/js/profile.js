// profile.js: handles user profile CRUD and UI

document.addEventListener('DOMContentLoaded', async function() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login/';
        return;
    }
    // Elements
    const infoDiv = document.getElementById('profile-info');
    const firstNameSpan = document.getElementById('profile-first-name');
    const lastNameSpan = document.getElementById('profile-last-name');
    const emailSpan = document.getElementById('profile-email');
    const phoneSpan = document.getElementById('profile-phone');
    const editBtn = document.getElementById('edit-profile-btn');
    const deleteBtn = document.getElementById('delete-profile-btn');
    const logoutBtn = document.getElementById('logout-profile-btn');
    const form = document.getElementById('profile-form');
    const messageDiv = document.getElementById('profile-message');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');

    // Form fields
    const editFirstName = document.getElementById('edit-first-name');
    const editLastName = document.getElementById('edit-last-name');
    const editEmail = document.getElementById('edit-email');
    const editPhone = document.getElementById('edit-phone');

    let userData = {};

    async function loadProfile() {
        try {
            const res = await fetch('/api/users/me/', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!res.ok) throw new Error('Ошибка загрузки профиля');
            userData = await res.json();
            firstNameSpan.textContent = userData.first_name || '';
            lastNameSpan.textContent = userData.last_name || '';
            emailSpan.textContent = userData.email || '';
            phoneSpan.textContent = userData.phone || '';
            editFirstName.value = userData.first_name || '';
            editLastName.value = userData.last_name || '';
            editEmail.value = userData.email || '';
            editPhone.value = userData.phone || '';
        } catch (e) {
            messageDiv.textContent = 'Ошибка загрузки профиля';
        }
    }

    editBtn.onclick = function() {
        infoDiv.style.display = 'none';
        form.style.display = 'block';
        messageDiv.textContent = '';
    };
    cancelEditBtn.onclick = function() {
        form.style.display = 'none';
        infoDiv.style.display = 'block';
        messageDiv.textContent = '';
    };
    form.onsubmit = async function(e) {
        e.preventDefault();
        const data = {
            first_name: editFirstName.value.trim(),
            last_name: editLastName.value.trim(),
            email: editEmail.value.trim(),
            phone: editPhone.value.trim()
        };
        try {
            const res = await fetch('/api/users/me/', {
                method: 'PUT',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error('Ошибка сохранения');
            messageDiv.textContent = 'Профиль обновлен';
            form.style.display = 'none';
            infoDiv.style.display = 'block';
            await loadProfile();
        } catch (e) {
            messageDiv.textContent = 'Ошибка сохранения';
        }
    };
    deleteBtn.onclick = async function() {
        if (!confirm('Удалить аккаунт? Это действие необратимо!')) return;
        try {
            const res = await fetch('/api/users/me/', {
                method: 'DELETE',
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!res.ok) throw new Error('Ошибка удаления');
            localStorage.clear();
            window.location.href = '/register/';
        } catch (e) {
            messageDiv.textContent = 'Ошибка удаления';
        }
    };
    logoutBtn.onclick = function() {
        localStorage.clear();
        window.location.href = '/login/';
    };
    await loadProfile();
});
