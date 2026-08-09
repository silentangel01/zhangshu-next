<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { getAppConfig } from '@/entities/app-config/api'
import type { AppConfigResponse } from '@/entities/app-config/types'
import {
  acceptKnowledgeGraphRelation,
  createKnowledgeGraphExtractionRun,
  getKnowledgeGraphSubgraph,
  listKnowledgeGraphExtractionRuns,
  listKnowledgeGraphRelations,
  rejectKnowledgeGraphRelation,
} from '@/entities/knowledge/api'
import type {
  KnowledgeGraphExtractionRun,
  KnowledgeGraphExtractionScope,
  KnowledgeGraphRelation,
  KnowledgeGraphSubgraph,
} from '@/entities/knowledge/types'
import {
  knowledgeGraphEntityTypeLabels,
  knowledgeGraphExtractionStatusLabels,
  knowledgeGraphFactStatusLabels,
  knowledgeGraphRelationTypeLabels,
} from '@/entities/knowledge/types'
import { formatApiErrorMessage } from '@/shared/api/client'

const props = defineProps<{
  projectId: string
  selectedSourceId?: string | null
  selectedSourceTitle?: string | null
}>()

const emit = defineEmits<{
  selectSource: [sourceId: string]
}>()

const appConfig = ref<AppConfigResponse | null>(null)
const activeTab = ref<'candidates' | 'graph'>('candidates')
const extractionScope = ref<KnowledgeGraphExtractionScope>('source')
const privacyConfirmed = ref(false)
const maxChunks = ref(40)
const runs = ref<KnowledgeGraphExtractionRun[]>([])
const candidateRelations = ref<KnowledgeGraphRelation[]>([])
const acceptedRelations = ref<KnowledgeGraphRelation[]>([])
const subgraph = ref<KnowledgeGraphSubgraph>({ nodes: [], edges: [] })
const isLoading = ref(false)
const isExtracting = ref(false)
const mutatingRelationId = ref<string | null>(null)
const errorMessage = ref('')
const successMessage = ref('')
const isRefreshingGraph = ref(false)
let pollTimer: number | null = null

const canUseSelectedSource = computed(() => !!props.selectedSourceId)
const hasConfiguredLlm = computed(() => {
  const key = appConfig.value?.dashscope_api_key
  return appConfig.value?.llm_enabled === true && key?.has_value === true && key.decrypt_error !== true
})
const latestRun = computed(() => runs.value[0] ?? null)
const hasActiveRun = computed(() => {
  return latestRun.value?.status === 'pending' || latestRun.value?.status === 'running'
})
const hasValidChunkLimit = computed(() => {
  return Number.isFinite(maxChunks.value) && maxChunks.value >= 1 && maxChunks.value <= 80
})
const canExtract = computed(() => {
  if (!hasConfiguredLlm.value || !privacyConfirmed.value || isExtracting.value) return false
  if (!hasValidChunkLimit.value) return false
  if (extractionScope.value === 'source' && !props.selectedSourceId) return false
  return true
})

watch(
  () => props.selectedSourceId,
  () => {
    if (!props.selectedSourceId && extractionScope.value === 'source') {
      extractionScope.value = 'project'
    }
  },
)

watch(
  () => props.projectId,
  () => {
    void loadGraphData()
  },
)

onMounted(() => {
  if (!props.selectedSourceId) {
    extractionScope.value = 'project'
  }
  void loadAll()
})

onBeforeUnmount(() => {
  stopPolling()
})

async function loadAll() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [config] = await Promise.all([getAppConfig(), loadGraphData()])
    appConfig.value = config
  } catch (error) {
    errorMessage.value = formatApiErrorMessage(error, '知识图谱加载失败，请稍后重试。')
  } finally {
    isLoading.value = false
  }
}

async function loadGraphData() {
  if (!props.projectId) return
  if (isRefreshingGraph.value) return
  isRefreshingGraph.value = true
  try {
    const [runList, candidateList, acceptedList, graphData] = await Promise.all([
      listKnowledgeGraphExtractionRuns(props.projectId, 10),
      listKnowledgeGraphRelations(props.projectId, { status: 'candidate', limit: 80 }),
      listKnowledgeGraphRelations(props.projectId, { status: 'accepted', limit: 120 }),
      getKnowledgeGraphSubgraph(props.projectId, { status: 'accepted', limit: 120 }),
    ])
    runs.value = runList.items
    candidateRelations.value = candidateList.items
    acceptedRelations.value = acceptedList.items
    subgraph.value = graphData
    syncPolling()
  } finally {
    isRefreshingGraph.value = false
  }
}

