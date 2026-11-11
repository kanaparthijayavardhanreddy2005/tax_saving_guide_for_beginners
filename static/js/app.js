/**
 * TaxWise AI - Frontend Application Controller
 * Connects UI views, 8-step wizard, Chart.js visualizations, RAG assistant chat,
 * personalized recommendations, and Explainable AI transparent modals.
 */

// Global Application State
const AppState = {
    currentView: 'landing',
    wizardStep: 1,
    financialYear: 'FY 2025-26',
    currentUser: null,
    calculationResult: null,
    recommendations: [],
    educationTopics: [],
    taxDocuments: [],
    chatHistory: [],
    chartInstance: null
};

// =============================================================================
// Initialization
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    checkCurrentUser();
    loadEducationContent();
    loadTaxDocuments();
    recalculateAll();
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeMobileNav();
    });
});

// =============================================================================
// Navigation & View Routing (Specification Section 21)
// =============================================================================
function navigateTo(viewName) {
    AppState.currentView = viewName;

    document.querySelectorAll('#main-nav [data-view]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // Update view visibility
    document.querySelectorAll('.app-view').forEach(view => {
        view.classList.remove('active');
    });

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) {
        targetView.classList.add('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (viewName === 'dashboard') {
        renderDashboardChart();
    }
    if (viewName === 'admin') {
        loadAdminData();
    }

    closeMobileNav(false);
}

function toggleMobileNav() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    const toggle = document.getElementById('mobile-nav-toggle');
    if (!sidebar || !toggle) return;
    const isOpen = sidebar.classList.toggle('is-open');
    backdrop?.classList.toggle('is-open', isOpen);
    document.body.classList.toggle('sidebar-open', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
    toggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
}

function closeMobileNav(returnFocus = true) {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    const toggle = document.getElementById('mobile-nav-toggle');
    if (!sidebar) return;
    const wasOpen = sidebar.classList.contains('is-open');
    sidebar.classList.remove('is-open');
    backdrop?.classList.remove('is-open');
    document.body.classList.remove('sidebar-open');
    toggle?.setAttribute('aria-expanded', 'false');
    toggle?.setAttribute('aria-label', 'Open navigation');
    if (wasOpen && returnFocus) toggle?.focus();
}

function navigateToSection(viewName, selector) {
    navigateTo(viewName);
    window.setTimeout(() => document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth' }), 40);
}

function onFinancialYearChange(selectedFY) {
    AppState.financialYear = selectedFY;
    recalculateAll();
    if (AppState.currentView === 'admin') loadAdminData();
}

// =============================================================================
// Tax Calculator 8-Step Wizard Controller (Specification Section 22)
// =============================================================================
function jumpToStep(step) {
    if (step < 1 || step > 8) return;
    AppState.wizardStep = step;

    // Update wizard steppers
    for (let i = 1; i <= 8; i++) {
        const navEl = document.getElementById(`step-nav-i`);
        const paneEl = document.getElementById(`wizard-step-${i}`);
        
        const navItem = document.getElementById(`step-nav-${i}`);
        if (navItem) {
            navItem.classList.remove('active', 'completed');
            if (i === step) navItem.classList.add('active');
            else if (i < step) navItem.classList.add('completed');
        }

        if (paneEl) {
            paneEl.classList.remove('active');
            if (i === step) paneEl.classList.add('active');
        }
    }

    // Update Prev / Next buttons
    const prevBtn = document.getElementById('wiz-prev-btn');
    const nextBtn = document.getElementById('wiz-next-btn');
    const countLabel = document.getElementById('step-count-text');

    if (prevBtn) prevBtn.disabled = (step === 1);
    if (nextBtn) {
        if (step === 7) nextBtn.textContent = 'View Recommendations (Step 8)';
        else if (step === 8) nextBtn.textContent = 'Go to Dashboard';
        else nextBtn.textContent = 'Next Step';
    }
    if (countLabel) countLabel.textContent = `Step ${step} of 8`;

    if (step === 7 || step === 8) {
        recalculateAll();
    }
}

function nextStep() {
    if (AppState.wizardStep === 8) {
        navigateTo('dashboard');
    } else {
        jumpToStep(AppState.wizardStep + 1);
    }
}

function prevStep() {
    if (AppState.wizardStep > 1) {
        jumpToStep(AppState.wizardStep - 1);
    }
}

function setWizSalary(amount) {
    const salaryInput = document.getElementById('wiz-salary');
    if (salaryInput) salaryInput.value = amount;

    // Update chip styling
    document.querySelectorAll('.quick-chips .chip').forEach(chip => {
        chip.classList.toggle('active', chip.textContent.includes(amount / 100000 + 'L'));
    });

    recalculateAll();
}

function resetCalculatorForm() {
    document.getElementById('wiz-age').value = 28;
    document.getElementById('wiz-employment').value = 'salaried';
    document.getElementById('wiz-salary').value = 1200000;
    document.getElementById('wiz-business').value = 0;
    document.getElementById('wiz-interest').value = 0;
    document.getElementById('wiz-rental').value = 0;
    document.getElementById('wiz-80c').value = 150000;
    document.getElementById('wiz-nps').value = 50000;
    document.getElementById('wiz-80d').value = 25000;
    document.getElementById('wiz-parents-senior').value = 'unknown';
    document.getElementById('wiz-homeloan').value = 0;
    document.getElementById('wiz-eduloan').value = 0;
    document.getElementById('wiz-hra').value = 0;
    document.getElementById('wiz-donations').value = 0;
    jumpToStep(1);
    recalculateAll();
}

// =============================================================================
// Tax Calculation & Deterministic API Integration
// =============================================================================
function collectFormData() {
    const grossSalary = parseFloat(document.getElementById('wiz-salary')?.value) || 0;
    const businessInc = parseFloat(document.getElementById('wiz-business')?.value) || 0;
    const interestInc = parseFloat(document.getElementById('wiz-interest')?.value) || 0;
    const rentalInc = parseFloat(document.getElementById('wiz-rental')?.value) || 0;
    const totalGross = grossSalary + businessInc + interestInc + rentalInc;

    const employmentType = document.getElementById('wiz-employment')?.value || 'salaried';
    const isSalaried = (employmentType === 'salaried');
    const regime = document.getElementById('wiz-regime')?.value || 'new';

    const sec80c = parseFloat(document.getElementById('wiz-80c')?.value) || 0;
    const nps = parseFloat(document.getElementById('wiz-nps')?.value) || 0;
    const sec80d = parseFloat(document.getElementById('wiz-80d')?.value) || 0;
    const parentsSenior = document.getElementById('wiz-parents-senior')?.value;
    const homeLoan = parseFloat(document.getElementById('wiz-homeloan')?.value) || 0;
    const eduLoan = parseFloat(document.getElementById('wiz-eduloan')?.value) || 0;
    const rentPaid = parseFloat(document.getElementById('wiz-hra')?.value) || 0;
    const donations = parseFloat(document.getElementById('wiz-donations')?.value) || 0;

    return {
        gross_income: totalGross,
        is_salaried: isSalaried,
        regime: regime,
        financial_year: AppState.financialYear,
        age: parseInt(document.getElementById('wiz-age')?.value) || 28,
        is_resident: document.getElementById('wiz-residence')?.value !== 'nri',
        sec_80c: sec80c,
        sec_80ccd_1b: nps,
        sec_80d: sec80d,
        parents_senior: parentsSenior === 'unknown' ? null : (parentsSenior === 'yes'),
        home_loan_24b: homeLoan,
        education_loan_80e: eduLoan,
        rent_paid: rentPaid,
        hra_exemption: rentPaid,
        donations_80g: donations
    };
}

async function recalculateAll() {
    const payload = collectFormData();

    try {
        const response = await fetch('/api/tax/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const err = await response.json();
            console.error('Calculation error:', err);
            return;
        }

        const data = await response.json();
        AppState.calculationResult = data;
        AppState.recommendations = data.recommendations || [];

        updateDashboardUI(data);
        updateWizardResultsUI(data);
        updateComparisonUI(data.comparison);
        updateRecommendationsUI(AppState.recommendations);
    } catch (err) {
        console.error('Failed to calculate tax:', err);
    }
}

// =============================================================================
// UI Update Handlers
// =============================================================================
function formatINR(number) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(number);
}

function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[character]));
}

