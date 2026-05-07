<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const MARKDOWN_TEMPLATE = `# 企微消息通知

## 发送主题
- 事项：请填写本次通知主题
- 时间：请填写发送时间
- 负责人：请填写负责人

## 重点内容
1. 请填写第一条重点信息
2. 请填写第二条重点信息
3. 请填写第三条重点信息

## 后续安排
- 请填写需要跟进的动作
- 请填写截止时间或注意事项

> 如有图片素材，可在下方上传后随正文一起发送。`

const webhooks = ref({})
const newWebhook = ref({ name: '', url: '' })
const selectedWebhooks = ref([])
const messageText = ref(MARKDOWN_TEMPLATE)
const activeTab = ref('markdown')
const uploadRef = ref()
const markdownInputRef = ref()
const markdownPreviewBodyRef = ref()
const uploadedImages = ref([])
const sending = ref(false)
const addDialogVisible = ref(false)
const editingWebhookName = ref('')
const uploadSuccessNames = ref([])
const uploadFailedItems = ref([])
let markdownTextareaElement = null
let syncingMarkdownSource = null

const webhookEntries = computed(() => Object.entries(webhooks.value))
const selectedCount = computed(() => selectedWebhooks.value.length)
const uploadedCount = computed(() => uploadedImages.value.length)
const isEditingWebhook = computed(() => Boolean(editingWebhookName.value))

const escapeHtml = (value) => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;')

const formatInlineMarkdown = (value) => {
  const escaped = escapeHtml(value)
  return escaped
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

const markdownPreviewHtml = computed(() => {
  const lines = messageText.value.split('\n')
  const parts = []
  let listType = null

  const closeList = () => {
    if (listType) {
      parts.push(listType === 'ul' ? '</ul>' : '</ol>')
      listType = null
    }
  }

  for (const line of lines) {
    const trimmed = line.trim()

    if (!trimmed) {
      closeList()
      continue
    }

    if (trimmed.startsWith('### ')) {
      closeList()
      parts.push(`<h3>${formatInlineMarkdown(trimmed.slice(4))}</h3>`)
      continue
    }

    if (trimmed.startsWith('## ')) {
      closeList()
      parts.push(`<h2>${formatInlineMarkdown(trimmed.slice(3))}</h2>`)
      continue
    }

    if (trimmed.startsWith('# ')) {
      closeList()
      parts.push(`<h1>${formatInlineMarkdown(trimmed.slice(2))}</h1>`)
      continue
    }

    if (trimmed.startsWith('> ')) {
      closeList()
      parts.push(`<blockquote>${formatInlineMarkdown(trimmed.slice(2))}</blockquote>`)
      continue
    }

    if (trimmed.startsWith('- ')) {
      if (listType !== 'ul') {
        closeList()
        parts.push('<ul>')
        listType = 'ul'
      }
      parts.push(`<li>${formatInlineMarkdown(trimmed.slice(2))}</li>`)
      continue
    }

    const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)$/)
    if (orderedMatch) {
      if (listType !== 'ol') {
        closeList()
        parts.push('<ol>')
        listType = 'ol'
      }
      parts.push(`<li>${formatInlineMarkdown(orderedMatch[2])}</li>`)
      continue
    }

    closeList()
    parts.push(`<p>${formatInlineMarkdown(trimmed)}</p>`)
  }

  closeList()
  return parts.join('') || '<p>输入 Markdown 内容后，这里会实时显示预览。</p>'
})


const applyMarkdownTemplate = () => {
  messageText.value = MARKDOWN_TEMPLATE
  ElMessage.success('已套用 Markdown 模板')
}

const getMarkdownTextarea = () => markdownInputRef.value?.textarea || markdownInputRef.value?.$el?.querySelector('textarea') || null