function syncPolling() {
  if (hasActiveRun.value) {
    startPolling()
  } else {
    stopPolling()
  }
}

function startPolling() {
  if (pollTimer !== null) return
  pollTimer = window.setInterval(() => {
    void loadGraphData()
  }, 2500)
}

function stopPolling() {
  if (pollTimer === null) return
  window.clearInterval(pollTimer)
  pollTimer = null
}

async function handleExtract() {
  if (!canExtract.value) return
  if (hasActiveRun.value) {
    const shouldRestart = confirm('已有知识图谱抽取任务正在进行。是否替换旧任务并重新开始？')
    if (!shouldRestart) return
  }
  isExtracting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await createKnowledgeGraphExtractionRun(props.projectId, {
      scope: extractionScope.value,
      source_id: extractionScope.value === 'source' ? props.selectedSourceId : null,
      max_chunks: maxChunks.value,
      privacy_confirmed: privacyConfirmed.value,
    })
    successMessage.value = '已开始后台抽取，进度会自动刷新。'
    await loadGraphData()
    activeTab.value = 'candidates'
  } catch (error) {
    errorMessage.value = formatApiErrorMessage(error, '知识图谱抽取失败，请稍后重试。')
  } finally {
    isExtracting.value = false
  }
}

async function handleAcceptRelation(relation: KnowledgeGraphRelation) {
  mutatingRelationId.value = relation.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await acceptKnowledgeGraphRelation(props.projectId, relation.id)
    successMessage.value = '关系已确认。'
    await loadGraphData()
  } catch (error) {
    errorMessage.value = formatApiErrorMessage(error, '确认关系失败，请稍后重试。')
  } finally {
    mutatingRelationId.value = null
  }
}

async function handleRejectRelation(relation: KnowledgeGraphRelation) {
  mutatingRelationId.value = relation.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await rejectKnowledgeGraphRelation(props.projectId, relation.id)
    successMessage.value = '关系已忽略。'
    await loadGraphData()
  } catch (error) {
    errorMessage.value = formatApiErrorMessage(error, '忽略关系失败，请稍后重试。')
  } finally {
    mutatingRelationId.value = null
  }
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

