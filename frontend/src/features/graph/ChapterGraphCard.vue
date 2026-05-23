<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listChapterCharacters } from '@/entities/chapter-character/api'
import type { ChapterCharacterLink } from '@/entities/chapter-character/types'
import { listChapterClues } from '@/entities/chapter-clue/api'
import type { ChapterClueLink } from '@/entities/chapter-clue/types'
import { listChapterSettings } from '@/entities/chapter-setting/api'
import type { ChapterSettingLink } from '@/entities/chapter-setting/types'
import { listChapterTimelineEvents } from '@/entities/timeline/api'
import type { TimelineEvent } from '@/entities/timeline/types'
import { listGraphEdges, listGraphNodes } from '@/entities/graph/api'
import type { GraphEdge, GraphNode } from '@/entities/graph/types'
import {
  graphEdgeDirectionLabels,
  graphEdgeRelationLabels,
  graphNodeTypeLabels,
  graphVisibilityLabels,
} from '@/entities/graph/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

type ChapterTargetType = 'character' | 'setting' | 'clue' | 'timeline_event'

interface MatchedNodeSummary {
  node: GraphNode
  nodeTypeLabel: string
  boundTypeLabel: string
  summary: string
  visibilityClass: string
}

interface DirectEdgeSummary {
  edge: GraphEdge
  fromNode: GraphNode
  toNode: GraphNode
  relationLabel: string
  directionLabel: string
  directionSymbol: string
  visibilityLabel: string
  edgeLabel: string
  strengthLabel: string
  visibilityClass: string
  bothMatched: boolean
}

interface AssociatedNodeSummary {
  node: GraphNode
  nodeTypeLabel: string
  visibilityClass: string
  viaLabel: string
}

const isLoading = ref(false)
const errorMessage = ref('')
const chapterCharacters = ref<ChapterCharacterLink[]>([])
const chapterSettings = ref<ChapterSettingLink[]>([])
const chapterClues = ref<ChapterClueLink[]>([])
const chapterTimelineEvents = ref<TimelineEvent[]>([])
const graphNodes = ref<GraphNode[]>([])
const graphEdges = ref<GraphEdge[]>([])

let loadToken = 0

watch(
  () => [props.projectId, props.chapterId],
  () => {
    void refreshPanel()
  },
  { immediate: true },
)

const chapterTargetKeys = computed(() => {
  const keys = new Set<string>()

  chapterCharacters.value.forEach((link) => {
    keys.add(`character:${link.character.id}`)
  })

  chapterSettings.value.forEach((link) => {
    keys.add(`setting:${link.setting_item.id}`)
  })

  chapterClues.value.forEach((link) => {
    keys.add(`clue:${link.clue.id}`)
  })

  chapterTimelineEvents.value.forEach((event) => {
    keys.add(`timeline_event:${event.id}`)
  })

  return keys
})

const matchedNodes = computed<MatchedNodeSummary[]>(() => {
  const matched = graphNodes.value.filter((node) => {
    if (node.visibility === 'hidden') {
      return false
    }

    if (!node.bound_type || !node.bound_id) {
      return false
    }

    return chapterTargetKeys.value.has(`${node.bound_type}:${node.bound_id}`)
  })

  return matched
    .map((node) => ({
      node,
      nodeTypeLabel: graphNodeTypeLabels[node.node_type],
      boundTypeLabel: getBoundTypeLabel(node.bound_type),
      summary: node.summary || '暂无简介。',
      visibilityClass: getVisibilityClass(node.visibility),
    }))
    .sort((left, right) => {
      if (left.nodeTypeLabel !== right.nodeTypeLabel) {
        return left.nodeTypeLabel.localeCompare(right.nodeTypeLabel, 'zh-Hans-CN')
      }
      return left.node.title.localeCompare(right.node.title, 'zh-Hans-CN')
    })
})

const matchedNodeIds = computed(() => new Set(matchedNodes.value.map((item) => item.node.id)))

