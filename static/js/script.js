/**
 * MaxWell Webscraper - メインJavaScriptファイル
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初期化
    initTabs();
    initUrlInputs();
    initSelectorInputs();
    initCheckboxToggles();
    initRunButton();
    initTestSelectorForm();
});

/**
 * タブ切り替え機能の初期化
 */
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // アクティブタブの切り替え
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // タブコンテンツの切り替え
            const targetId = tab.getAttribute('data-target');
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetId) {
                    content.classList.add('active');
                }
            });
        });
    });
}

/**
 * URL入力フィールドの動的追加・削除機能を初期化
 */
function initUrlInputs() {
    const urlContainer = document.getElementById('url-container');
    const addUrlButton = document.getElementById('add-url');
    
    if (addUrlButton) {
        addUrlButton.addEventListener('click', () => {
            addUrlField();
        });
    }
    
    // 初期URLフィールドにも削除ボタンを追加
    document.querySelectorAll('.url-group').forEach(group => {
        addRemoveButtonToUrlGroup(group);
    });
}

/**
 * URLフィールドを追加
 */
function addUrlField() {
    const urlContainer = document.getElementById('url-container');
    const urlCount = urlContainer.querySelectorAll('.url-group').length;
    
    const urlGroup = document.createElement('div');
    urlGroup.className = 'url-group';
    urlGroup.innerHTML = `
        <input type="text" name="url[]" placeholder="スクレイピング対象URL ${urlCount + 1}" class="url-input">
    `;
    
    urlContainer.appendChild(urlGroup);
    addRemoveButtonToUrlGroup(urlGroup);
}

/**
 * URL入力グループに削除ボタンを追加
 */
function addRemoveButtonToUrlGroup(group) {
    const urlContainer = document.getElementById('url-container');
    
    // 最初のフィールドに削除ボタンを追加しない場合は以下の条件をコメントアウト解除
    // if (urlContainer.querySelectorAll('.url-group').length <= 1) return;
    
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'btn-remove';
    removeButton.textContent = '-';
    removeButton.addEventListener('click', () => {
        // 少なくとも1つのURLフィールドは残す
        if (urlContainer.querySelectorAll('.url-group').length > 1) {
            group.remove();
        }
    });
    
    group.appendChild(removeButton);
}

/**
 * セレクタ入力フィールドの動的追加・削除機能を初期化
 */
function initSelectorInputs() {
    const selectorContainer = document.getElementById('selector-container');
    const addSelectorButton = document.getElementById('add-selector');
    
    if (addSelectorButton) {
        addSelectorButton.addEventListener('click', () => {
            addSelectorField();
        });
    }
    
    // 初期セレクタフィールドにも削除ボタンを追加
    document.querySelectorAll('.selector-group').forEach(group => {
        addRemoveButtonToSelectorGroup(group);
    });
}

/**
 * セレクタフィールドを追加
 */
function addSelectorField() {
    const selectorContainer = document.getElementById('selector-container');
    const selectorCount = selectorContainer.querySelectorAll('.selector-group').length;
    
    const selectorGroup = document.createElement('div');
    selectorGroup.className = 'selector-group';
    selectorGroup.innerHTML = `
        <input type="text" name="selector_label[]" placeholder="列名 ${selectorCount + 1}" class="selector-label">
        <input type="text" name="selector_value[]" placeholder="CSSセレクタ ${selectorCount + 1}" class="selector-input">
    `;
    
    selectorContainer.appendChild(selectorGroup);
    addRemoveButtonToSelectorGroup(selectorGroup);
}

/**
 * セレクタ入力グループに削除ボタンを追加
 */
function addRemoveButtonToSelectorGroup(group) {
    const selectorContainer = document.getElementById('selector-container');
    
    // 最初のフィールドに削除ボタンを追加しない場合は以下の条件をコメントアウト解除
    // if (selectorContainer.querySelectorAll('.selector-group').length <= 1) return;
    
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'btn-remove';
    removeButton.textContent = '-';
    removeButton.addEventListener('click', () => {
        // 少なくとも1つのセレクタフィールドは残す
        if (selectorContainer.querySelectorAll('.selector-group').length > 1) {
            group.remove();
        }
    });
    
    group.appendChild(removeButton);
}

/**
 * チェックボックストグル機能の初期化
 */