const syncMarkdownPaneScroll = (source) => {
  const editorTextarea = getMarkdownTextarea()
  const previewBody = markdownPreviewBodyRef.value

  if (!editorTextarea || !previewBody) {
    return
  }

  const editorScrollableHeight = editorTextarea.scrollHeight - editorTextarea.clientHeight
  const previewScrollableHeight = previewBody.scrollHeight - previewBody.clientHeight

  if (source === 'editor') {
    const ratio = editorScrollableHeight > 0 ? editorTextarea.scrollTop / editorScrollableHeight : 0
    syncingMarkdownSource = 'editor'
    previewBody.scrollTop = previewScrollableHeight > 0 ? ratio * previewScrollableHeight : 0
    requestAnimationFrame(() => {
      syncingMarkdownSource = null
    })
    return
  }

  const ratio = previewScrollableHeight > 0 ? previewBody.scrollTop / previewScrollableHeight : 0
  syncingMarkdownSource = 'preview'
  editorTextarea.scrollTop = editorScrollableHeight > 0 ? ratio * editorScrollableHeight : 0
  requestAnimationFrame(() => {
    syncingMarkdownSource = null
  })
}

const handleMarkdownEditorScroll = () => {
  if (syncingMarkdownSource === 'preview') {
    return
  }
  syncMarkdownPaneScroll('editor')
}

const handleMarkdownPreviewScroll = () => {
  if (syncingMarkdownSource === 'editor') {
    return
  }
  syncMarkdownPaneScroll('preview')
}

const bindMarkdownScrollSync = async () => {
  await nextTick()
  const nextTextareaElement = getMarkdownTextarea()

  if (markdownTextareaElement === nextTextareaElement) {
    return
  }

  if (markdownTextareaElement) {
    markdownTextareaElement.removeEventListener('scroll', handleMarkdownEditorScroll)
  }

  markdownTextareaElement = nextTextareaElement
  markdownTextareaElement?.addEventListener('scroll', handleMarkdownEditorScroll, { passive: true })
}

const bindOverflowTitle = (el, text) => {
  if (!el) {
    return
  }

  requestAnimationFrame(() => {
    const isOverflowing = el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight
    if (isOverflowing) {
      el.setAttribute('title', text)
    } else {
      el.removeAttribute('title')
    }
  })
}

const loadWebhooks = async () => {
  try {
    const { data } = await axios.get('/api/webhooks')
    webhooks.value = data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '读取机器人列表失败')
  }
}

const closeWebhookDialog = () => {
  addDialogVisible.value = false
  editingWebhookName.value = ''
  newWebhook.value = { name: '', url: '' }
}

const updateWebhookWithFallback = async (oldName, payload) => {
  try {
    await axios.put(`/api/webhooks/${encodeURIComponent(oldName)}`, payload)
    return
  } catch (error) {
    const statusCode = error?.response?.status
    if (statusCode !== 404 && statusCode !== 405) {
      throw error
    }
  }

  const trimmedOldName = oldName.trim()
  const trimmedNewName = payload.name.trim()
  const trimmedNewUrl = payload.url.trim()

  if (trimmedNewName !== trimmedOldName && webhooks.value[trimmedNewName]) {
    throw new Error('机器人名称已存在，请使用其他名称')
  }

  await axios.post('/api/webhooks', { name: trimmedNewName, url: trimmedNewUrl })

  if (trimmedNewName !== trimmedOldName) {
    await axios.delete(`/api/webhooks/${encodeURIComponent(trimmedOldName)}`)
  }
}

const saveWebhook = async () => {
  if (!newWebhook.value.name.trim() || !newWebhook.value.url.trim()) {
    ElMessage.warning('请填写完整的机器人名称和地址')
    return
  }

  try {
    const previousName = editingWebhookName.value
    const previousUrl = previousName ? webhooks.value[previousName] : ''

    if (isEditingWebhook.value) {
      await updateWebhookWithFallback(editingWebhookName.value, newWebhook.value)

      if (previousUrl && selectedWebhooks.value.includes(previousUrl)) {
        selectedWebhooks.value = selectedWebhooks.value.map((url) => {
          if (url === previousUrl) {
            return newWebhook.value.url.trim()
          }
          return url
        })
      }
      ElMessage.success('机器人已更新')
    } else {
      await axios.post('/api/webhooks', newWebhook.value)
      ElMessage.success('机器人已保存')
    }

    newWebhook.value = { name: '', url: '' }
    editingWebhookName.value = ''
    closeWebhookDialog()
    await loadWebhooks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || (isEditingWebhook.value ? '更新机器人失败' : '新增机器人失败'))
  }
}

