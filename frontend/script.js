// API 基础地址（前后端同源）
const API_BASE = '/api';

// DOM 元素
const collectionSelect = document.getElementById('collectionSelect');
const targetCollectionSelect = document.getElementById('targetCollection');
const currentCollectionSpan = document.getElementById('currentCollectionDisplay');
const refreshBtn = document.getElementById('refreshCollectionsBtn');
const createCollectionBtn = document.getElementById('createCollectionBtn');
const newCollectionNameInput = document.getElementById('newCollectionName');
const uploadBtn = document.getElementById('uploadBtn');
const docFileInput = document.getElementById('docFile');
const minChunkInput = document.getElementById('minChunk');
const maxChunkInput = document.getElementById('maxChunk');
const uploadStatusDiv = document.getElementById('uploadStatus');
const askBtn = document.getElementById('askBtn');
const questionInput = document.getElementById('questionInput');
const chatMessagesDiv = document.getElementById('chatMessages');

let currentCollection = '';

// ========== UI 辅助函数 ==========
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-msg ${type}`;
    if (type === 'success') {
        setTimeout(() => {
            if (element === uploadStatusDiv) {
                element.textContent = '';
                element.className = 'status-msg';
            }
        }, 4000);
    }
}

function addMessageToChat(role, content, isMarkdown = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '📖';
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (role === 'bot' && isMarkdown) {
        // 预处理：将 \\[ ... \\] 转换为 $$ ... $$，\\( ... \\) 转换为 $ ... $
        let processedContent = content;
        // 匹配 \\[ ... \\] （非贪婪，支持多行）
        processedContent = processedContent.replace(/\\\[(.*?)\\\]/gs, (match, p1) => {
            return `$$ ${p1} $$`;
        });
        // 匹配 \\( ... \\)
        processedContent = processedContent.replace(/\\\((.*?)\\\)/gs, (match, p1) => {
            return `$ ${p1} $`;
        });
        
        // 使用 marked 解析 Markdown
        let html = marked.parse(processedContent);
        contentDiv.innerHTML = html;
        
        // 渲染 KaTeX 公式
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(contentDiv, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                throwOnError: false
            });
        }
        
        // 代码高亮
        contentDiv.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
    } else {
        contentDiv.textContent = content;
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessagesDiv.appendChild(messageDiv);
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
}

function addLoadingMessage() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot';
    loadingDiv.id = 'loadingMsg';
    loadingDiv.innerHTML = `<div class="message-avatar">📖</div><div class="message-content">思考中 <span class="loading-spinner"></span></div>`;
    chatMessagesDiv.appendChild(loadingDiv);
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
}

function removeLoadingMessage() {
    const loadingMsg = document.getElementById('loadingMsg');
    if (loadingMsg) loadingMsg.remove();
}

// ========== API 调用 ==========
function preprocessLatexInMarkdown(text) {
    // 匹配不在代码块内的成对方括号，且内部包含 LaTeX 命令字符（如 \frac, \text, \sum, \int 等）
    // 简单正则：匹配 [ 内容 ]，内容中不包含方括号（不支持嵌套），且包含反斜杠加字母（LaTeX命令）
    // 为了防止破坏普通文本中的方括号，只替换明显是公式的块
    // 更安全的做法：将形如 "[ \\text{...} = ... ]" 的替换为 "$$ \\text{...} = ... $$"
    // 注意：原文本中可能已经有 $$ 或 \[\]，不要重复替换
    
    // 暂不处理代码块内的内容（简化起见，完整实现需要跳过 ``` 代码块）
    // 匹配 [ ... ] 其中 ... 不包含 [ ] 但包含反斜杠字母组合
    // 注意：这里使用非贪婪匹配，且要求开头的 [ 前面不是反斜杠（避免已转义）
    const regex = /(?<!\\)\[((?:[^\[\]]|\\[\[\]])+?)\](?!\\)/g;
    return text.replace(regex, (match, content) => {
        // 如果内容中包含 LaTeX 命令特征（例如 \text, \frac, \sum 等），则认为是公式
        if (/\\[a-zA-Z]+/.test(content)) {
            // 转换为块级公式 $$
            return `$$ ${content} $$`;
        }
        // 否则保持原样
        return match;
    });
}

async function loadCollections() {
    try {
        const res = await fetch(`${API_BASE}/collections/`);
        if (!res.ok) throw new Error('加载失败');
        const collections = await res.json();
        const options = collections.map(c => `<option value="${c.name}">${c.name} (${c.document_count})</option>`).join('');
        collectionSelect.innerHTML = options || '<option value="">暂无集合</option>';
        targetCollectionSelect.innerHTML = options;
        
        if (currentCollection && collections.some(c => c.name === currentCollection)) {
            collectionSelect.value = currentCollection;
            targetCollectionSelect.value = currentCollection;
            currentCollectionSpan.textContent = currentCollection;
        } else if (collections.length) {
            collectionSelect.value = collections[0].name;
            targetCollectionSelect.value = collections[0].name;
            onCollectionChange();
        } else {
            currentCollectionSpan.textContent = '未选择';
        }
    } catch (err) {
        console.error(err);
        collectionSelect.innerHTML = '<option value="">加载失败</option>';
    }
}