const directEdges = computed<DirectEdgeSummary[]>(() => {
  const matchedIds = matchedNodeIds.value

  return graphEdges.value
    .filter((edge) => {
      if (edge.visibility === 'hidden') {
        return false
      }

      return matchedIds.has(edge.from_node_id) || matchedIds.has(edge.to_node_id)
    })
    .map((edge) => {
      const fromNode = graphNodes.value.find((node) => node.id === edge.from_node_id)
      const toNode = graphNodes.value.find((node) => node.id === edge.to_node_id)
      if (!fromNode || !toNode || fromNode.visibility === 'hidden' || toNode.visibility === 'hidden') {
        return null
      }

      return {
        edge,
        fromNode,
        toNode,
        relationLabel: graphEdgeRelationLabels[edge.relation_type],
        directionLabel: graphEdgeDirectionLabels[edge.direction],
        directionSymbol: edge.direction === 'directed' ? '→' : '↔',
        visibilityLabel: graphVisibilityLabels[edge.visibility],
        edgeLabel: edge.label || graphEdgeRelationLabels[edge.relation_type],
        strengthLabel: `强度 ${edge.strength}`,
        visibilityClass: getVisibilityClass(edge.visibility),
        bothMatched: matchedIds.has(edge.from_node_id) && matchedIds.has(edge.to_node_id),
      }
    })
    .filter((item): item is DirectEdgeSummary => item !== null)
    .sort((left, right) => {
      if (left.bothMatched !== right.bothMatched) {
        return left.bothMatched ? -1 : 1
      }

      return (
        left.relationLabel.localeCompare(right.relationLabel, 'zh-Hans-CN')
        || left.fromNode.title.localeCompare(right.fromNode.title, 'zh-Hans-CN')
        || left.toNode.title.localeCompare(right.toNode.title, 'zh-Hans-CN')
      )
    })
})

const associatedNodes = computed<AssociatedNodeSummary[]>(() => {
  const matchedIds = matchedNodeIds.value
  const map = new Map<string, AssociatedNodeSummary>()

  for (const item of directEdges.value) {
    const endpoints: Array<{ node: GraphNode; matched: boolean }> = [
      { node: item.fromNode, matched: matchedIds.has(item.fromNode.id) },
      { node: item.toNode, matched: matchedIds.has(item.toNode.id) },
    ]

    const external = endpoints.find((entry) => !entry.matched)
    if (!external || external.node.visibility === 'hidden') {
      continue
    }

    if (!map.has(external.node.id)) {
      map.set(external.node.id, {
        node: external.node,
        nodeTypeLabel: graphNodeTypeLabels[external.node.node_type],
        visibilityClass: getVisibilityClass(external.node.visibility),
        viaLabel: item.relationLabel,
      })
    }
  }

  return [...map.values()].sort((left, right) =>
    left.node.title.localeCompare(right.node.title, 'zh-Hans-CN'),
  )
})

const hasMatchedNodes = computed(() => matchedNodes.value.length > 0)

async function refreshPanel() {
  const currentToken = ++loadToken

  if (!props.projectId || !props.chapterId) {
    clearState()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    // 当前仅基于章节的显式绑定关系抽取图谱摘要；后续可再扩展为关键词、共现或 AI 候选匹配。
    const [characters, settings, clues, timelineEvents, nodes, edges] = await Promise.all([
      listChapterCharacters(props.chapterId),
      listChapterSettings(props.chapterId),
      listChapterClues(props.chapterId),
      listChapterTimelineEvents(props.chapterId),
      listGraphNodes(props.projectId),
      listGraphEdges(props.projectId),
    ])

    if (currentToken !== loadToken) {
      return
    }

    chapterCharacters.value = characters
    chapterSettings.value = settings
    chapterClues.value = clues
    chapterTimelineEvents.value = timelineEvents
    graphNodes.value = nodes
    graphEdges.value = edges
  } catch (error) {
    if (currentToken === loadToken) {
      void error
      errorMessage.value = '关系图信息加载失败，请稍后重试。'
    }
  } finally {
    if (currentToken === loadToken) {
      isLoading.value = false
    }
  }
}

function clearState() {
  isLoading.value = false
  errorMessage.value = ''
  chapterCharacters.value = []
  chapterSettings.value = []
  chapterClues.value = []
  chapterTimelineEvents.value = []
  graphNodes.value = []
  graphEdges.value = []
}

function getBoundTypeLabel(boundType: GraphNode['bound_type']) {
  switch (boundType) {
    case 'character':
      return '人物'
    case 'setting':
      return '设定'
    case 'clue':
      return '伏笔'
    case 'timeline_event':
      return '时间轴事件'
    case 'custom':
      return '自定义'
    default:
      return '未绑定'
  }
}

function getVisibilityClass(visibility: GraphNode['visibility']) {
  return visibility === 'subtle' ? 'subtle' : 'normal'
}
</script>