function updateDashboardUI(data) {
    const res = data.result;
    const comp = data.comparison;

    document.getElementById('dash-gross-income').textContent = formatINR(res.gross_income);
    document.getElementById('dash-total-deductions').textContent = formatINR(res.total_deductions);
    document.getElementById('dash-taxable-income').textContent = formatINR(res.taxable_income);
    document.getElementById('dash-estimated-tax').textContent = formatINR(res.total_tax);
    document.getElementById('dash-effective-rate').textContent = `${res.effective_rate}%`;

    const taxSub = document.getElementById('dash-tax-sub');
    if (res.total_tax === 0) {
        taxSub.textContent = 'Zero Tax via Section 87A Rebate! 🎉';
        taxSub.className = 'metric-sub text-success';
    } else {
        taxSub.textContent = `Includes 4% Cess (${formatINR(res.cess)})`;
        taxSub.className = 'metric-sub';
    }

    // Regime Decision Snapshot
    const diffBadge = document.getElementById('dash-lower-regime-badge');
    const diffAmount = document.getElementById('dash-diff-amount');
    const diffSummary = document.getElementById('dash-diff-summary');
    const neutralText = document.getElementById('dash-neutral-text');

    if (comp.tax_difference === 0) {
        diffBadge.textContent = 'Both Regimes Equal';
        diffBadge.className = 'badge badge-light';
        diffAmount.textContent = '₹0 Tax Difference';
    } else {
        const isNew = comp.lower_tax_regime === 'new';
        diffBadge.textContent = isNew ? 'New Regime Recommended' : 'Old Regime Recommended';
        diffBadge.className = 'badge badge-success';
        diffAmount.textContent = `${formatINR(comp.tax_difference)} Saved`;
    }

    diffSummary.textContent = comp.summary;
    neutralText.textContent = comp.neutral_disclaimer;

    renderDashboardChart();
}