function initCheckboxToggles() {
    // ログイン設定セクションのトグル
    const loginCheckbox = document.getElementById('require-login');
    const loginSection = document.getElementById('login-section');
    
    if (loginCheckbox && loginSection) {
        toggleSectionVisibility(loginCheckbox, loginSection);
        loginCheckbox.addEventListener('change', () => {
            toggleSectionVisibility(loginCheckbox, loginSection);
        });
    }
    
    // ページネーション設定セクションのトグル
    const paginationCheckbox = document.getElementById('use-pagination');
    const paginationSection = document.getElementById('pagination-section');
    
    if (paginationCheckbox && paginationSection) {
        toggleSectionVisibility(paginationCheckbox, paginationSection);
        paginationCheckbox.addEventListener('change', () => {
            toggleSectionVisibility(paginationCheckbox, paginationSection);
        });
    }
    
    // 画像ダウンロード設定セクションのトグル
    const imageCheckbox = document.getElementById('download-images');
    const imageSection = document.getElementById('image-section');
    
    if (imageCheckbox && imageSection) {
        toggleSectionVisibility(imageCheckbox, imageSection);
        imageCheckbox.addEventListener('change', () => {
            toggleSectionVisibility(imageCheckbox, imageSection);
        });
    }
}

/**
 * チェックボックスの状態に応じてセクションの表示/非表示を切り替え
 */
function toggleSectionVisibility(checkbox, section) {
    if (checkbox.checked) {
        section.style.display = 'block';
    } else {
        section.style.display = 'none';
    }
}

/**
 * スクレイピング実行ボタンの初期化
 */
function initRunButton() {
    const runForm = document.getElementById('scraper-form');
    const runButton = document.getElementById('run-button');
    const loadingElement = document.getElementById('loading');
    const logArea = document.getElementById('log-area');
    
    if (runForm && runButton) {
        runForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // フォームの入力値を取得
            const formData = getFormData();
            
            // バリデーション
            if (!validateForm(formData)) {
                return;
            }
            
            // ローディング表示
            if (loadingElement) loadingElement.style.display = 'block';
            if (runButton) runButton.disabled = true;
            
            // ログエリアをクリア
            if (logArea) logArea.innerHTML = '';
            addLogMessage('スクレイピングを開始します...', 'info');
            
            try {
                // APIリクエスト
                const response = await fetch('/run-scraper/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    addLogMessage(data.message, 'success');
                } else {
                    addLogMessage(`エラー: ${data.message}`, 'error');
                }
            } catch (error) {
                addLogMessage(`エラー: ${error.message}`, 'error');
            } finally {
                // ローディング非表示
                if (loadingElement) loadingElement.style.display = 'none';
                if (runButton) runButton.disabled = false;
            }
        });
    }
}

/**
 * フォームデータを取得
 */
function getFormData() {
    // URL配列を取得
    const urlInputs = document.querySelectorAll('.url-input');
    const urls = Array.from(urlInputs).map(input => input.value.trim());
    
    // 抽出セレクタを取得
    const selectorLabels = document.querySelectorAll('input[name="selector_label[]"]');
    const selectorValues = document.querySelectorAll('input[name="selector_value[]"]');
    
    const extractionSelectors = {};
    for (let i = 0; i < selectorLabels.length; i++) {
        const label = selectorLabels[i].value.trim();
        const value = selectorValues[i].value.trim();
        
        if (label && value) {
            extractionSelectors[label] = value;
        }
    }
    
    // ログイン設定を取得
    const requireLogin = document.getElementById('require-login').checked;
    let usernameSelector = '';
    let passwordSelector = '';
    let loginButtonSelector = '';
    let username = '';
    let password = '';
    
    if (requireLogin) {
        usernameSelector = document.getElementById('username-selector').value.trim();
        passwordSelector = document.getElementById('password-selector').value.trim();
        loginButtonSelector = document.getElementById('login-button-selector').value.trim();
        username = document.getElementById('username').value.trim();
        password = document.getElementById('password').value.trim();
    }
    
    // ページネーション設定を取得
    const usePagination = document.getElementById('use-pagination').checked;
    let nextButtonSelector = '';
    let maxPages = 1;
    
    if (usePagination) {
        nextButtonSelector = document.getElementById('next-button-selector').value.trim();
        maxPages = parseInt(document.getElementById('max-pages').value) || 1;
    }
    
    // 画像ダウンロード設定を取得
    const downloadImages = document.getElementById('download-images').checked;
    let imageSelector = '';
    
    if (downloadImages) {
        imageSelector = document.getElementById('image-selector').value.trim();
    }
    
    // その他の設定を取得
    const additionalUrl = document.getElementById('additional-url').value.trim();
    const useTextMode = document.getElementById('use-text-mode').checked;
    const outputPath = document.getElementById('output-path').value.trim() || 'output';
    
    return {
        urls,
        extraction_selectors: extractionSelectors,
        require_login: requireLogin,
        username_selector: usernameSelector,
        password_selector: passwordSelector,
        login_button_selector: loginButtonSelector,
        username,
        password,
        use_pagination: usePagination,
        next_button_selector: nextButtonSelector,
        max_pages: maxPages,
        download_images: downloadImages,
        image_selector: imageSelector,
        additional_url: additionalUrl,
        use_text_mode: useTextMode,
        output_path: outputPath
    };
}

