function showModal(message) {
    const copyButton = document.getElementById('copy-button');
    copyButton.dataset.text = message;
    document.getElementById('modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

function copyToClipboard() {
    const button = document.getElementById('copy-button');
    const text = button.dataset.text;

    navigator.clipboard.writeText(text).then(() => {
        const message = document.getElementById('copy-message');
        message.style.display = 'block';

        setTimeout(() => {
            message.style.display = 'none';
        }, 1000);
    }).catch(err => {
        console.error('Ошибка при копировании текста: ', err);
    });
}

function createWord(crmId) {
    fetch(`/generate_word/${crmId}`)
        .then(response => response.json())
        .then(data => showModal(data.word))
        .catch(error => console.error('Ошибка:', error));
}

function openEditModal(crmId) {
    document.getElementById('crmId').value = crmId;
    document.getElementById('editModal').style.display = 'block';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
    window.location.href = '/Dashboard_branches';
}

document.getElementById('editForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const timeValue = document.getElementById('timeSelect').value;
    const crmId = document.getElementById('crmId').value;

    // Выводим значение timeValue в консоль
    console.log("Selected time value:", timeValue);
    console.log("CRM ID:", crmId);

    fetch('/update_time', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            crm_id: crmId,
            time_send: timeValue
        }),
    })
    .then(response => response.json())
    .then(data => {
        closeEditModal();
    })
    .catch(error => console.error('Ошибка:', error));
});
    function openHelpModal() {
        document.getElementById('helpModal').style.display = 'block';
    }

    function closeHelpModal() {
        document.getElementById('helpModal').style.display = 'none';
    }

    function openPhoneModal(crmId) {
        document.getElementById('crmId').value = crmId;
        document.getElementById('phoneModal').style.display = 'block';
    }

    function closePhoneModal() {
        document.getElementById('phoneModal').style.display = 'none';
        window.location.href = '/Dashboard_branches';
    }

    document.getElementById('phoneForm').addEventListener('submit', function(event) {
        event.preventDefault();

        const crmId = document.getElementById('crmId').value;
        const phone = document.getElementById('phone').value;

        fetch('/connect_whatsapp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                crm_id: crmId,
                phone: phone
            }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('authMessage').style.display = 'block';
        })
        .catch(error => console.error('Ошибка:', error));
    });

        function openDeactivateModal(crmId) {
    document.getElementById('deactivateCrmId').value = crmId;
    document.getElementById('deactivateModal').style.display = 'block';
}

function closeDeactivateModal() {
    document.getElementById('deactivateModal').style.display = 'none';
}

document.getElementById('deactivateForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const crmId = document.getElementById('deactivateCrmId').value;

    fetch('/disconnect_whatsapp', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            crm_id: crmId
        }),
    })
    .then(response => response.json())
    .then(data => {
        closeDeactivateModal();
        // Вы можете добавить дополнительную логику здесь, если необходимо
    })
    .catch(error => console.error('Ошибка:', error));
});

function openLinkRequestModal() {
    document.getElementById("linkRequestModal").style.display = "block";
}

function closeLinkRequestModal() {
    document.getElementById("linkRequestModal").style.display = "none";
}