function formatDate(value: string | null): string {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function evidencePreview(relation: KnowledgeGraphRelation): string {
  const evidence = relation.evidence[0]?.evidence_text || ''
  if (evidence.length <= 140) return evidence
  return `${evidence.slice(0, 140)}...`
}

function sourceTitle(relation: KnowledgeGraphRelation): string {
  return relation.evidence[0]?.source_title || '未知资料'
}

function openEvidenceSource(relation: KnowledgeGraphRelation) {
  const sourceId = relation.evidence[0]?.source_id
  if (sourceId) emit('selectSource', sourceId)
}

function nodeLabel(nodeId: string): string {
  return subgraph.value.nodes.find((node) => node.id === nodeId)?.label || nodeId
}
</script>

<template>
  <section class="knowledge-graph-panel">
    <header class="graph-header">
      <div>
        <h2>知识图谱</h2>
        <p>从知识库资料抽取实体关系候选，确认后进入图谱。</p>
      </div>
      <button class="secondary-button" type="button" :disabled="isLoading" @click="loadAll">
        刷新
      </button>
    </header>

    <section v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-message" role="status">{{ successMessage }}</section>

    <section class="extract-toolbar">
      <div class="llm-state" :class="{ ready: hasConfiguredLlm }">
        <span class="state-dot"></span>
        <span>{{ hasConfiguredLlm ? '外接 AI 已启用' : '未启用外接 AI' }}</span>
      </div>

      <div class="scope-group" role="group" aria-label="抽取范围">
        <button
          type="button"
          class="scope-button"
          :class="{ active: extractionScope === 'source' }"
          :disabled="!canUseSelectedSource || isExtracting"
          @click="extractionScope = 'source'"
        >
          当前资料
        </button>
        <button
          type="button"
          class="scope-button"
          :class="{ active: extractionScope === 'project' }"
          :disabled="isExtracting"
          @click="extractionScope = 'project'"
        >
          全部资料
        </button>
      </div>

      <label class="limit-field">
        <span>片段上限</span>
        <input v-model.number="maxChunks" type="number" min="1" max="80" :disabled="isExtracting" />
      </label>

      <label class="privacy-check">
        <input v-model="privacyConfirmed" type="checkbox" :disabled="isExtracting" />
        <span>允许将选中资料片段发送到用户配置的外部 AI 服务</span>
      </label>

      <button class="primary-button" type="button" :disabled="!canExtract" @click="handleExtract">
        {{ isExtracting ? '启动中...' : hasActiveRun ? '重新开始抽取' : '抽取图谱候选' }}
      </button>
    </section>

    <p v-if="!hasConfiguredLlm" class="config-hint">
      未配置用户 API Key 时，章枢只保留本地知识库能力，不会调用外部 AI。
    </p>
    <p v-else-if="extractionScope === 'source' && props.selectedSourceTitle" class="scope-hint">
      当前范围：{{ props.selectedSourceTitle }}
    </p>

    <section v-if="latestRun" class="run-strip">
      <span>最近抽取</span>
      <strong>{{ knowledgeGraphExtractionStatusLabels[latestRun.status] || latestRun.status }}</strong>
      <span>{{ latestRun.processed_chunks }}/{{ latestRun.total_chunks }} 片段</span>
      <span>{{ latestRun.model_name }}</span>
      <span>{{ formatDate(latestRun.completed_at || latestRun.created_at) }}</span>
      <span v-if="latestRun.status === 'failed' && latestRun.error_message" class="run-error">
        {{ latestRun.error_message }}
      </span>
    </section>

    <div class="graph-tabs">
      <button
        type="button"
        :class="{ active: activeTab === 'candidates' }"
        @click="activeTab = 'candidates'"
      >
        候选关系 {{ candidateRelations.length }}
      </button>
      <button type="button" :class="{ active: activeTab === 'graph' }" @click="activeTab = 'graph'">
        已确认图谱 {{ acceptedRelations.length }}
      </button>
    </div>

    <section v-if="activeTab === 'candidates'" class="candidate-section">
      <p v-if="isLoading" class="empty-hint">正在加载知识图谱...</p>
      <p v-else-if="candidateRelations.length === 0" class="empty-hint">
        暂无候选关系。
      </p>

      <ul v-else class="relation-list">
        <li v-for="relation in candidateRelations" :key="relation.id" class="relation-item">
          <div class="relation-main">
            <span class="entity-name">{{ relation.subject.canonical_name }}</span>
            <span class="predicate">{{ relation.predicate_text }}</span>
            <span class="entity-name">{{ relation.object.canonical_name }}</span>
          </div>
          <div class="relation-meta">
            <span>{{ knowledgeGraphRelationTypeLabels[relation.relation_type] }}</span>
            <span>{{ knowledgeGraphFactStatusLabels[relation.fact_status] }}</span>
            <span>置信度 {{ formatPercent(relation.confidence) }}</span>
            <span>{{ sourceTitle(relation) }}</span>
          </div>
          <p v-if="evidencePreview(relation)" class="evidence-text">
            {{ evidencePreview(relation) }}
          </p>
          <div class="relation-actions">
            <button type="button" class="link-button" @click="openEvidenceSource(relation)">
              打开资料
            </button>
            <button
              type="button"
              class="secondary-button"
              :disabled="mutatingRelationId === relation.id"
              @click="handleRejectRelation(relation)"
            >
              忽略
            </button>
            <button
              type="button"
              class="primary-button"
              :disabled="mutatingRelationId === relation.id"
              @click="handleAcceptRelation(relation)"
            >
              确认
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section v-else class="accepted-section">
      <div class="graph-summary">
        <span>{{ subgraph.nodes.length }} 个实体</span>
        <span>{{ subgraph.edges.length }} 条关系</span>
      </div>

      <p v-if="acceptedRelations.length === 0" class="empty-hint">暂无已确认关系。</p>
      <div v-else class="subgraph-layout">
        <div class="node-column">
          <h3>实体</h3>
          <ul>
            <li v-for="node in subgraph.nodes" :key="node.id">
              <span class="node-name">{{ node.label }}</span>
              <span class="node-type">{{ knowledgeGraphEntityTypeLabels[node.entity_type] }}</span>
            </li>
          </ul>
        </div>
        <div class="edge-column">
          <h3>关系</h3>
          <ul>
            <li v-for="edge in subgraph.edges" :key="edge.id">
              <span class="entity-name">{{ nodeLabel(edge.source) }}</span>
              <span class="predicate">{{ edge.label }}</span>
              <span class="entity-name">{{ nodeLabel(edge.target) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </section>
</template>

<style scoped>
.knowledge-graph-panel {
  display: grid;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
}

.graph-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.graph-header h2,
.node-column h3,
.edge-column h3 {
  margin: 0;
  color: var(--zs-color-text);
}

.graph-header h2 {
  font-size: 1.1rem;
}

.graph-header p,
.config-hint,
.scope-hint,
.empty-hint {
  margin: 4px 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.6;
}

.extract-toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 6px;
  background: var(--zs-color-bg);
}

.llm-state,
.run-strip,
.graph-summary,
.relation-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

.llm-state {
  font-weight: 700;
}

.state-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--zs-color-warning);
}