/**
 * フォームのバリデーション
 */
function validateForm(formData) {
    // URLが少なくとも1つ設定されているか
    if (!formData.urls.some(url => url !== '')) {
        addLogMessage('エラー: 少なくとも1つのURLを入力してください', 'error');
        return false;
    }
    
    // 抽出セレクタが少なくとも1つ設定されているか
    if (Object.keys(formData.extraction_selectors).length === 0) {
        addLogMessage('エラー: 少なくとも1つの抽出セレクタを設定してください', 'error');
        return false;
    }
    
    // ログイン設定が有効な場合のバリデーション
    if (formData.require_login) {
        if (!formData.username_selector || !formData.password_selector || !formData.login_button_selector) {
            addLogMessage('エラー: ログイン設定には、ユーザー名セレクタ、パスワードセレクタ、ログインボタンセレクタが必要です', 'error');
            return false;
        }
        
        if (!formData.username || !formData.password) {
            addLogMessage('エラー: ログイン設定には、ユーザー名とパスワードが必要です', 'error');
            return false;
        }
    }
    
    // ページネーション設定が有効な場合のバリデーション
    if (formData.use_pagination) {
        if (!formData.next_button_selector) {
            addLogMessage('エラー: ページネーション設定には、次へボタンセレクタが必要です', 'error');
            return false;
        }
    }
    
    // 画像ダウンロード設定が有効な場合のバリデーション
    if (formData.download_images) {
        if (!formData.image_selector) {
            addLogMessage('エラー: 画像ダウンロード設定には、画像セレクタが必要です', 'error');
            return false;
        }
    }
    
    return true;
}

/**
 * ログメッセージを追加
 */
function addLogMessage(message, type = 'info') {
    const logArea = document.getElementById('log-area');
    
    if (!logArea) return;
    
    const logEntry = document.createElement('p');
    logEntry.className = `log-${type}`;
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    
    logArea.appendChild(logEntry);
    logArea.scrollTop = logArea.scrollHeight;
}

/**
 * セレクタテストフォームの初期化
 */
function initTestSelectorForm() {
    const testForm = document.getElementById('selector-test-form');
    const testButton = document.getElementById('test-selector-button');
    const testLoadingElement = document.getElementById('test-loading');
    const resultArea = document.getElementById('test-result');
    
    if (testForm && testButton) {
        testForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const testUrl = document.getElementById('test-url').value.trim();
            const testSelector = document.getElementById('test-selector').value.trim();
            
            if (!testUrl || !testSelector) {
                if (resultArea) {
                    resultArea.innerHTML = '<p class="log-error">URLとセレクタを入力してください</p>';
                }
                return;
            }
            
            // ローディング表示
            if (testLoadingElement) testLoadingElement.style.display = 'block';
            if (testButton) testButton.disabled = true;
            
            // 結果エリアをクリア
            if (resultArea) resultArea.innerHTML = '';
            
            try {
                // APIリクエスト
                const response = await fetch('/test-selector/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: testUrl,
                        selector: testSelector
                    })
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    if (resultArea) {
                        resultArea.innerHTML = `<p class="log-success">${data.message}</p>`;
                        
                        if (data.results && data.results.length > 0) {
                            data.results.forEach(result => {
                                const resultItem = document.createElement('div');
                                resultItem.className = 'result-item';
                                resultItem.innerHTML = `
                                    <strong>要素 #${result.index + 1}</strong><br>
                                    <div>テキスト: ${escapeHtml(result.text)}</div>
                                    <div style="margin-top: 5px;">HTML: <pre style="margin: 0;">${escapeHtml(result.html)}</pre></div>
                                `;
                                resultArea.appendChild(resultItem);
                            });
                        }
                    }
                } else {
                    if (resultArea) {
                        resultArea.innerHTML = `<p class="log-error">エラー: ${data.message}</p>`;
                    }
                }
            } catch (error) {
                if (resultArea) {
                    resultArea.innerHTML = `<p class="log-error">エラー: ${error.message}</p>`;
                }
            } finally {
                // ローディング非表示
                if (testLoadingElement) testLoadingElement.style.display = 'none';
                if (testButton) testButton.disabled = false;
            }
        });
    }
}

/**
 * HTMLエスケープ
 */
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
} 