function onCollectionChange() {
    currentCollection = collectionSelect.value;
    currentCollectionSpan.textContent = currentCollection || '未选择';
    if (targetCollectionSelect) targetCollectionSelect.value = currentCollection;
}

async function createCollection() {
    const name = newCollectionNameInput.value.trim();
    if (!name) {
        showStatus(uploadStatusDiv, '请输入集合名称', 'error');
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/collections/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '创建失败');
        }
        showStatus(uploadStatusDiv, `集合 "${name}" 创建成功`, 'success');
        newCollectionNameInput.value = '';
        await loadCollections();
        collectionSelect.value = name;
        onCollectionChange();
    } catch (err) {
        showStatus(uploadStatusDiv, err.message, 'error');
    }
}

async function uploadDocument() {
    const files = docFileInput.files;
    if (!files || files.length === 0) {
        showStatus(uploadStatusDiv, '请选择至少一个文件', 'error');
        return;
    }
    const targetColl = targetCollectionSelect.value;
    if (!targetColl) {
        showStatus(uploadStatusDiv, '请选择目标集合', 'error');
        return;
    }
    const minChunk = parseInt(minChunkInput.value, 10);
    const maxChunk = parseInt(maxChunkInput.value, 10);
    if (minChunk >= maxChunk) {
        showStatus(uploadStatusDiv, '最小块必须小于最大块', 'error');
        return;
    }

    uploadBtn.disabled = true;
    uploadBtn.textContent = '上传中...';
    showStatus(uploadStatusDiv, `开始上传 ${files.length} 个文件...`, 'success');

    let successCount = 0;
    let failCount = 0;
    const statusLines = [];

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('collection_name', targetColl);
        formData.append('min_chunk_size', minChunk.toString());
        formData.append('max_chunk_size', maxChunk.toString());
        formData.append('record_stats', 'true');

        try {
            const response = await fetch(`${API_BASE}/documents/upload`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || '上传失败');
            }
            const data = await response.json();
            successCount++;
            statusLines.push(`✅ ${file.name}: ${data.total_chunks} 个片段`);
        } catch (err) {
            failCount++;
            statusLines.push(`❌ ${file.name}: ${err.message}`);
        }
        // 实时更新状态（可选）
        showStatus(uploadStatusDiv, `已处理 ${i+1}/${files.length} 个文件...`, 'success');
    }

    uploadBtn.disabled = false;
    uploadBtn.textContent = '上传并索引';
    
    // 完整结果
    const summary = `上传完成：成功 ${successCount} 个，失败 ${failCount} 个。\n` + statusLines.join('\n');
    showStatus(uploadStatusDiv, summary, successCount === files.length ? 'success' : 'error');
    
    // 如果全部成功，清空文件选择
    if (failCount === 0) {
        docFileInput.value = '';
    }
    // 刷新集合列表（文档数可能变化）
    await loadCollections();
}

async function askQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;
    if (!currentCollection) {
        addMessageToChat('bot', '请先在左侧选择一个集合。', false);
        return;
    }
    const adaptiveEnabled = document.getElementById('adaptiveToggle').checked; // 获取开关状态
    addMessageToChat('user', question, false);
    questionInput.value = '';
    addLoadingMessage();
    
    try {
        const res = await fetch(`${API_BASE}/query/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                collection_name: currentCollection,
                initial_k: null,
                final_top_k: null,
                adaptive_enabled: adaptiveEnabled
            })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '问答失败');
        }
        const data = await res.json();
        removeLoadingMessage();
        const answerMd = data.answer_markdown || data.answer_plain;
        const footer = `\n\n---\n⏱️ ${data.processing_time_ms.toFixed(0)} ms | 参考 ${data.contexts_count} 个片段`;
        addMessageToChat('bot', answerMd + footer, true);
    } catch (err) {
        removeLoadingMessage();
        addMessageToChat('bot', `❌ 错误：${err.message}`, false);
    }
}

// ========== 事件绑定 ==========
collectionSelect.addEventListener('change', onCollectionChange);
refreshBtn.addEventListener('click', loadCollections);
createCollectionBtn.addEventListener('click', createCollection);
uploadBtn.addEventListener('click', uploadDocument);
askBtn.addEventListener('click', askQuestion);
questionInput.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') askQuestion();
});

// 初始化
loadCollections();