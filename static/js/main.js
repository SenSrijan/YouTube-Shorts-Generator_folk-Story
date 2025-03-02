/**
 * Main JavaScript for YouTube Shorts Generator
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-button');
    if (copyButtons.length > 0) {
        copyButtons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-copy-target');
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    // Create a temporary textarea
                    const textarea = document.createElement('textarea');
                    textarea.value = targetElement.textContent;
                    document.body.appendChild(textarea);
                    
                    // Select and copy
                    textarea.select();
                    document.execCommand('copy');
                    
                    // Clean up
                    document.body.removeChild(textarea);
                    
                    // Update button text temporarily
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="bi bi-check"></i> Copied!';
                    
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 2000);
                }
            });
        });
    }
    
    // Handle form submissions with loading states
    const forms = document.querySelectorAll('form[data-loading]');
    if (forms.length > 0) {
        forms.forEach(form => {
            form.addEventListener('submit', function() {
                const submitButton = this.querySelector('button[type="submit"]');
                if (submitButton) {
                    const originalContent = submitButton.innerHTML;
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                    
                    // Store original content for restoration after form submission
                    submitButton.setAttribute('data-original-content', originalContent);
                }
            });
        });
    }
    
    // Confirm actions (like deletion)
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    if (confirmButtons.length > 0) {
        confirmButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                const message = this.getAttribute('data-confirm') || 'Are you sure?';
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }
    
    // Country input with auto-suggestion
    const countryInput = document.getElementById('country-input');
    if (countryInput) {
        // List of countries for auto-suggestion
        const countries = [
            "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", 
            "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", 
            "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde", 
            "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", 
            "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic", 
            "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", 
            "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", 
            "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", 
            "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Korea, North", "Korea, South", "Kosovo", "Kuwait", 
            "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", 
            "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", 
            "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", 
            "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Macedonia", "Norway", "Oman", "Pakistan", 
            "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", 
            "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", 
            "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", 
            "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Sudan", "Spain", "Sri Lanka", "Sudan", 
            "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", 
            "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", 
            "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen", 
            "Zambia", "Zimbabwe"
        ];
        
        // Create datalist for auto-suggestions
        const datalist = document.createElement('datalist');
        datalist.id = 'country-suggestions';
        
        countries.forEach(country => {
            const option = document.createElement('option');
            option.value = country;
            datalist.appendChild(option);
        });
        
        document.body.appendChild(datalist);
        countryInput.setAttribute('list', 'country-suggestions');
    }
    
    // Generation form handling
    const generationForm = document.getElementById('generation-form');
    if (generationForm) {
        generationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const countryInput = document.getElementById('country-input');
            const resultContainer = document.getElementById('result-container');
            const loadingSpinner = document.getElementById('loading-spinner');
            
            if (!countryInput.value.trim()) {
                alert('Please enter a country name');
                countryInput.focus();
                return;
            }
            
            // Show loading spinner
            resultContainer.classList.add('d-none');
            loadingSpinner.classList.remove('d-none');
            
            // Disable form
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            
            // Prepare data for submission
            const data = {
                country: countryInput.value.trim()
            };
            
            // Make API request
            fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading spinner
                loadingSpinner.classList.add('d-none');
                
                if (data.error) {
                    // Show error
                    alert('Error: ' + data.error);
                } else {
                    // Show results
                    resultContainer.classList.remove('d-none');
                    
                    // Update result content
                    document.getElementById('story-preview').textContent = data.preview.story_preview;
                    document.getElementById('voiceover-preview').textContent = data.preview.voiceover_preview;
                    document.getElementById('scenes-preview').textContent = data.preview.scenes_preview;
                    
                    // Update download links
                    const downloadContainer = document.getElementById('download-container');
                    if (downloadContainer) {
                        downloadContainer.classList.remove('d-none');
                        
                        // Update download links with the correct paths
                        document.getElementById('download-story').href = data.paths.story_path;
                        document.getElementById('download-voiceover').href = data.paths.voiceover_path;
                        document.getElementById('download-audio').href = data.paths.voiceover_tts_path;
                        document.getElementById('download-scenes').href = data.paths.scenes_path;
                        document.getElementById('view-generation').href = '/view/' + data.generation_id;
                    }
                }
                
                // Re-enable form
                submitButton.disabled = false;
            })
            .catch(error => {
                // Hide loading spinner
                loadingSpinner.classList.add('d-none');
                
                // Show error
                alert('Error: ' + error.message);
                
                // Re-enable form
                submitButton.disabled = false;
            });
        });
    }
    
    // Handle API key visibility toggle
    const apiKeyToggles = document.querySelectorAll('.api-key-toggle');
    if (apiKeyToggles.length > 0) {
        apiKeyToggles.forEach(toggle => {
            toggle.addEventListener('click', function() {
                const keyElement = document.getElementById(this.getAttribute('data-key-id'));
                if (keyElement) {
                    if (keyElement.getAttribute('type') === 'password') {
                        keyElement.setAttribute('type', 'text');
                        this.innerHTML = '<i class="bi bi-eye-slash"></i>';
                    } else {
                        keyElement.setAttribute('type', 'password');
                        this.innerHTML = '<i class="bi bi-eye"></i>';
                    }
                }
            });
        });
    }
    
    // Initialize charts if any are present on the page
    initializeCharts();
});

// Function to initialize charts (if present)
function initializeCharts() {
    // Monthly generations chart
    const monthlyChartElement = document.getElementById('monthly-generations-chart');
    if (monthlyChartElement) {
        // Get data from data attributes
        const labels = JSON.parse(monthlyChartElement.getAttribute('data-labels'));
        const values = JSON.parse(monthlyChartElement.getAttribute('data-values'));
        
        // Create chart context
        const ctx = monthlyChartElement.getContext('2d');
        
        // Create chart
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Generations',
                    data: values,
                    backgroundColor: 'rgba(90, 103, 216, 0.2)',
                    borderColor: 'rgba(90, 103, 216, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointBackgroundColor: 'rgba(90, 103, 216, 1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    // Countries chart
    const countriesChartElement = document.getElementById('countries-chart');
    if (countriesChartElement) {
        // Get data from data attributes
        const labels = JSON.parse(countriesChartElement.getAttribute('data-labels'));
        const values = JSON.parse(countriesChartElement.getAttribute('data-values'));
        
        // Create chart context
        const ctx = countriesChartElement.getContext('2d');
        
        // Create chart
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Generations',
                    data: values,
                    backgroundColor: 'rgba(56, 178, 172, 0.7)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
}

// Stripe checkout handling
function handleCheckout(planId) {
    const button = document.getElementById(`checkout-${planId}`);
    
    if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Redirecting...';
        
        // Redirect to checkout
        window.location.href = `/subscription/checkout/${planId}`;
    }
}

// Function to display a toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    
    // Create toast container if it doesn't exist
    if (!toastContainer) {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast show bg-${type === 'error' ? 'danger' : type} text-white`;
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.ariaAtomic = 'true';
    
    // Toast content
    toast.innerHTML = `
        <div class="toast-header bg-${type === 'error' ? 'danger' : type} text-white">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Add to container
    document.querySelector('.toast-container').appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
    
    // Add click listener to close button
    toast.querySelector('.btn-close').addEventListener('click', function() {
        toast.remove();
    });
}