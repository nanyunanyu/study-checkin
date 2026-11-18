<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import type { Review } from '../types'
import { PROBLEM_OPTIONS } from '../utils'
import Icon from './Icon.vue'

const props = defineProps<{ review: Review; readonly?: boolean }>()
const emit = defineEmits<{ (event: 'update', patch: Partial<Review>): void }>()
const bestList = ref<HTMLElement>()
const priorityList = ref<HTMLElement>()
const visibleBestCount = computed(() => Math.max(2, props.review.best?.length || 0))
const visiblePriorityCount = computed(() => Math.max(3, props.review.priorities?.length || 0))
const customProblems = computed(() => (props.review.problems || []).filter((problem) => !PROBLEM_OPTIONS.includes(problem)))

type ReviewList = 'best' | 'priorities'

function setEntry(field: ReviewList, index: number, value: string) {
  const entries = [...(props.review[field] || [])]
  while (entries.length <= index) entries.push('')
  entries[index] = value
  emit('update', { [field]: entries })
}

async function addEntry(field: ReviewList) {
  const index = field === 'best' ? visibleBestCount.value : visiblePriorityCount.value
  setEntry(field, index, '')
  await nextTick()
  const list = field === 'best' ? bestList.value : priorityList.value
  list?.querySelectorAll('input')[index]?.focus()
}

function removeBest(index: number) {
  emit('update', { best: props.review.best.filter((_, position) => index !== position) })
}

function removePriority(index: number) {
  const priorities = [...(props.review.priorities || ['', '', ''])]
  priorities.splice(index, 1)
  while (priorities.length < 3) priorities.push('')
  emit('update', { priorities })
}

function toggleProblem(problem: string) {
  const set = new Set(props.review.problems || [])
  if (set.has(problem)) set.delete(problem)
  else set.add(problem)
  emit('update', { problems: [...set] })
}

function removeCustomProblem(problem: string) {
  emit('update', { problems: (props.review.problems || []).filter((item) => item !== problem) })
}
</script>

<template>
  <section class="card">
    <div class="card-pad">
      <div class="card-head">
        <div class="card-title">今日复盘</div>
        <span v-if="readonly" class="tag">只读</span>
        <div class="spacer" />
        <span class="hint">每天留 3 分钟，写清楚问题比多刷一套题有用</span>
      </div>

      <div class="stack" style="gap: 14px">
        <div>
          <div class="hint" style="margin-bottom: 6px">最有效的学习内容</div>
          <div ref="bestList" class="grid-2">
            <div v-for="index in visibleBestCount" :key="index" class="best-entry">
              <el-input
                :readonly="readonly"
                :model-value="review.best?.[index - 1] || ''"
                :aria-label="`最有效的学习内容 ${index}`"
                :placeholder="index === 1 ? '例如：晨背 40 分钟记了 60 个单词' : `学习内容 ${index}（可留空）`"
                @input="setEntry('best', index - 1, $event)"
              />
              <el-button v-if="!readonly && index > 2" text circle type="danger" :aria-label="`删除第 ${index} 条学习内容`" @click="removeBest(index - 1)"><Icon name="trash" :size="14" /></el-button>
            </div>
          </div>
          <div v-if="!readonly" class="review-actions">
            <el-button class="review-add" text type="primary" aria-label="新增学习内容" title="新增学习内容" @click="addEntry('best')"><Icon name="plus" :size="16" /></el-button>
          </div>
        </div>

        <div>
          <div class="hint" style="margin-bottom: 6px">今日问题</div>
          <div class="row review-problem-options">
            <el-button
              v-for="option in PROBLEM_OPTIONS"
              :key="option"
              class="chip-pick"
              :class="{ active: (review.problems || []).includes(option) }"
              :type="(review.problems || []).includes(option) ? 'primary' : 'default'"
              size="small"
              :aria-pressed="(review.problems || []).includes(option)"
              :disabled="readonly"
              @click="toggleProblem(option)"
            >
              {{ option }}
            </el-button>
          </div>
          <div v-if="customProblems.length" class="row review-custom-problems">
            <span v-for="problem in customProblems" :key="problem" class="custom-problem-tag">
              {{ problem }}
              <el-button v-if="!readonly" text circle type="danger" :aria-label="`删除问题：${problem}`" @click="removeCustomProblem(problem)">×</el-button>
            </span>
          </div>
          <el-input
            v-if="(review.problems || []).includes('其他')"
            :readonly="readonly"
            :model-value="review.other"
            placeholder="具体是什么问题"
            style="margin-top: 8px"
            @input="emit('update', { other: $event })"
          />
        </div>

        <div>
          <div class="hint" style="margin-bottom: 6px">明日优先解决</div>
          <div ref="priorityList" class="stack priority-list" style="gap: 8px">
            <div v-for="index in visiblePriorityCount" :key="index" class="priority-row">
              <span class="priority-index">{{ index }}.</span>
              <el-input
                :readonly="readonly"
                :model-value="review.priorities?.[index - 1] || ''"
                :placeholder="`优先解决事项 ${index}`"
                @input="setEntry('priorities', index - 1, $event)"
              />
              <el-button v-if="!readonly && visiblePriorityCount > 3" class="priority-remove" text circle type="danger" :aria-label="`删除第 ${index} 项`" @click="removePriority(index - 1)"><Icon name="trash" :size="14" /></el-button>
            </div>
          </div>
          <div v-if="!readonly" class="review-actions">
            <el-button class="review-add" text type="primary" aria-label="新增优先事项" title="新增优先事项" @click="addEntry('priorities')"><Icon name="plus" :size="16" /></el-button>
          </div>
        </div>

        <div>
          <div class="hint" style="margin-bottom: 6px">明日调整</div>
          <el-input
            type="textarea"
            :rows="3"
            :readonly="readonly"
            :model-value="review.adjustment"
            placeholder="例如：上午网课容易走神，改成先看 15 分钟再做笔记"
            @input="emit('update', { adjustment: $event })"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.review-problem-options,
.review-custom-problems {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.review-problem-options > .el-button {
  width: auto;
  min-height: 30px;
  height: 30px;
  margin: 0;
  padding: 0 9px;
  font-size: 12px;
}

.review-custom-problems {
  margin-top: 8px;
}

.custom-problem-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 28px;
  padding: 1px 4px 1px 8px;
  border: 1px solid var(--accent);
  border-radius: 99px;
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.custom-problem-tag button {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: inherit;
  font-size: 18px;
  line-height: 1;
}

.priority-row {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px;
}

.priority-index {
  color: var(--text-3);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.priority-list .priority-row .el-input__wrapper {
  min-height: 40px;
}

.priority-row:not(:has(.priority-remove)) { grid-template-columns: 20px minmax(0, 1fr); }
.best-entry { display: flex; align-items: center; min-width: 0; gap: 6px; }
.best-entry > .el-input { min-width: 0; }
.review-actions { display: flex; justify-content: flex-end; margin-top: 4px; }
.review-add.el-button { width: 36px; height: 36px; padding: 0; }
</style>