const openAddWebhookDialog = () => {
  newWebhook.value = { name: '', url: '' }
  editingWebhookName.value = ''
  addDialogVisible.value = true
}

const openEditWebhookDialog = (name, url) => {
  editingWebhookName.value = name
  newWebhook.value = { name, url }
  addDialogVisible.value = true
}

const deleteWebhook = async (name) => {
  try {
    await ElMessageBox.confirm(`确认删除机器人：${name}？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await axios.delete(`/api/webhooks/${encodeURIComponent(name)}`)
    selectedWebhooks.value = selectedWebhooks.value.filter((url) => url !== webhooks.value[name])
    ElMessage.success('机器人已删除')
    await loadWebhooks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除机器人失败')
    }
  }
}

const flushUploadMessages = () => {
  if (uploadSuccessNames.value.length) {
    const successLabel = uploadSuccessNames.value.join('、')
    const successText = `已成功上传图片：${successLabel}`
    ElMessage.success(successText)
  }

  if (uploadFailedItems.value.length) {
    const failedText = uploadFailedItems.value
      .map((item) => `${item.name}${item.reason ? `（${item.reason}）` : ''}`)
      .join('、')
    ElMessage.error(`以下图片上传失败：${failedText}`)
  }

  uploadSuccessNames.value = []
  uploadFailedItems.value = []
}

const clearUploadFilesIfSettled = (uploadFiles = []) => {
  const hasPendingFile = uploadFiles.some((file) => file.status === 'ready' || file.status === 'uploading')
  if (!hasPendingFile) {
    uploadRef.value?.clearFiles()
    flushUploadMessages()
  }
}

const handleUploadSuccess = (response, uploadFile, uploadFiles = []) => {
  if (!response?.token) {
    uploadFailedItems.value.push({
      name: uploadFile?.name || '未知文件',
      reason: '上传结果缺少 token',
    })
    clearUploadFilesIfSettled(uploadFiles)
    return
  }

  uploadedImages.value.push({
    token: response.token,
    name: response.name,
    size: response.size,
  })
  uploadSuccessNames.value.push(response.name)
  clearUploadFilesIfSettled(uploadFiles)
}

const handleUploadError = (error, uploadFile, uploadFiles = []) => {
  uploadFailedItems.value.push({
    name: uploadFile?.name || '未知文件',
    reason: error?.response?.data?.detail || '图片上传失败',
  })
  clearUploadFilesIfSettled(uploadFiles)
}

const removeUploadedImage = async (token, silent = false) => {
  try {
    await axios.delete(`/api/uploads/${token}`)
  } catch (error) {
    if (!silent) {
      ElMessage.error(error.response?.data?.detail || '删除上传图片失败')
      return false
    }
  }

  uploadedImages.value = uploadedImages.value.filter((item) => item.token !== token)
  if (!silent) {
    ElMessage.success('已从待发送队列移除')
  }
  return true
}

const clearUploadedImages = async () => {
  const tokens = uploadedImages.value.map((item) => item.token)
  for (const token of tokens) {
    await removeUploadedImage(token, true)
  }
  ElMessage.success('待发送队列已清空')
}

const sendMessage = async () => {
  if (!selectedWebhooks.value.length) {
    ElMessage.warning('请先选择至少一个机器人')
    return
  }

  if (activeTab.value === 'image' && !uploadedImages.value.length) {
    ElMessage.warning('图片模式下请至少上传一张图片')
    return
  }

  if (activeTab.value === 'markdown' && !messageText.value.trim() && !uploadedImages.value.length) {
    ElMessage.warning('请填写 Markdown 内容或上传图片')
    return
  }

  const payload = {
    webhook_urls: selectedWebhooks.value,
    msg_type: activeTab.value,
    content: {
      text: messageText.value,
      upload_tokens: uploadedImages.value.map((item) => item.token),
    },
  }

  sending.value = true
  try {
    const { data } = await axios.post('/api/send', payload)
    const successCount = data.results.filter((item) => item.status === 'success').length
    const failCount = data.results.length - successCount
    const failedItems = data.results.filter((item) => item.status === 'error')
    uploadedImages.value = []
    uploadRef.value?.clearFiles()

    if (successCount) {
      ElMessage.success(`发送完成：成功 ${successCount} 个，失败 ${failCount} 个`)
    } else {
      ElMessage.error(failedItems[0]?.msg || '发送失败，请检查 Webhook 配置或网络')
    }

    if (failedItems.length) {
      const details = failedItems
        .map((item) => `目标：${item.url}\n原因：${item.msg || '未知错误'}`)
        .join('\n\n')
      ElMessageBox.alert(details, '发送失败详情', { confirmButtonText: '知道了' })
    }

    if (data.notes?.length) {
      ElMessageBox.alert(data.notes.join('\n'), '发送说明', { confirmButtonText: '知道了' })
    }
  } catch (error) {
    const detail = error.response?.data?.detail || '发送失败'
    if (typeof detail === 'string' && detail.includes('上传文件不存在')) {
      uploadedImages.value = []
      uploadRef.value?.clearFiles()
    }
    ElMessage.error(detail)
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  loadWebhooks()
  bindMarkdownScrollSync()
})

watch(activeTab, () => {
  bindMarkdownScrollSync()
})

watch(messageText, async () => {
  await nextTick()
  syncMarkdownPaneScroll('editor')
})

onBeforeUnmount(() => {
  if (markdownTextareaElement) {
    markdownTextareaElement.removeEventListener('scroll', handleMarkdownEditorScroll)
  }
})
</script>

<template>
  <div class="app-shell">
    <section class="hero-panel">
      <div class="hero-main">
        <p class="eyebrow">Wechat Web Pusher</p>
        <h1>企微消息工作台</h1>
        <p class="hero-copy">面向日常群通知、巡检播报与图片分发的轻量工作台，帮助您更快地整理内容、选择目标并完成发送。</p>
      </div>
      <div class="hero-metrics">
        <div class="metric-card">
          <span>已选目标</span>
          <strong>{{ selectedCount }}</strong>
        </div>
        <div class="metric-card accent">
          <span>待发图片</span>
          <strong>{{ uploadedCount }}</strong>
        </div>
      </div>
    </section>

    <div class="workspace-grid">
      <aside class="panel sidebar-panel">
        <div class="panel-header sidebar-title-block">
          <h2>推送目标</h2>
          <p>先选择机器人，再整理本次要发送的内容和图片。</p>
        </div>

        <section class="sidebar-section sidebar-section-main">
          <div class="section-heading-row">
            <strong>机器人列表</strong>
            <span class="section-count" v-if="selectedCount > 0">已选 {{ selectedCount }} / 共 {{ webhookEntries.length }} 个</span>
            <span class="section-count" v-else>{{ webhookEntries.length }} 个</span>
          </div>

          <el-checkbox-group v-model="selectedWebhooks" class="webhook-list">
            <div v-for="([name, url]) in webhookEntries" :key="name" class="webhook-item">
              <el-checkbox :label="url" class="webhook-check-card">
                <div class="webhook-copy">
                  <span :ref="(el) => bindOverflowTitle(el, name)" class="webhook-name">{{ name }}</span>
                </div>
              </el-checkbox>
              <div class="webhook-item-actions">
                <el-button type="primary" link @click.prevent="openEditWebhookDialog(name, url)">编辑</el-button>
                <el-button type="danger" link @click.prevent="deleteWebhook(name)">删除</el-button>
              </div>
            </div>
          </el-checkbox-group>
        </section>

        <section class="sidebar-section sidebar-section-action">
          <div class="section-heading-row compact-row">
            <strong>新增机器人</strong>
          </div>
          <p class="sidebar-actions-tip">建议使用清晰名称，例如“巡检播报”“采购通知”，便于后续快速选择。</p>
          <el-button type="primary" class="sidebar-primary-btn" @click="openAddWebhookDialog">新增机器人</el-button>
        </section>
      </aside>

      <main class="panel content-panel">
        <div class="panel-header inline-header">
          <div>
            <h2>消息内容</h2>
            <p>在这里组织本次发送的正文与图片。不同模式会按各自的消息形式发往所选目标。</p>
          </div>
          <el-button type="primary" :loading="sending" @click="sendMessage">立即发送</el-button>
        </div>

        <div class="content-scroll-area">
          <el-tabs v-model="activeTab" class="composer-tabs">
            <el-tab-pane label="Markdown 图文" name="markdown">
              <div class="tab-section">
                <p class="hint-text">适合发送公告、巡检说明、日报摘要等内容。已上传的图片会在正文发送后依次补发。</p>
                <div class="editor-toolbar">
                  <span>可直接在模板基础上修改后发送。</span>
                  <el-button link type="primary" @click="applyMarkdownTemplate">套用模板</el-button>
                </div>
                <div class="markdown-workbench">
                  <section class="markdown-editor-panel">
                    <div class="markdown-pane-title">Markdown 编辑</div>
                    <el-input
                      ref="markdownInputRef"
                      class="composer-textarea"
                      v-model="messageText"
                      type="textarea"
                      :rows="8"
                      resize="none"
                      placeholder="输入本次要发送的 Markdown 内容，可配合下方图片素材一起发送。"
                    />
                  </section>
                  <section class="markdown-preview-panel">
                    <div class="markdown-pane-title">Markdown 预览</div>
                    <div ref="markdownPreviewBodyRef" class="markdown-preview-body" @scroll.passive="handleMarkdownPreviewScroll" v-html="markdownPreviewHtml"></div>
                  </section>
                </div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="批量图片" name="image">
              <div class="tab-section">
                <p class="hint-text">适合集中发送现场截图、巡检照片或宣传物料。图片会按上传顺序逐张发送。</p>
              </div>
            </el-tab-pane>
          </el-tabs>

          <div class="uploader-panel">
            <div class="panel-header compact">
                <div>
                  <h3>图片素材队列 <span class="tag-counter" v-if="uploadedCount">({{ uploadedCount }})</span></h3>
                  <p>先上传图片到队列，再根据需要与正文一起发送，或单独以图片消息形式发送。</p>
                </div>
                <el-button v-if="uploadedImages.length" link type="danger" @click="clearUploadedImages">清空队列</el-button>
              </div>

              <el-upload
              ref="uploadRef"
              drag
              action="/api/upload_image"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.bmp,.gif"
              :show-file-list="false"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
            >
              <div class="upload-dragger">
                <strong>拖拽图片到此处</strong>
                <span>或点击选择 PNG、JPG、WEBP 等常见图片格式</span>
              </div>
            </el-upload>

            <div v-if="uploadedImages.length" class="queue-list">
              <article v-for="item in uploadedImages" :key="item.token" class="queue-item">
                <div>
                  <strong>{{ item.name }}</strong>
                  <span>{{ Math.max(1, Math.round(item.size / 1024)) }} KB</span>
                </div>
                <el-button link type="danger" @click="removeUploadedImage(item.token)">移除</el-button>
              </article>
            </div>
            <div v-else class="empty-state">暂未添加图片，上传后会在这里展示待发送队列。</div>
          </div>
        </div>
      </main>
    </div>

    <el-dialog v-model="addDialogVisible" :title="isEditingWebhook ? '编辑机器人' : '新增机器人'" width="560px" destroy-on-close class="robot-dialog">
      <div class="dialog-form robot-dialog-form">
        <section class="dialog-hero">
          <strong>{{ isEditingWebhook ? '更新机器人信息' : '创建新的机器人' }}</strong>
          <p>机器人名称仅用于本地识别和选择，Webhook 地址仅保存在本地配置中，不会在列表中明文展示。</p>
        </section>

        <label class="dialog-field">
          <span class="dialog-label">机器人名称</span>
          <el-input v-model="newWebhook.name" placeholder="例如：测试群 / 巡检播报 / 采购通知" />
        </label>

        <label class="dialog-field">
          <span class="dialog-label">Webhook 地址</span>
          <el-input
            v-model="newWebhook.url"
            type="textarea"
            :rows="5"
            resize="none"
            placeholder="请输入企业微信群机器人的 Webhook 地址"
          />
          <span class="dialog-help">建议直接粘贴完整地址，保存后列表中不会展示原始链接。</span>
        </label>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="closeWebhookDialog">取消</el-button>
          <el-button type="primary" @click="saveWebhook">{{ isEditingWebhook ? '保存修改' : '保存机器人' }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