function updateWizardResultsUI(data) {
    const res = data.result;

    document.getElementById('calc-res-gross').textContent = formatINR(res.gross_income);
    document.getElementById('calc-res-ded').textContent = formatINR(res.total_deductions);
    document.getElementById('calc-res-taxable').textContent = formatINR(res.taxable_income);
    document.getElementById('calc-res-tax').textContent = formatINR(res.total_tax);

    const tbody = document.getElementById('calc-slabs-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    res.slab_breakdown.forEach(slab => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${slab.slab}</strong></td>
            <td>${slab.rate}</td>
            <td>${formatINR(slab.taxable_amount)}</td>
            <td>${formatINR(slab.tax)}</td>
        `;
        tbody.appendChild(tr);
    });

    if (res.rebate_87a > 0) {
        const rebateRow = document.createElement('tr');
        rebateRow.innerHTML = `
            <td colspan="3" class="text-success font-bold">Section 87A Tax Rebate applied</td>
            <td class="text-success font-bold">-${formatINR(res.rebate_87a)}</td>
        `;
        tbody.appendChild(rebateRow);
    }
}

function updateComparisonUI(comp) {
    if (!comp) return;

    const oldR = comp.old_regime;
    const newR = comp.new_regime;

    document.getElementById('comp-old-gross').textContent = formatINR(oldR.gross_income);
    document.getElementById('comp-new-gross').textContent = formatINR(newR.gross_income);

    document.getElementById('comp-old-std').textContent = formatINR(oldR.standard_deduction);
    document.getElementById('comp-new-std').textContent = formatINR(newR.standard_deduction);

    const oldItemized = oldR.total_deductions - oldR.standard_deduction;
    document.getElementById('comp-old-itemized').textContent = formatINR(oldItemized);
    document.getElementById('comp-new-itemized').textContent = '₹0 (Not allowed)';

    document.getElementById('comp-old-total-ded').textContent = formatINR(oldR.total_deductions);
    document.getElementById('comp-new-total-ded').textContent = formatINR(newR.total_deductions);

    document.getElementById('comp-old-taxable').textContent = formatINR(oldR.taxable_income);
    document.getElementById('comp-new-taxable').textContent = formatINR(newR.taxable_income);

    document.getElementById('comp-old-base-tax').textContent = formatINR(oldR.base_tax);
    document.getElementById('comp-new-base-tax').textContent = formatINR(newR.base_tax);

    document.getElementById('comp-old-rebate').textContent = formatINR(oldR.rebate_87a);
    document.getElementById('comp-new-rebate').textContent = newR.rebate_87a > 0 ? `${formatINR(newR.rebate_87a)} (100% Rebate)` : '₹0';

    document.getElementById('comp-old-cess').textContent = formatINR(oldR.cess);
    document.getElementById('comp-new-cess').textContent = formatINR(newR.cess);

    document.getElementById('comp-old-total-tax').textContent = formatINR(oldR.total_tax);
    document.getElementById('comp-new-total-tax').textContent = formatINR(newR.total_tax);

    document.getElementById('comp-diff-tax').textContent = `${formatINR(comp.tax_difference)} Saved`;

    document.getElementById('comp-old-rate').textContent = `${oldR.effective_rate}%`;
    document.getElementById('comp-new-rate').textContent = `${newR.effective_rate}%`;

    const bannerTitle = document.getElementById('comp-summary-title');
    const bannerBadge = document.getElementById('comp-badge');
    const bannerDisclaimer = document.getElementById('comp-disclaimer-text');

    if (comp.lower_tax_regime === 'new') {
        bannerBadge.textContent = 'RECOMMENDED: NEW REGIME';
        bannerTitle.textContent = `You save ${formatINR(comp.tax_difference)} under the New Tax Regime`;
    } else {
        bannerBadge.textContent = 'RECOMMENDED: OLD REGIME';
        bannerTitle.textContent = `You save ${formatINR(comp.tax_difference)} under the Old Tax Regime`;
    }
    bannerDisclaimer.textContent = comp.neutral_disclaimer;
}

// =============================================================================
// Recommendations & Explainable AI Rendering (Specification Section 14, 15, 29)
// =============================================================================
function getStatusBadgeClass(status) {
    switch (status) {
        case 'Eligible': return 'eligible';
        case 'Potentially Eligible': return 'potentially-eligible';
        case 'Requires Additional Information': return 'needs-info';
        default: return 'not-applicable';
    }
}

function renderRecommendationCard(rec) {
    const badgeClass = getStatusBadgeClass(rec.status);
    const savingsText = rec.potential_savings > 0 ? `Potential Savings: <strong>${formatINR(rec.potential_savings)}</strong>` : '';

    return `
        <div class="rec-item-card" id="rec-card-${rec.id}">
            <div class="rec-main">
                <div class="rec-header-row">
                    <span class="status-badge ${badgeClass}">${rec.status}</span>
                    <h4 class="rec-title">${rec.title}</h4>
                </div>
                <p class="rec-why">${rec.why_suggested}</p>
                <div class="rec-impact-row">
                    ${savingsText}
                    <span class="text-subtle">Category: ${rec.category}</span>
                </div>
            </div>
            <div class="rec-actions">
                <button type="button" class="btn btn-outline btn-sm" onclick="openExplainableModal('${rec.id}')">
                    <span>Why am I seeing this?</span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </button>
            </div>
        </div>
    `;
}

function updateRecommendationsUI(recommendations) {
    const dashContainer = document.getElementById('dashboard-recs-container');
    const wizContainer = document.getElementById('wizard-recs-container');
    const fullContainer = document.getElementById('full-opportunities-list');

    const topThree = recommendations.slice(0, 3);
    const topThreeHtml = topThree.map(renderRecommendationCard).join('');
    const fullHtml = recommendations.map(renderRecommendationCard).join('');

    if (dashContainer) dashContainer.innerHTML = topThreeHtml;
    if (wizContainer) wizContainer.innerHTML = fullHtml;
    if (fullContainer) fullContainer.innerHTML = fullHtml;
}

function filterOpportunities(statusFilter) {
    document.querySelectorAll('.filter-bar .filter-chip').forEach(chip => {
        chip.classList.toggle('active', chip.textContent.toLowerCase().includes(statusFilter.toLowerCase()) || (statusFilter === 'all' && chip.textContent.includes('All')));
    });

    const fullContainer = document.getElementById('full-opportunities-list');
    if (!fullContainer) return;

    if (statusFilter === 'all') {
        fullContainer.innerHTML = AppState.recommendations.map(renderRecommendationCard).join('');
    } else {
        const filtered = AppState.recommendations.filter(r => r.status.toLowerCase() === statusFilter.toLowerCase());
        fullContainer.innerHTML = filtered.length ? filtered.map(renderRecommendationCard).join('') : '<p class="text-muted">No recommendations found in this category.</p>';
    }
}

function openExplainableModal(recId) {
    const rec = AppState.recommendations.find(r => r.id === recId);
    if (!rec || !rec.explanation) return;

    const x = rec.explanation;
    document.getElementById('xai-title').textContent = `${rec.title} - Transparency Breakdown`;

    const bodyEl = document.getElementById('xai-body');
    bodyEl.innerHTML = `
        <div class="xai-section">
            <h4 style="color: var(--primary); margin-bottom: 0.4rem;">🎯 Reason for Recommendation</h4>
            <p>${x.reason_for_recommendation}</p>
        </div>
        <hr style="margin: 1rem 0; border: none; border-top: 1px solid var(--border-color);">
        <div class="xai-section">
            <h4 style="margin-bottom: 0.4rem;">👤 User Profile Data Considered</h4>
            <ul style="margin-left: 1.25rem;">
                ${x.user_data_considered.map(d => `<li>${d}</li>`).join('')}
            </ul>
        </div>
        <hr style="margin: 1rem 0; border: none; border-top: 1px solid var(--border-color);">
        <div class="xai-section">
            <h4 style="margin-bottom: 0.4rem;">📜 Applicable Statutory Tax Rule</h4>
            <p><strong>${x.relevant_rule}</strong> (${x.financial_year})</p>
            <ul style="margin-left: 1.25rem; margin-top: 0.4rem;">
                ${x.eligibility_logic.map(c => `<li>${c}</li>`).join('')}
            </ul>
        </div>
        <hr style="margin: 1rem 0; border: none; border-top: 1px solid var(--border-color);">
        <div class="xai-section">
            <h4 style="color: var(--warning); margin-bottom: 0.4rem;">⚠️ Missing Information to Verify</h4>
            <ul style="margin-left: 1.25rem;">
                ${x.missing_information.map(m => `<li>${m}</li>`).join('')}
            </ul>
        </div>
        <hr style="margin: 1rem 0; border: none; border-top: 1px solid var(--border-color);">
        <div class="xai-section">
            <h4 style="margin-bottom: 0.4rem;">🏛️ Verified Legal Source</h4>
            <p style="font-size: 0.88rem; color: var(--text-muted);">${x.source}</p>
            <p style="font-size: 0.82rem; color: #92400E; margin-top: 0.4rem;"><em>${x.caution}</em></p>
        </div>
    `;

    openModal('explainable-modal');
}

// =============================================================================
// Chart.js Visualization (Specification Section 23)
// =============================================================================
function renderDashboardChart() {
    const canvas = document.getElementById('dashboardDonutChart');
    if (!canvas || !AppState.calculationResult) return;

    const res = AppState.calculationResult.result;
    const takeHome = Math.max(0, res.take_home);
    const tax = res.total_tax;
    const deductions = res.total_deductions;

    if (AppState.chartInstance) {
        AppState.chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');
    AppState.chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Take-Home Pay', 'Estimated Tax', 'Total Deductions'],
            datasets: [{
                data: [takeHome, tax, deductions],
                backgroundColor: ['#10B981', '#EF4444', '#3B82F6'],
                hoverOffset: 6,
                borderWidth: 2,
                borderColor: '#FFFFFF'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 600 },
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` ${ctx.label}: ${formatINR(ctx.raw)}`
                    }
                }
            },
            cutout: '68%'
        }
    });
}

// =============================================================================
// RAG AI Assistant Chat Controller (Specification Section 10, 13, 18)
// =============================================================================
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question) return;

    const beginnerMode = document.getElementById('chat-beginner-toggle').checked;
    const messagesContainer = document.getElementById('chat-messages-container');

    // Append User Message Bubble
    appendChatMessage('user', question);
    input.value = '';

    // Show AI Typing Indicator
    const typingIndicatorId = 'ai-typing-' + Date.now();
    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-msg ai-msg';
    typingBubble.id = typingIndicatorId;
    typingBubble.innerHTML = `
        <div class="msg-avatar">🤖</div>
        <div class="msg-content">
            <div class="msg-bubble">
                <span class="text-muted">Retrieving verified tax context and synthesizing answer...</span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(typingBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const payload = {
            question: question,
            user_context: collectFormData(),
            conversation_history: AppState.chatHistory,
            beginner_mode: beginnerMode,
            financial_year: AppState.financialYear
        };

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        const indicator = document.getElementById(typingIndicatorId);
        if (indicator) indicator.remove();

        if (response.ok) {
            appendChatMessage('ai', data.answer, data.sources, data.confidence);
            AppState.chatHistory.push({ question: question, answer: data.answer });
        } else {
            appendChatMessage('ai', `⚠️ ${data.error || 'Failed to retrieve response.'}`);
        }
    } catch (err) {
        const indicator = document.getElementById(typingIndicatorId);
        if (indicator) indicator.remove();
        appendChatMessage('ai', '⚠️ Connection error. Please verify your internet connection or local server.');
    }
}

function appendChatMessage(sender, text, sources = [], confidence = 'high') {
    const container = document.getElementById('chat-messages-container');
    if (!container) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${sender}-msg`;

    // Markdown converter for bold, headers, and bullet lists
    let formattedHtml = escapeHTML(text)
        .replace(/### (.*?)\n/g, '<h3 style="margin-top: 0.8rem; font-size: 1rem; color: var(--primary-dark);">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/- (.*?)\n/g, '<li style="margin-left: 1.25rem;">$1</li>');

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="msg-meta">
                <strong>Sources</strong>
                <ul class="citation-list">${sources.map(source => `
                    <li><a href="${escapeHTML(source.url || 'https://www.incometax.gov.in/iec/foportal/')}" target="_blank" rel="noopener noreferrer">${escapeHTML(source.title || source.section || 'Tax source')}</a>
                    <span>${escapeHTML(source.source || '')} · ${escapeHTML(source.financial_year || AppState.financialYear)} · p. ${escapeHTML(source.page || 'n/a')}</span></li>
                `).join('')}</ul>
                <span class="confidence-tag">${escapeHTML(confidence)} confidence</span>
            </div>
        `;
    }

    msgDiv.innerHTML = `
        <div class="msg-avatar">${sender === 'user' ? '👤' : '🤖'}</div>
        <div class="msg-content">
            <div class="msg-bubble">
                ${formattedHtml}
            </div>
            ${sourcesHtml}
        </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function askPreset(promptText) {
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = promptText;
        sendChatMessage();
    }
}

// =============================================================================
// Education Center & Document Explainer (Specification Section 16 & 17)
// =============================================================================
async function loadEducationContent() {
    try {
        const resp = await fetch('/api/education/topics');
        const data = await resp.json();
        AppState.educationTopics = data.topics || [];
        renderEducationCards(AppState.educationTopics);
    } catch (e) {
        console.error('Failed to load education topics:', e);
    }
}

function renderEducationCards(topics) {
    const container = document.getElementById('education-cards-container');
    if (!container) return;

    container.innerHTML = topics.map(t => `
        <div class="edu-card">
            <div>
                <span class="edu-card-badge">${t.category}</span>
                <h3>${t.title}</h3>
                <p>${t.content}</p>
                <div class="doc-section-block">
                    <strong>💡 Example:</strong> ${t.example}
                </div>
            </div>
            <div style="margin-top: 1rem; font-size: 0.82rem; color: var(--primary);">
                <strong>Key Takeaway:</strong> ${t.key_takeaway}
            </div>
        </div>
    `).join('');
}

function filterEducationCategory(category) {
    document.querySelectorAll('#edu-category-pills .category-pill').forEach(pill => {
        pill.classList.toggle('active', pill.textContent.toLowerCase().includes(category.toLowerCase()) || (category === 'all' && pill.textContent.includes('All')));
    });

    if (category === 'all') {
        renderEducationCards(AppState.educationTopics);
    } else {
        const filtered = AppState.educationTopics.filter(t => t.category.toLowerCase() === category.toLowerCase());
        renderEducationCards(filtered);
    }
}

function filterEducationTopics(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
        renderEducationCards(AppState.educationTopics);
        return;
    }
    const filtered = AppState.educationTopics.filter(t =>
        t.title.toLowerCase().includes(q) ||
        t.content.toLowerCase().includes(q) ||
        t.summary.toLowerCase().includes(q)
    );
    renderEducationCards(filtered);
}

async function loadTaxDocuments() {
    try {
        const resp = await fetch('/api/documents');
        const data = await resp.json();
        AppState.taxDocuments = data.documents || [];
        renderTaxDocuments(AppState.taxDocuments);
    } catch (e) {
        console.error('Failed to load tax documents:', e);
    }
}

function renderTaxDocuments(docs) {
    const container = document.getElementById('documents-cards-container');
    const sectionContainer = document.getElementById('tax-section-cards-container');
    const sections = docs.filter(document => document.kind === 'tax-section');
    const generalDocuments = docs.filter(document => document.kind !== 'tax-section');

    if (sectionContainer) {
        sectionContainer.innerHTML = sections.map(section => {
            const conditions = (section.conditions || []).map(condition => `<li>${escapeHTML(condition)}</li>`).join('');
            const sourceUrl = escapeHTML(section.official_source_url || 'https://www.incometax.gov.in/iec/foportal/');
            return `
                <article class="doc-card tax-section-card">
                    <div class="tax-section-card-heading">
                        <span class="edu-card-badge">${escapeHTML(section.name)}</span>
                        <span class="tax-regime-badge">${escapeHTML(section.regime || 'Check current regime')}</span>
                    </div>
                    <h3>${escapeHTML(section.full_title)}</h3>
                    <p>${escapeHTML(section.what_it_is)}</p>
                    <div class="doc-section-block"><strong>Why it matters:</strong> ${escapeHTML(section.why_important)}</div>
                    <details class="tax-section-details">
                        <summary>Eligibility, limits & records</summary>
                        <div class="tax-section-detail-body">
                            <p><strong>Who may qualify:</strong> ${escapeHTML(section.who_receives_it)}</p>
                            <p><strong>Limit and scope:</strong> ${escapeHTML(section.what_it_contains)}</p>
                            <strong>Conditions to check</strong>
                            <ul>${conditions}</ul>
                            <p><strong>Records to review:</strong> ${escapeHTML(section.records || 'Keep records supporting the claim.')}</p>
                            <p><strong>When to review:</strong> ${escapeHTML(section.when_needed)}</p>
                            <p class="tax-section-caution"><strong>Caution:</strong> ${escapeHTML(section.caution || 'Confirm current rules and personal eligibility.')}</p>
                            <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer">${escapeHTML(section.official_source || 'Income Tax Department portal')}</a>
                        </div>
                    </details>
                </article>
            `;
        }).join('');

        const sectionCount = document.getElementById('tax-section-count');
        if (sectionCount) sectionCount.textContent = `${sections.length} sections`;
    }

    if (container) {
        container.innerHTML = generalDocuments.map(document => `
            <article class="doc-card">
                <div>
                    <span class="edu-card-badge">${escapeHTML(document.name)}</span>
                    <h3>${escapeHTML(document.full_title)}</h3>
                    <p>${escapeHTML(document.what_it_is)}</p>
                    <div class="doc-section-block"><strong>Why it matters:</strong> ${escapeHTML(document.why_important)}</div>
                    <div class="doc-section-block"><strong>Who uses it:</strong> ${escapeHTML(document.who_receives_it)}</div>
                    <div class="doc-section-block"><strong>What it contains:</strong> ${escapeHTML(document.what_it_contains)}</div>
                </div>
                <div class="doc-when-needed"><strong>When it may be needed:</strong> ${escapeHTML(document.when_needed)}</div>
            </article>
        `).join('');
    }
}

function filterTaxDocuments(query) {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
        renderTaxDocuments(AppState.taxDocuments);
        return;
    }
    const filtered = AppState.taxDocuments.filter(document =>
        [document.name, document.full_title, document.what_it_is, document.why_important,
            document.who_receives_it, document.what_it_contains, document.regime,
            document.conditions?.join(' '), document.records, document.caution]
            .filter(Boolean)
            .join(' ')
            .toLowerCase()
            .includes(normalizedQuery)
    );
    renderTaxDocuments(filtered);
}

// =============================================================================
// Admin Telemetry & Rules Loader (Specification Section 34)
// =============================================================================
async function loadAdminData() {
    const token = document.getElementById('admin-token')?.value.trim();
    const status = document.getElementById('admin-status-msg');
    if (!token) {
        if (status) status.textContent = 'Enter the configured admin token to load protected statistics.';
        return;
    }

    try {
        const statsResp = await fetch('/api/admin/stats', {
            headers: { 'X-Admin-Token': token }
        });
        const stats = await statsResp.json();
        if (!statsResp.ok) throw new Error(stats.error || 'Admin authorization failed.');

        document.getElementById('admin-user-count').textContent = stats.total_users;
        document.getElementById('admin-profile-count').textContent = stats.profiles_created;
        document.getElementById('admin-rules-count').textContent = stats.tax_rules_configured;
        document.getElementById('admin-docs-count').textContent = stats.knowledge_base_documents;

        const rulesResp = await fetch(`/api/tax-rules?financial_year=${encodeURIComponent(AppState.financialYear)}`);
        const rulesData = await rulesResp.json();
        const tbody = document.getElementById('admin-rules-tbody');

        if (tbody && rulesData.rules) {
            tbody.innerHTML = rulesData.rules.map(r => `
                <tr>
                    <td><span class="badge badge-light">${escapeHTML(r.financial_year)}</span></td>
                    <td><strong>${escapeHTML(r.rule_name)}</strong></td>
                    <td>${escapeHTML(r.rule_type)}</td>
                    <td>${r.limits ? formatINR(r.limits) : 'Special Formula / Uncapped'}</td>
                    <td style="font-size: 0.8rem; color: var(--text-muted);">${escapeHTML(r.source)}</td>
                </tr>
            `).join('');
        }
        if (status) status.textContent = '';
    } catch (e) {
        if (status) status.textContent = e.message || 'Failed to load admin data.';
    }
}

// =============================================================================
// User Authentication & Profile Persistence (Specification Section 5)
// =============================================================================
async function checkCurrentUser() {
    try {
        const resp = await fetch('/api/auth/me');
        const data = await resp.json();
        if (data.authenticated && data.user) {
            setUserLoggedIn(data.user, data.profile);
        } else {
            setUserLoggedOut();
        }
    } catch (e) {
        setUserLoggedOut();
    }
}

function setUserLoggedIn(user, profile) {
    AppState.currentUser = user;

    document.getElementById('auth-buttons-container')?.classList.add('hidden');
    document.getElementById('mobile-auth-actions')?.classList.add('hidden');
    document.getElementById('mobile-user-actions')?.classList.remove('hidden');
    const badge = document.getElementById('user-profile-badge');
    if (badge) {
        badge.classList.remove('hidden');
        document.getElementById('nav-user-name').textContent = user.name;
        document.getElementById('nav-user-initial').textContent = user.name.charAt(0).toUpperCase();
    }

    document.getElementById('profile-logged-out-msg')?.classList.add('hidden');
    document.getElementById('profile-form-container')?.classList.remove('hidden');

    if (document.getElementById('prof-name')) document.getElementById('prof-name').value = user.name;
    if (document.getElementById('prof-email')) document.getElementById('prof-email').value = user.email;

    if (profile) {
        if (document.getElementById('prof-age')) document.getElementById('prof-age').value = profile.age || 28;
        if (document.getElementById('prof-income')) document.getElementById('prof-income').value = profile.income || 1200000;
        if (document.getElementById('prof-regime')) document.getElementById('prof-regime').value = profile.regime || 'new';
        if (document.getElementById('prof-fy')) document.getElementById('prof-fy').value = profile.financial_year || 'FY 2025-26';

        AppState.financialYear = profile.financial_year || AppState.financialYear;
        document.getElementById('global-fy-select').value = AppState.financialYear;
        document.getElementById('wiz-age').value = profile.age || 28;
        document.getElementById('wiz-salary').value = profile.income || 1200000;
        document.getElementById('wiz-employment').value = profile.employment_type || 'salaried';
        document.getElementById('wiz-regime').value = profile.regime || 'new';
        recalculateAll();
    }
}

function setUserLoggedOut() {
    AppState.currentUser = null;
    document.getElementById('auth-buttons-container')?.classList.remove('hidden');
    document.getElementById('mobile-auth-actions')?.classList.remove('hidden');
    document.getElementById('mobile-user-actions')?.classList.add('hidden');
    document.getElementById('user-profile-badge')?.classList.add('hidden');
    document.getElementById('profile-logged-out-msg')?.classList.remove('hidden');
    document.getElementById('profile-form-container')?.classList.add('hidden');
}

async function submitLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');

    errorEl.textContent = '';

    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            closeModal('login-modal');
            checkCurrentUser();
            loadAdminData();
        } else {
            errorEl.textContent = data.error || 'Login failed.';
        }
    } catch (e) {
        errorEl.textContent = 'Server connection error.';
    }
}

async function submitRegister() {
    const name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const errorEl = document.getElementById('reg-error');

    errorEl.textContent = '';

    try {
        const resp = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            closeModal('register-modal');
            checkCurrentUser();
            loadAdminData();
        } else {
            errorEl.textContent = data.error || 'Registration failed.';
        }
    } catch (e) {
        errorEl.textContent = 'Server connection error.';
    }
}

async function logoutUser() {
    await fetch('/api/auth/logout', { method: 'POST' });
    setUserLoggedOut();
    loadAdminData();
}

async function saveProfile() {
    const payload = {
        age: parseInt(document.getElementById('prof-age').value) || 28,
        income: parseFloat(document.getElementById('prof-income').value) || 0,
        regime: document.getElementById('prof-regime').value,
        financial_year: document.getElementById('prof-fy').value
    };

    const statusMsg = document.getElementById('profile-status-msg');
    statusMsg.textContent = 'Saving...';

    try {
        const resp = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await resp.json();
        if (resp.ok && result.success) {
            statusMsg.textContent = 'Saved successfully!';
            statusMsg.style.color = 'var(--success)';
            AppState.financialYear = payload.financial_year;
            document.getElementById('global-fy-select').value = payload.financial_year;
            document.getElementById('wiz-age').value = payload.age;
            document.getElementById('wiz-salary').value = payload.income;
            document.getElementById('wiz-regime').value = payload.regime;
            recalculateAll();
            setTimeout(() => { statusMsg.textContent = ''; }, 3000);
        } else {
            statusMsg.textContent = result.error || 'Failed to save.';
            statusMsg.style.color = 'var(--danger)';
        }
    } catch (e) {
        statusMsg.textContent = 'Failed to save.';
        statusMsg.style.color = 'var(--danger)';
    }
}

async function changePassword() {
    const statusMsg = document.getElementById('password-status-msg');
    statusMsg.textContent = 'Updating...';
    try {
        const response = await fetch('/api/auth/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: document.getElementById('current-password').value,
                new_password: document.getElementById('new-password').value
            })
        });
        const result = await response.json();
        statusMsg.textContent = response.ok ? 'Password updated.' : (result.error || 'Could not update password.');
        statusMsg.style.color = response.ok ? 'var(--success)' : 'var(--danger)';
        if (response.ok) document.getElementById('change-password-form').reset();
    } catch (error) {
        statusMsg.textContent = 'Could not connect to the server.';
        statusMsg.style.color = 'var(--danger)';
    }
}

// =============================================================================
// Helper Explainer Modal
// =============================================================================
function showExplainer(title, explanation) {
    document.getElementById('explainer-title').textContent = title;
    document.getElementById('explainer-body').innerHTML = `<p>${explanation}</p>`;
    openModal('explainer-modal');
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

function switchModal(fromId, toId) {
    closeModal(fromId);
    openModal(toId);
}