<template>
  <section class="chapter-graph-card">
    <header class="panel-header">
      <div>
        <p class="eyebrow">本章关系图</p>
        <h2>关系图摘要</h2>
      </div>
      <RouterLink class="graph-link" :to="`/projects/${projectId}/graph`">完整关系图</RouterLink>
    </header>

    <p class="helper-note">仅显示与当前章节资料显式关联的关系节点。当前结果来自显式绑定，暂未启用智能匹配。</p>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章关系图。</p>

    <template v-else>
      <p v-if="isLoading" class="state-message">正在加载本章关系图……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <template v-else>
        <section class="section-block">
          <div class="section-head">
            <h3>本章相关节点</h3>
            <span class="count-pill">{{ matchedNodes.length }}</span>
          </div>

          <p v-if="!hasMatchedNodes" class="state-message compact">
            本章暂无关系图节点。可在完整关系图中创建或绑定节点。当前结果来自显式绑定，暂未启用智能匹配。
          </p>

          <div v-else class="node-list">
            <article
              v-for="item in matchedNodes"
              :key="item.node.id"
              class="node-card"
              :class="item.visibilityClass"
            >
              <div class="node-card-head">
                <div>
                  <p class="node-type">{{ item.nodeTypeLabel }}</p>
                  <h4>{{ item.node.title }}</h4>
                </div>
                <span class="bound-pill">{{ item.boundTypeLabel }}</span>
              </div>

              <p class="node-summary">{{ item.summary }}</p>
              <p class="node-meta">可见性：{{ graphVisibilityLabels[item.node.visibility] }}</p>
            </article>
          </div>
        </section>

        <section class="section-block">
          <div class="section-head">
            <h3>直接关系</h3>
            <span class="count-pill">{{ directEdges.length }}</span>
          </div>

          <p v-if="directEdges.length === 0" class="state-message compact">暂无直接关系。</p>

          <div v-else class="edge-list">
            <article
              v-for="item in directEdges"
              :key="item.edge.id"
              class="edge-card"
              :class="item.visibilityClass"
            >
              <div class="edge-card-head">
                <span class="edge-relation">{{ item.relationLabel }}</span>
                <span class="edge-direction">{{ item.directionLabel }}</span>
                <span class="edge-visibility">{{ item.visibilityLabel }}</span>
              </div>

              <p class="edge-line">
                <strong>{{ item.fromNode.title }}</strong>
                <span>{{ item.directionSymbol }}</span>
                <strong>{{ item.toNode.title }}</strong>
              </p>

              <p class="edge-meta">
                <span>标签：{{ item.edgeLabel }}</span>
                <span>·</span>
                <span>{{ item.strengthLabel }}</span>
              </p>
            </article>
          </div>
        </section>

        <section class="section-block">
          <div class="section-head">
            <h3>关联节点</h3>
            <span class="count-pill">{{ associatedNodes.length }}</span>
          </div>

          <p v-if="associatedNodes.length === 0" class="state-message compact">暂无关联节点。</p>

          <div v-else class="related-node-list">
            <article v-for="item in associatedNodes" :key="item.node.id" class="related-node-card" :class="item.visibilityClass">
              <div>
                <p class="node-type">{{ item.nodeTypeLabel }}</p>
                <h4>{{ item.node.title }}</h4>
              </div>
              <p class="related-node-meta">通过：{{ item.viaLabel }}</p>
            </article>
          </div>
        </section>
      </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-graph-card {
  display: grid;
  gap: 12px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow,
h2,
h3,
h4,
p {
  margin: 0;
}

.eyebrow {
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

h2 {
  color: var(--zs-color-text);
  font-size: 1rem;
}

h3 {
  color: var(--zs-color-text);
  font-size: 0.95rem;
}

h4 {
  color: var(--zs-color-text);
  font-size: 0.92rem;
}

.graph-link {
  color: var(--zs-color-primary);
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
}

.helper-note {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.6;
}

.state-message,
.error-message {
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
  text-align: center;
}

.state-message.compact {
  padding: 12px;
}

.error-message {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.section-block {
  display: grid;
  gap: 10px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.count-pill {
  min-width: 28px;
  border-radius: 999px;
  padding: 3px 8px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.75rem;
  font-weight: 800;
  text-align: center;
}

.node-list,
.edge-list,
.related-node-list {
  display: grid;
  gap: 10px;
}

.node-card,
.edge-card,
.related-node-card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-surface);
}

.node-card.subtle,
.edge-card.subtle,
.related-node-card.subtle {
  opacity: 0.78;
  background: var(--zs-color-bg);
}

.node-card-head,
.edge-card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.node-type,
.node-meta,
.related-node-meta,
.edge-meta {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.55;
}

.node-summary {
  color: var(--zs-color-text);
  font-size: 0.82rem;
  line-height: 1.65;
  white-space: pre-wrap;
}

.bound-pill,
.edge-relation,
.edge-direction,
.edge-visibility {
  border-radius: 999px;
  padding: 3px 8px;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-info);
  font-size: 0.72rem;
  font-weight: 800;
}

.edge-direction {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.edge-visibility {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
}

.edge-line {
  color: var(--zs-color-text);
  font-size: 0.84rem;
  line-height: 1.6;
}

.edge-line span {
  margin: 0 8px;
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.edge-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 900px) {
  .node-card-head,
  .edge-card-head,
  .panel-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
