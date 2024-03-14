document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector('form');

    form.addEventListener('submit', function(event) {
        event.preventDefault();

        // get all validation error messages elements
        const errorMessages = document.querySelectorAll('.validation-error');
        // remove all validation error messages
        errorMessages.forEach(msg => msg.remove());

        let errors = [];

        let firstname = document.getElementById('firstname').value.trim();
        if (!firstname) {
            errors.push({ field: 'firstname', message: 'First name is required' });
        }

        let lastname = document.getElementById('lastname').value.trim();
        if (!lastname) {
            errors.push({ field: 'lastname', message: 'Last name is required' });
        }

        let username = document.getElementById('username').value.trim();
        if (!username) {
            errors.push({ field: 'username', message: 'Username is required' });
        }
        // exist
        let password = document.getElementById('password').value;
        if (!password) {
            errors.push({ field: 'password', message: 'Password is required' });
            // min length
        } else if (password.length < 6) {
            errors.push({ field: 'password', message: 'Password must be at least 6 characters long' });
        }

        let repeatpassword = document.getElementById('repeatpassword').value;
        if (!repeatpassword) {
            errors.push({ field: 'repeatpassword', message: 'Repeat password is required' });
        } else if (password !== repeatpassword) {
            errors.push({ field: 'repeatpassword', message: 'Passwords do not match' });
        }

        // add errors all errors to elements
        errors.forEach(error => {
            const inputField = document.getElementById(error.field);
            const errorMessage = document.createElement('div');
            errorMessage.classList.add('validation-error');
            errorMessage.textContent = error.message;
            inputField.parentNode.appendChild(errorMessage);

            setTimeout(() => {
                errorMessage.classList.add('show');
            }, 50);
        });

        // remove errors when the user corrects the input
        const inputFields = document.querySelectorAll('.form-control');
        inputFields.forEach(input => {
            input.addEventListener('input', function() {
                const errorMessage = input.parentNode.querySelector('.validation-error');
                if (errorMessage) {
                    errorMessage.remove();
                }
            });
        });
        // submit if no errors
        if (errors.length === 0) {
            form.submit();
        }
    });
});
