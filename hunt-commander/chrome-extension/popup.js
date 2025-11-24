// Hunt Commander Chrome Extension - Popup Script

// Load saved configuration
document.addEventListener('DOMContentLoaded', async () => {
  const config = await chrome.storage.sync.get(['apiUrl', 'authToken']);

  if (config.apiUrl) {
    document.getElementById('apiUrl').value = config.apiUrl;
  }
  if (config.authToken) {
    document.getElementById('authToken').value = config.authToken;
  }

  // Check if we're on a job page
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab.url.includes('profesia.sk') || tab.url.includes('linkedin.com/jobs')) {
    // Try to detect job info
    chrome.tabs.sendMessage(tab.id, { action: 'getJobInfo' }, (response) => {
      if (response && response.title) {
        document.getElementById('jobDetected').style.display = 'block';
        document.getElementById('detectedTitle').textContent = response.title;
        document.getElementById('detectedCompany').textContent = response.company;
        document.getElementById('autoFill').disabled = false;
      }
    });
  }
});

// Save configuration
document.getElementById('saveConfig').addEventListener('click', async () => {
  const apiUrl = document.getElementById('apiUrl').value;
  const authToken = document.getElementById('authToken').value;

  await chrome.storage.sync.set({ apiUrl, authToken });

  showStatus('Configuration saved!', 'success');
});

// Auto-fill application
document.getElementById('autoFill').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.tabs.sendMessage(tab.id, { action: 'autoFill' }, (response) => {
    if (response && response.success) {
      showStatus('Form auto-filled!', 'success');
    } else {
      showStatus('Auto-fill failed', 'error');
    }
  });
});

// Track job
document.getElementById('trackJob').addEventListener('click', async () => {
  const config = await chrome.storage.sync.get(['apiUrl', 'authToken']);

  if (!config.apiUrl || !config.authToken) {
    showStatus('Please configure API settings first', 'error');
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.tabs.sendMessage(tab.id, { action: 'getJobInfo' }, async (response) => {
    if (!response || !response.title) {
      showStatus('Could not detect job info', 'error');
      return;
    }

    try {
      const apiResponse = await fetch(`${config.apiUrl}/applications`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${config.authToken}`
        },
        body: JSON.stringify({
          job_title: response.title,
          company: response.company,
          location: response.location || 'Unknown',
          salary_range: response.salary,
          job_url: tab.url,
          status: 'interested'
        })
      });

      if (apiResponse.ok) {
        showStatus('Job tracked successfully! 🎯', 'success');
      } else {
        showStatus('Failed to track job', 'error');
      }
    } catch (error) {
      showStatus('Error: ' + error.message, 'error');
    }
  });
});

function showStatus(message, type) {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;

  setTimeout(() => {
    statusDiv.style.display = 'none';
  }, 3000);
}
