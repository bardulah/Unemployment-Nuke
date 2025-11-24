// Hunt Commander Chrome Extension - Content Script

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getJobInfo') {
    const jobInfo = extractJobInfo();
    sendResponse(jobInfo);
  } else if (request.action === 'autoFill') {
    const success = autoFillApplication();
    sendResponse({ success });
  }
  return true;
});

// Extract job information from page
function extractJobInfo() {
  let jobInfo = {
    title: null,
    company: null,
    location: null,
    salary: null
  };

  if (window.location.hostname.includes('profesia.sk')) {
    // Profesia.sk selectors
    jobInfo.title = document.querySelector('h1[itemprop="title"]')?.textContent.trim() ||
                    document.querySelector('.job-title')?.textContent.trim();

    jobInfo.company = document.querySelector('[itemprop="hiringOrganization"]')?.textContent.trim() ||
                      document.querySelector('.company-name')?.textContent.trim();

    jobInfo.location = document.querySelector('[itemprop="jobLocation"]')?.textContent.trim();

    jobInfo.salary = document.querySelector('[itemprop="baseSalary"]')?.textContent.trim() ||
                     document.querySelector('.salary')?.textContent.trim();

  } else if (window.location.hostname.includes('linkedin.com')) {
    // LinkedIn selectors
    jobInfo.title = document.querySelector('.job-details-jobs-unified-top-card__job-title')?.textContent.trim() ||
                    document.querySelector('h1')?.textContent.trim();

    jobInfo.company = document.querySelector('.job-details-jobs-unified-top-card__company-name')?.textContent.trim() ||
                      document.querySelector('.jobs-unified-top-card__company-name')?.textContent.trim();

    jobInfo.location = document.querySelector('.job-details-jobs-unified-top-card__bullet')?.textContent.trim();

    const salaryElement = document.querySelector('.job-details-jobs-unified-top-card__job-insight');
    if (salaryElement && salaryElement.textContent.includes('€')) {
      jobInfo.salary = salaryElement.textContent.trim();
    }
  }

  return jobInfo;
}

// Auto-fill application form
function autoFillApplication() {
  // Get stored user data
  chrome.storage.sync.get(['userData'], (result) => {
    if (!result.userData) return false;

    const userData = result.userData;

    // Try to fill common form fields
    fillField('name', userData.name);
    fillField('email', userData.email);
    fillField('phone', userData.phone);
    fillField('message', generateCoverLetter(userData));
  });

  return true;
}

// Fill form field
function fillField(fieldName, value) {
  if (!value) return;

  // Try multiple selector strategies
  const selectors = [
    `input[name="${fieldName}"]`,
    `input[name*="${fieldName}"]`,
    `input[id*="${fieldName}"]`,
    `input[placeholder*="${fieldName}"]`,
    `textarea[name="${fieldName}"]`,
    `textarea[name*="${fieldName}"]`
  ];

  for (const selector of selectors) {
    const field = document.querySelector(selector);
    if (field) {
      field.value = value;
      // Trigger events to ensure validation
      field.dispatchEvent(new Event('input', { bubbles: true }));
      field.dispatchEvent(new Event('change', { bubbles: true }));
      break;
    }
  }
}

// Generate quick cover letter
function generateCoverLetter(userData) {
  const jobInfo = extractJobInfo();

  return `Dear Hiring Manager,

I am writing to express my interest in the ${jobInfo.title || 'position'} at ${jobInfo.company || 'your company'}. With my experience in Python development and passion for building scalable solutions, I believe I would be a valuable addition to your team.

I am excited about this opportunity and would welcome the chance to discuss how my skills align with your needs.

Best regards,
${userData.name}`;
}

// Add floating button to job pages
function addQuickTrackButton() {
  const button = document.createElement('button');
  button.innerHTML = '🎯 Track in Hunt Commander';
  button.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 10000;
    padding: 12px 20px;
    background: #10b981;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    font-size: 14px;
  `;

  button.addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'openPopup' });
  });

  document.body.appendChild(button);
}

// Initialize on job pages
if (window.location.hostname.includes('profesia.sk') ||
    window.location.hostname.includes('linkedin.com/jobs')) {
  addQuickTrackButton();
}
