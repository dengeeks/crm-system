// Список всех модальных окон
const modals = ['generalTooltip', 'modal1', 'modal2', 'modal3', 'modal4', 'modal5', 'modal6'];

function showModal(id) {
    modals.forEach(modal => {
        document.getElementById(modal).style.display = (modal === id) ? 'block' : 'none';
    });
}

function hideTooltip(id) {
    document.getElementById(id).style.display = 'none';
}

function showTooltip(id) {
    showModal(id);
}

// Функция загрузки сообщений по филиалу
function loadMessages(crmId) {
    const messageBlocks = document.getElementById('message_blocks');
    const sendTypeSelect = document.getElementById('send_type');
    messageBlocks.style.display = 'flex'; // Показываем блоки с сообщениями

    // Отправка запроса на получение сообщений по ID филиала
    fetch(`/get_messages/${crmId}`)
        .then(response => response.json())
        .then(data => {
            // Заполнение textarea с сообщениями
            document.getElementById('message1').value = data.message1 || '';
            document.getElementById('message2').value = data.message2 || '';
            document.getElementById('message3').value = data.message3 || '';

            // Установка выбранного типа отправки
            if (data.type_send) {
                sendTypeSelect.value = data.type_send;
            } else {
                sendTypeSelect.value = ''; // Если нет значения, очищаем выбор
            }
        });
}

function navigateModal(currentId, direction) {
    const currentIndex = modals.indexOf(currentId);
    let newIndex = currentIndex + direction;

    if (newIndex < 0) newIndex = modals.length - 1;
    if (newIndex >= modals.length) newIndex = 0;

    showModal(modals[newIndex]);
}

// Изначально скрываем все модальные окна при загрузке страницы
window.onload = function() {
    modals.forEach(modal => {
        document.getElementById(modal).style.display = 'none';
    });
};

// Обработчики событий для стрелочек
document.querySelectorAll('.nav-arrow.prev').forEach(arrow => {
    arrow.addEventListener('click', function() {
        navigateModal(this.closest('.modal-message').id, -1);
    });
});

document.querySelectorAll('.nav-arrow.next').forEach(arrow => {
    arrow.addEventListener('click', function() {
        navigateModal(this.closest('.modal-message').id, 1);
    });
});