.llm-state.ready .state-dot {
  background: var(--zs-color-success);
}

.scope-group,
.graph-tabs {
  display: flex;
  gap: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  overflow: hidden;
}

.scope-button,
.graph-tabs button {
  border: none;
  border-left: 1px solid var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 700;
  min-height: 34px;
  padding: 0 12px;
}

.scope-button:first-child,
.graph-tabs button:first-child {
  border-left: none;
}

.scope-button.active,
.graph-tabs button.active {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.scope-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.limit-field {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.limit-field input {
  width: 64px;
  border: 1px solid var(--zs-color-border);
  border-radius: 4px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-size: 0.82rem;
  min-height: 32px;
  padding: 0 8px;
}

.privacy-check {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--zs-color-text);
  font-size: 0.8rem;
}

.privacy-check input {
  width: 15px;
  height: 15px;
  accent-color: var(--zs-color-primary);
}

.primary-button,
.secondary-button {
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 700;
  min-height: 34px;
  padding: 0 12px;
}

.primary-button {
  border: 1px solid var(--zs-color-primary);
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  border: 1px solid var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.primary-button:disabled,
.secondary-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.error-message,
.success-message {
  border-radius: 6px;
  font-size: 0.84rem;
  padding: 10px 12px;
}

.error-message {
  border: 1px solid var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.success-message {
  border: 1px solid var(--zs-color-success);
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.run-strip {
  padding: 8px 10px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 6px;
  background: var(--zs-color-bg);
}

.run-strip strong {
  color: var(--zs-color-text);
}

.run-error {
  color: var(--zs-color-danger);
  font-weight: 700;
}

.candidate-section,
.accepted-section {
  display: grid;
  gap: 12px;
}

.relation-list,
.node-column ul,
.edge-column ul {
  display: grid;
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.relation-item,
.node-column li,
.edge-column li {
  display: grid;
  gap: 8px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 6px;
  padding: 12px;
  background: var(--zs-color-bg);
}

.relation-main,
.edge-column li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.entity-name,
.node-name {
  color: var(--zs-color-text);
  font-size: 0.9rem;
  font-weight: 800;
}

.predicate {
  color: var(--zs-color-primary);
  font-size: 0.82rem;
  font-weight: 800;
}

.relation-meta span,
.node-type {
  border-radius: 999px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
}

.evidence-text {
  margin: 0;
  border-left: 3px solid var(--zs-color-primary);
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.6;
  padding-left: 10px;
}

.relation-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.link-button {
  border: none;
  background: transparent;
  color: var(--zs-color-primary);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0 4px;
}

.link-button:hover {
  text-decoration: underline;
}

.subgraph-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(320px, 1.2fr);
  gap: 12px;
}

.node-column,
.edge-column {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.node-column h3,
.edge-column h3 {
  font-size: 0.92rem;
}

.node-column li {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 900px) {
  .graph-header,
  .subgraph-layout {
    grid-template-columns: 1fr;
  }

  .graph-header {
    display: grid;
  }

  .relation-actions {
    justify-content: flex-start;
  }
}
</style>
